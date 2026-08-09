from __future__ import annotations

import re
from typing import Any

from worker.worker_config import CAR_EVENT_MIN_SCORE, WORD_RE
from worker.worker_keywords import HOOK_MARKERS, LAUGHTER_TOKENS, PUNCHLINE_MARKERS, TAG_KEYWORDS


TITLE_FILLER_PREFIXES = (
    "alors",
    "du coup",
    "en fait",
    "genre",
    "bref",
    "bon",
    "ok",
    "euh",
    "bah",
    "tu vois",
    "vous voyez",
    "attends",
    "attendez",
)

TITLE_WEAK_ENDINGS = {
    "quoi",
    "en fait",
    "genre",
    "bref",
    "tu vois",
    "vous voyez",
}

TITLE_BAD_OUTRO_PATTERNS = (
    "thanks for watching",
    "merci d'avoir regarde",
    "merci d avoir regarde",
    "takk for",
    "suscribete",
    "subscribe",
    "abonne toi",
)

def _format_mmss(seconds: float) -> str:
    total = int(max(0, round(float(seconds))))
    minutes = total // 60
    secs = total % 60
    return f"{minutes:02d}:{secs:02d}"

def _is_transcript_title_reliable(
    sentence: str,
    text_features: dict[str, Any],
    audio_features: dict[str, Any] | None,
) -> bool:
    if not sentence:
        return False

    lower = sentence.lower()
    if any(pattern in lower for pattern in TITLE_BAD_OUTRO_PATTERNS):
        return False

    words = WORD_RE.findall(lower)
    if len(words) < 4:
        return False

    if audio_features:
        clip_profile = str(audio_features.get("clip_profile", "")).strip().lower()
        words_per_sec = float(text_features.get("words_per_sec", 0.0))
        text_score = float(text_features.get("text_score", 0.0))
        dialogue_hits = int(text_features.get("dialogue_hits", 0))
        has_story_end = bool(text_features.get("has_story_end", False))
        has_hook = bool(text_features.get("has_hook", False))
        has_punchline = bool(text_features.get("has_punchline", False))
        if clip_profile == "car":
            if (
                words_per_sec < 1.10
                and text_score < 0.58
                and dialogue_hits < 1
                and not has_story_end
                and not has_hook
                and not has_punchline
            ):
                return False

    return True

