from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any

import requests

try:
    import cv2

    _CV2_AVAILABLE = True
except Exception:
    cv2 = None
    _CV2_AVAILABLE = False

from worker.worker_config import (
    OLLAMA_ENABLED,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
    OLLAMA_URL,
    OLLAMA_VISION_ENABLED,
    OLLAMA_VISION_FRAME_COUNT,
    OLLAMA_VISION_MAX_SIDE,
    OLLAMA_VISION_MODEL,
    OLLAMA_VISION_NUM_GPU,
    OLLAMA_VISION_REQUIRE_GPU,
    OLLAMA_VISION_TIMEOUT,
    OLLAMA_VISION_UNLOAD_CPU_FALLBACK,
)
from worker.worker_logging import LOGGER

_ALLOWED_ACTIONS = {
    "keep",
    "extend_start",
    "extend_end",
    "trim_start",
    "trim_end",
    "drop",
}


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """
    Extract the first valid JSON object from arbitrary model output.
    """
    if not text:
        return None

    stripped = text.strip()
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if code_block:
        candidate = code_block.group(1).strip()
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    # Balanced brace scan with string/escape awareness.
    n = len(text)
    for start in range(n):
        if text[start] != "{":
            continue
        depth = 0
        in_string = False
        escape = False
        for idx in range(start, n):
            ch = text[idx]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start : idx + 1]
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, dict):
                            return parsed
                    except Exception:
                        break
                    break
                if depth < 0:
                    break
    return None


def _clamp01(value: Any, default: float) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    return max(0.0, min(1.0, out))


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "oui"}:
            return True
        if lowered in {"0", "false", "no", "n", "non"}:
            return False
    return default


def _post_ollama_generate(
    payload: dict[str, Any],
    *,
    timeout_seconds: float | None = None,
) -> requests.Response:
    timeout = float(timeout_seconds) if timeout_seconds is not None else float(OLLAMA_TIMEOUT)
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json=payload,
        timeout=timeout,
    )
    if response.status_code == 400 and payload.get("format"):
        payload_no_format = dict(payload)
        payload_no_format.pop("format", None)
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload_no_format,
            timeout=timeout,
        )
    return response


def _ollama_get_loaded_model_vram(model_name: str) -> int | None:
    model_name = str(model_name).strip()
    if not model_name:
        return None
    try:
        response = requests.get(f"{OLLAMA_URL}/api/ps", timeout=4)
        if response.status_code != 200:
            return None
        data = response.json()
        models = data.get("models", [])
        if not isinstance(models, list):
            return None
        for entry in models:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name", "") or entry.get("model", "")).strip()
            if not name:
                continue
            if name == model_name or model_name in name:
                try:
                    return int(entry.get("size_vram", 0) or 0)
                except Exception:
                    return 0
    except Exception:
        return None
    return None


def _ollama_unload_model(model_name: str) -> bool:
    model_name = str(model_name).strip()
    if not model_name:
        return False
    payload = {
        "model": model_name,
        "prompt": "",
        "stream": False,
        "keep_alive": 0,
    }
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=8,
        )
        return response.status_code == 200
    except Exception:
        return False