def _build_car_title(
    start: float,
    end: float,
    tag: str,
    audio_features: dict[str, Any] | None,
) -> str:
    car_event_min_score = float(
        audio_features.get("car_event_min_score", CAR_EVENT_MIN_SCORE)
    ) if audio_features else float(CAR_EVENT_MIN_SCORE)
    car_start_score = float(audio_features.get("car_start_score", 0.0)) if audio_features else 0.0
    has_stationary_showcase = bool(
        audio_features and audio_features.get("car_stationary_showcase_event", False)
    )
    has_showcase_hard = bool(
        audio_features
        and (
            audio_features.get("car_showcase_event", False)
            or has_stationary_showcase
            or audio_features.get("ollama_vision_showcase", False)
        )
    )
    has_showcase_soft = bool(audio_features and audio_features.get("car_presentation_like", False))
    has_showcase = has_showcase_hard or has_showcase_soft
    visual_motion_score = float(audio_features.get("visual_motion_score", 0.0)) if audio_features else 0.0
    car_exterior_hint = bool(audio_features and audio_features.get("car_exterior_tour_text_hint", False))
    vision_showcase = bool(audio_features and audio_features.get("ollama_vision_showcase", False))
    vision_scene = str(audio_features.get("ollama_vision_scene", "")).strip().lower() if audio_features else ""
    has_start = bool(
        audio_features
        and (
            audio_features.get("car_start_event", False)
            or car_start_score >= car_event_min_score
        )
    )
    has_stop = bool(audio_features and audio_features.get("car_stop_event", False))
    has_strong = bool(audio_features and audio_features.get("car_strong_signal", False))
    has_motion = bool(audio_features and audio_features.get("visual_motion_event", False))
    has_insertion = bool(audio_features and audio_features.get("car_insertion_focus", False))
    has_launch = bool(audio_features and audio_features.get("car_start_from_launch", False))
    has_start_audio = bool(audio_features and audio_features.get("car_start_from_audio", False))
    has_start_visual = bool(audio_features and audio_features.get("car_start_from_visual", False))
    has_start_inferred = bool(audio_features and audio_features.get("car_start_from_inferred", False))
    has_start_scene_cut = bool(audio_features and audio_features.get("car_start_from_scene_cut", False))
    has_start_yamnet = bool(audio_features and audio_features.get("car_start_from_yamnet", False))
    start_confirmation_count = sum(
        1
        for flag in (
            has_launch,
            has_start_audio,
            has_start_visual,
            has_start_inferred,
            has_start_scene_cut,
            has_start_yamnet,
        )
        if flag
    )
    has_start_confident = bool(
        has_start
        and (
            has_launch
            or start_confirmation_count >= 2
            or car_start_score >= max(car_event_min_score + 0.08, 0.62)
        )
    )
    driving_like = bool(
        not has_stationary_showcase
        and not car_exterior_hint
        and not vision_showcase
        and (
            has_insertion
            or has_start_confident
            or has_strong
            or vision_scene == "driving"
            or visual_motion_score >= 0.62
        )
    )
    is_presentation = bool(
        (
            has_showcase_hard
            or (
                has_showcase_soft
                and not has_start_confident
                and not has_strong
            )
            or (
                str(tag).strip().lower() == "presentation"
                and not has_start_confident
            )
            or has_stationary_showcase
        )
        and not driving_like
        and not has_insertion
        and not has_launch
    )

    if has_stationary_showcase and is_presentation:
        core = "Presentation voiture a l'arret"
    elif is_presentation:
        core = "Presentation complete de la voiture"
    elif has_showcase and driving_like:
        core = "Passage autoroute a haute vitesse"
    elif has_showcase and not has_insertion and not has_launch:
        core = "Presentation voiture puis acceleration"
    elif has_insertion:
        core = "Insertion autoroute et relance franche"
    elif has_launch and has_start_confident and has_strong:
        core = "Depart arrete puis acceleration"
    elif has_start_confident and has_strong:
        core = "Depart canon et montee moteur"
    elif has_stop and has_strong:
        core = "Acceleration puis freinage appuye"
    elif has_strong:
        core = "Acceleration moteur en pleine charge"
    elif has_start_confident:
        core = "Depart voiture bien senti"
    elif has_stop:
        core = "Freinage net a haute vitesse"
    elif has_motion:
        core = "Passage autoroute a haute vitesse"
    elif str(tag).strip().lower() == "tension":
        core = "Moment tension sur autoroute"
    else:
        core = "Sequence voiture a haute intensite"

    timecode = f"{_format_mmss(start)}-{_format_mmss(end)}"
    title = f"{core} | {timecode}"
    if len(title) > 80:
        title = title[:77].rstrip() + "..."
    return title

def _clean_vision_title_hint(hint: str) -> str:
    if not hint:
        return ""
    hint = re.sub(r"\s+", " ", str(hint)).strip()
    hint = hint.strip(" \"'")
    if not hint:
        return ""

    lower = hint.lower()
    if any(pattern in lower for pattern in TITLE_BAD_OUTRO_PATTERNS):
        return ""

    words = WORD_RE.findall(lower)
    if len(words) < 3:
        return ""

    hint = hint.strip(" ,:;.-")
    if not hint:
        return ""
    hint = hint[0].upper() + hint[1:]
    if len(hint) > 80:
        hint = hint[:77].rstrip() + "..."
    return hint

def _clip_text_snippet(
    start: float, end: float, transcript_segments: list[dict[str, Any]]
) -> str:
    overlaps = [
        seg for seg in transcript_segments if seg["end"] >= start and seg["start"] <= end
    ]
    if not overlaps:
        return ""
    text = " ".join(seg["text"] for seg in overlaps)
    text = re.sub(r"\\s+", " ", text).strip()
    if not text:
        return ""
    sentence = re.split(r"[.!?]", text)[0].strip()
    if not sentence:
        sentence = text
    words = sentence.split()
    if len(words) > 12:
        sentence = " ".join(words[:12])
    return sentence