def _extract_clip_frames_base64(
    video_path: Path,
    start: float,
    end: float,
    frame_count: int,
    max_side: int,
) -> list[str]:
    """
    Extracts uniformly sampled JPG frames from [start, end] and encodes them to base64.
    """
    if not _CV2_AVAILABLE or frame_count <= 0:
        return []
    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return []

        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        total_frames = float(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0)
        duration = (total_frames / fps) if fps > 0 else 0.0

        safe_start = max(0.0, float(start))
        safe_end = max(safe_start + 0.10, float(end))
        if duration > 0:
            safe_start = min(safe_start, max(0.0, duration - 0.10))
            safe_end = min(safe_end, duration)
            if safe_end <= safe_start:
                safe_end = min(duration, safe_start + 0.10)

        span = max(0.10, safe_end - safe_start)
        times = [
            safe_start + span * ((idx + 1) / (frame_count + 1))
            for idx in range(frame_count)
        ]

        output: list[str] = []
        for ts in times:
            cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, ts) * 1000.0)
            ok, frame = cap.read()
            if (not ok or frame is None) and fps > 0:
                # Some codecs are unreliable with POS_MSEC; fallback to frame-index seeking.
                frame_idx = int(max(0.0, ts) * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, frame_idx))
                ok, frame = cap.read()
            if not ok or frame is None:
                continue

            if max_side > 0:
                h, w = frame.shape[:2]
                largest = max(h, w)
                if largest > max_side:
                    scale = max_side / float(largest)
                    new_w = max(64, int(round(w * scale)))
                    new_h = max(64, int(round(h * scale)))
                    frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

            ok, buffer = cv2.imencode(
                ".jpg",
                frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), 82],
            )
            if not ok:
                continue
            output.append(base64.b64encode(buffer.tobytes()).decode("ascii"))

        if not output:
            # Last-resort fallback: decode from start and sample uniformly by index.
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            fallback_frames: list[Any] = []
            while len(fallback_frames) < 120:
                ok, frame = cap.read()
                if not ok or frame is None:
                    break
                fallback_frames.append(frame)
            if fallback_frames:
                picks = [
                    int(round((len(fallback_frames) - 1) * ((idx + 1) / (frame_count + 1))))
                    for idx in range(frame_count)
                ]
                for idx in picks:
                    frame = fallback_frames[max(0, min(len(fallback_frames) - 1, idx))]
                    if max_side > 0:
                        h, w = frame.shape[:2]
                        largest = max(h, w)
                        if largest > max_side:
                            scale = max_side / float(largest)
                            new_w = max(64, int(round(w * scale)))
                            new_h = max(64, int(round(h * scale)))
                            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
                    ok, buffer = cv2.imencode(
                        ".jpg",
                        frame,
                        [int(cv2.IMWRITE_JPEG_QUALITY), 82],
                    )
                    if not ok:
                        continue
                    output.append(base64.b64encode(buffer.tobytes()).decode("ascii"))

        cap.release()
        return output
    except Exception:
        return []


def _ollama_analyze_clip_advanced(
    text: str,
    context_before: str = "",
    context_after: str = "",
) -> dict[str, Any]:
    """
    Analyse semantique LLM d'un clip pour guider le scoring de coupe.
    """
    default_result = {
        "is_complete": True,
        "cut_quality": 0.7,
        "suggested_action": "keep",
        "reason": "analyse non disponible",
        "ollama_used": False,
        "viral_potential": 0.5,
        "grammar_ok": True,
    }

    combined_context = " ".join(
        part.strip()
        for part in (text, context_before, context_after)
        if isinstance(part, str) and part.strip()
    )
    if not OLLAMA_ENABLED or not combined_context:
        return default_result

    clip_text = str(text).strip()[:1600]
    before_text = str(context_before).strip()[:260]
    after_text = str(context_after).strip()[:220]

    prompt = f"""Tu es monteur expert de clips YouTube Shorts/Reels.
Objectif: evaluer un extrait deja propose par le detecteur.
Tu fais du reranking semantique (qualite de coupe), pas de detection globale.

Regles prioritaires:
1) REJETER contenu commercial/sponsor/pub/CTA (code promo, lien bio/description, partenaire).
2) Favoriser une fin naturelle (phrase terminee, idee complete, pas de coupure brutale).
3) Penaliser les fins hors sujet ou digressions inutiles.
4) Etre strict: un clip moyen doit etre note moyen, pas excellent.
5) Si contexte avant/apres montre une meilleure coupe proche, proposer trim/extend.

Contexte avant:
\"\"\"{before_text}\"\"\"

Clip:
\"\"\"{clip_text}\"\"\"

Contexte apres:
\"\"\"{after_text}\"\"\"

Sortie JSON UNIQUEMENT, sans markdown ni texte autour:
{{
  "is_complete": true/false,
  "cut_quality": 0.0-1.0,
  "viral_potential": 0.0-1.0,
  "grammar_ok": true/false,
  "suggested_action": "keep|extend_start|extend_end|trim_start|trim_end|drop",
  "reason": "max 20 mots"
}}

Contraintes de notation:
- Si pub/sponsor/CTA detecte: suggested_action="drop", cut_quality <= 0.20, viral_potential <= 0.25.
- Si fin coupee ou hors sujet: preferer "trim_end" et baisser cut_quality.
- Si le clip est net et coherent: "keep".
"""

    try:
        payload: dict[str, Any] = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.05,
                "num_predict": 220,
            },
        }
        response = _post_ollama_generate(payload)

        if response.status_code != 200:
            LOGGER.warning("Ollama API error: %s", response.status_code)
            return default_result

        result_text = response.json().get("response", "")
        parsed = _extract_json_object(result_text)
        if parsed is None:
            LOGGER.warning("Ollama: no JSON in response")
            return default_result

        suggested_action = str(parsed.get("suggested_action", "keep")).strip().lower()
        if suggested_action not in _ALLOWED_ACTIONS:
            suggested_action = "keep"

        return {
            "is_complete": bool(parsed.get("is_complete", True)),
            "cut_quality": _clamp01(parsed.get("cut_quality", 0.7), 0.7),
            "viral_potential": _clamp01(parsed.get("viral_potential", 0.5), 0.5),
            "grammar_ok": bool(parsed.get("grammar_ok", True)),
            "suggested_action": suggested_action,
            "reason": str(parsed.get("reason", ""))[:100],
            "ollama_used": True,
        }

    except requests.exceptions.Timeout:
        LOGGER.warning("Ollama timeout after %ds", OLLAMA_TIMEOUT)
        return default_result
    except requests.exceptions.ConnectionError:
        LOGGER.warning("Ollama not reachable at %s", OLLAMA_URL)
        return default_result
    except json.JSONDecodeError as e:
        LOGGER.warning("Ollama JSON parse error: %s", e)
        return default_result
    except Exception as e:
        LOGGER.warning("Ollama error: %s", e)
        return default_result


def _ollama_vision_analyze_clip(
    video_path: Path,
    start: float,
    end: float,
    clip_text: str = "",
    audio_hint: str = "",
    profile_hint: str = "",
    tag_hint: str = "",
) -> dict[str, Any]:
    """
    Vision analysis from sampled clip frames.
    """
    default_result = {
        "vision_used": False,
        "scene_type": "unknown",
        "action_level": 0.5,
        "clip_quality": 0.5,
        "audio_visual_fit": 0.5,
        "is_car_showcase": False,
        "title_hint": "",
        "frame_count": 0,
        "reason": "vision non disponible",
    }
    if not OLLAMA_ENABLED or not OLLAMA_VISION_ENABLED:
        return default_result
    if not _CV2_AVAILABLE:
        return default_result
    if not isinstance(video_path, Path) or not video_path.exists():
        return default_result

    clip_duration = max(0.1, float(end) - float(start))
    frame_target = int(OLLAMA_VISION_FRAME_COUNT)
    if clip_duration >= 70.0:
        frame_target = max(frame_target, 8)
    elif clip_duration >= 40.0:
        frame_target = max(frame_target, 6)
    elif clip_duration >= 20.0:
        frame_target = max(frame_target, 5)
    frame_target = max(1, min(10, frame_target))

    frames = _extract_clip_frames_base64(
        video_path=video_path,
        start=start,
        end=end,
        frame_count=frame_target,
        max_side=OLLAMA_VISION_MAX_SIDE,
    )
    if not frames:
        return default_result

    if OLLAMA_VISION_REQUIRE_GPU and OLLAMA_VISION_UNLOAD_CPU_FALLBACK:
        current_vram = _ollama_get_loaded_model_vram(OLLAMA_VISION_MODEL)
        if current_vram == 0:
            LOGGER.info(
                "Ollama vision model CPU-loaded (size_vram=0), forcing unload before retry on GPU"
            )
            _ollama_unload_model(OLLAMA_VISION_MODEL)

    prompt = f"""Tu analyses des images extraites d'un clip court.
Objectif: evaluer la qualite visuelle du moment et detecter une presentation voiture.

Contexte texte (optionnel):
\"\"\"{str(clip_text).strip()[:450]}\"\"\"

Contexte audio/signal (optionnel):
\"\"\"{str(audio_hint).strip()[:450]}\"\"\"

Hints:
- profile={str(profile_hint).strip()[:24]}
- tag={str(tag_hint).strip()[:24]}

Retourne du JSON strict (sans markdown):
{{
  "scene_type": "driving|showcase|interior|talking|other",
  "action_level": 0.0-1.0,
  "clip_quality": 0.0-1.0,
  "audio_visual_fit": 0.0-1.0,
  "is_car_showcase": true/false,
  "title_hint": "max 70 caracteres",
  "reason": "max 18 mots"
}}

Regles:
- is_car_showcase=true seulement si on voit surtout la voiture (exterieur/interieur detail).
- Si les images sont peu lisibles, baisser clip_quality.
- audio_visual_fit doit refleter la coherence entre signaux audio fournis et ce que montrent les images.
"""

    try:
        options: dict[str, Any] = {
            "temperature": 0.05,
            "num_predict": 180,
        }
        if OLLAMA_VISION_NUM_GPU >= -1:
            options["num_gpu"] = int(OLLAMA_VISION_NUM_GPU)

        payload: dict[str, Any] = {
            "model": OLLAMA_VISION_MODEL,
            "prompt": prompt,
            "images": frames,
            "stream": False,
            "format": "json",
            "options": options,
        }
        response = _post_ollama_generate(payload, timeout_seconds=OLLAMA_VISION_TIMEOUT)
        if response.status_code != 200:
            LOGGER.warning("Ollama vision API error: %s", response.status_code)
            return default_result

        result_text = response.json().get("response", "")
        parsed = _extract_json_object(result_text)
        if parsed is None:
            LOGGER.warning("Ollama vision: no JSON in response")
            return default_result

        scene_type = str(parsed.get("scene_type", "other")).strip().lower()
        if scene_type not in {"driving", "showcase", "interior", "talking", "other"}:
            scene_type = "other"

        title_hint = str(parsed.get("title_hint", "")).strip()
        title_hint = re.sub(r"\s+", " ", title_hint).strip()[:90]

        if OLLAMA_VISION_REQUIRE_GPU:
            vram_after = _ollama_get_loaded_model_vram(OLLAMA_VISION_MODEL)
            if vram_after is not None and vram_after <= 0:
                LOGGER.warning(
                    "Ollama vision GPU required but model is running on CPU (size_vram=%s)",
                    vram_after,
                )
                gpu_result = dict(default_result)
                gpu_result["reason"] = "gpu_unavailable"
                return gpu_result

        return {
            "vision_used": True,
            "scene_type": scene_type,
            "action_level": _clamp01(parsed.get("action_level", 0.5), 0.5),
            "clip_quality": _clamp01(parsed.get("clip_quality", 0.5), 0.5),
            "audio_visual_fit": _clamp01(parsed.get("audio_visual_fit", 0.5), 0.5),
            "is_car_showcase": _as_bool(parsed.get("is_car_showcase"), default=False),
            "title_hint": title_hint,
            "frame_count": len(frames),
            "reason": str(parsed.get("reason", ""))[:100],
        }
    except requests.exceptions.Timeout:
        LOGGER.warning("Ollama vision timeout after %.1fs", OLLAMA_VISION_TIMEOUT)
        timeout_result = dict(default_result)
        timeout_result["reason"] = "timeout"
        return timeout_result
    except requests.exceptions.ConnectionError:
        LOGGER.warning("Ollama not reachable at %s", OLLAMA_URL)
        return default_result
    except json.JSONDecodeError as exc:
        LOGGER.warning("Ollama vision JSON parse error: %s", exc)
        return default_result
    except Exception as exc:
        LOGGER.warning("Ollama vision error: %s", exc)
        return default_result


def _ollama_check_model_available(model_name: str, *, log_label: str) -> bool:
    if not OLLAMA_ENABLED:
        return False
    model_name = str(model_name).strip()
    if not model_name:
        return False
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code != 200:
            return False
        models = [str(m.get("name", "")) for m in response.json().get("models", [])]
        if any(model_name in model for model in models):
            LOGGER.info("Ollama %s disponible avec modele %s", log_label, model_name)
            return True
        LOGGER.warning("Modele Ollama %s non trouve: %s", log_label, model_name)
        return False
    except Exception:
        return False


def _ollama_check_available() -> bool:
    """Verifie si le modele texte Ollama est disponible."""
    return _ollama_check_model_available(OLLAMA_MODEL, log_label="texte")


def _ollama_check_vision_available() -> bool:
    """Verifie si le modele vision Ollama est disponible."""
    if not OLLAMA_VISION_ENABLED:
        return False
    return _ollama_check_model_available(OLLAMA_VISION_MODEL, log_label="vision")