def _clean_title_sentence(sentence: str) -> str:
    sentence = re.sub(r"\s+", " ", sentence).strip()
    if not sentence:
        return ""
    sentence = sentence.strip(" \"'“”’")
    sentence = sentence.lstrip("-–—• ")
    lower = sentence.lower()

    for prefix in TITLE_FILLER_PREFIXES:
        if lower.startswith(prefix + " "):
            sentence = sentence[len(prefix):].lstrip(" ,:;.-—")
            lower = sentence.lower()
            break

    sentence = sentence.strip(" ,:;.-—")
    lower = sentence.lower()
    for ending in TITLE_WEAK_ENDINGS:
        if lower.endswith(" " + ending) or lower == ending:
            sentence = re.sub(
                rf"(?:\b{re.escape(ending)}\b\s*)$",
                "",
                sentence,
                flags=re.IGNORECASE,
            ).strip(" ,:;.-—")
            lower = sentence.lower()
            break

    if not sentence:
        return ""
    return sentence[0].upper() + sentence[1:]

def _score_title_sentence(
    sentence: str, text_features: dict[str, Any], tag: str | None
) -> float:
    lower = sentence.lower()
    words = WORD_RE.findall(lower)
    if not words:
        return 0.0

    length = len(words)
    if length <= 2:
        return 0.0

    length_score = 1.0 - min(1.0, abs(length - 9) / 10.0)
    punctuation_score = 0.0
    if "?" in sentence:
        punctuation_score += 0.3
    if "!" in sentence:
        punctuation_score += 0.2

    hook_score = 0.25 if any(hook in lower for hook in HOOK_MARKERS) else 0.0
    punch_score = 0.25 if any(punch in lower for punch in PUNCHLINE_MARKERS) else 0.0
    laugh_score = 0.2 if any(token in words for token in LAUGHTER_TOKENS) else 0.0

    tag_score = 0.0
    for key in filter(None, [tag, text_features.get("text_tag")]):
        keywords = TAG_KEYWORDS.get(key, set())
        if keywords and any(word in keywords for word in words):
            tag_score = 0.2
            break

    penalty = 0.0
    if length > 18:
        penalty += 0.3
    if length < 4:
        penalty += 0.2

    return max(0.0, length_score + punctuation_score + hook_score + punch_score + laugh_score + tag_score - penalty)

def _best_title_sentence(
    start: float,
    end: float,
    transcript_segments: list[dict[str, Any]],
    text_features: dict[str, Any],
    tag: str | None,
) -> str:
    overlaps = [
        seg for seg in transcript_segments if seg["end"] >= start and seg["start"] <= end
    ]
    if not overlaps:
        return ""
    text = " ".join(seg["text"] for seg in overlaps)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""

    candidates = re.split(r"(?<=[.!?…])\s+", text)
    if len(candidates) == 1:
        candidates = re.split(r"[;,•—-]\s+", text)

    best_sentence = ""
    best_score = 0.0
    for candidate in candidates:
        cleaned = _clean_title_sentence(candidate)
        if not cleaned:
            continue
        score = _score_title_sentence(cleaned, text_features, tag)
        if score > best_score:
            best_score = score
            best_sentence = cleaned

    if not best_sentence:
        return ""

    words = best_sentence.split()
    if len(words) > 16:
        best_sentence = " ".join(words[:16]).rstrip(" ,:;.-—") + "..."
    return best_sentence

def _build_tiktok_title(
    tag: str,
    start: float,
    end: float,
    transcript_segments: list[dict[str, Any]],
    text_features: dict[str, Any],
    audio_features: dict[str, Any] | None = None,
) -> str:
    text_tag = text_features.get("text_tag")
    prefix = (text_tag or tag or "clip").upper()
    sentence = _best_title_sentence(start, end, transcript_segments, text_features, tag)
    use_sentence = _is_transcript_title_reliable(sentence, text_features, audio_features)
    clip_profile = str((audio_features or {}).get("clip_profile", "")).strip().lower()
    vision_hint = _clean_vision_title_hint(
        str((audio_features or {}).get("ollama_vision_title", "")).strip()
    )
    if use_sentence:
        title = sentence
    elif vision_hint:
        title = vision_hint
    elif clip_profile == "car":
        title = _build_car_title(start, end, tag, audio_features)
    else:
        snippet = _clip_text_snippet(start, end, transcript_segments)
        if snippet:
            title = snippet
        else:
            title = f"{prefix}: moment à voir"
    if len(title) > 80:
        title = title[:77].rstrip() + "..."
    return title
