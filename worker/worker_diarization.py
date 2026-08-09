from __future__ import annotations

import importlib
import importlib.util
import inspect
import os
from pathlib import Path
from typing import Any

from worker.worker_config import ANALYSIS_CACHE_MAX_ITEMS
from worker.worker_logging import LOGGER
from worker.worker_utils import _cache_set_bounded

# Optional dependency: load lazily to avoid hard import failures in environments
# where pyannote is not installed.
def _has_pyannote() -> bool:
    try:
        return importlib.util.find_spec("pyannote.audio") is not None
    except Exception:
        return False


PYANNOTE_AVAILABLE = _has_pyannote()

_PYANNOTE_PIPELINE_CACHE: Any | None = None
_PYANNOTE_PIPELINE_CLASS: Any | None = None
_DIARIZATION_CACHE: dict[str, list[dict[str, Any]]] = {}
_PYANNOTE_DISABLED = False
_TF32_OPTIMIZATION_DONE = False
_AUTH_ERROR_TOKENS = (
    "401",
    "403",
    "unauthorized",
    "forbidden",
    "authentication",
    "use_auth_token",
    "token",
    "gated",
    "permission",
)


def _release_pyannote_pipeline_cache(*, clear_segments_cache: bool = False) -> bool:
    """
    Releases cached pyannote pipeline to free CUDA memory when vision takes priority.
    Returns True when a pipeline instance was present.
    """
    global _PYANNOTE_PIPELINE_CACHE

    pipeline = _PYANNOTE_PIPELINE_CACHE
    had_pipeline = pipeline is not None

    if pipeline is not None and hasattr(pipeline, "to"):
        try:
            import torch

            pipeline.to(torch.device("cpu"))
        except Exception:
            pass

    _PYANNOTE_PIPELINE_CACHE = None
    if clear_segments_cache:
        _DIARIZATION_CACHE.clear()

    if had_pipeline:
        LOGGER.info("pyannote pipeline cache released")
    return had_pipeline


def _enable_tf32_for_pyannote() -> None:
    global _TF32_OPTIMIZATION_DONE
    if _TF32_OPTIMIZATION_DONE:
        return
    _TF32_OPTIMIZATION_DONE = True

    try:
        import torch
    except Exception:
        return

    if not torch.cuda.is_available():
        return

    try:
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
    except Exception:
        return

    # pyannote disables TF32 in fix_reproducibility(). Override it to keep TF32 enabled.
    try:
        reproducibility = importlib.import_module("pyannote.audio.utils.reproducibility")
        core_pipeline = importlib.import_module("pyannote.audio.core.pipeline")
        core_inference = importlib.import_module("pyannote.audio.core.inference")

        def _keep_tf32(_device: Any) -> None:
            return

        reproducibility.fix_reproducibility = _keep_tf32
        core_pipeline.fix_reproducibility = _keep_tf32
        core_inference.fix_reproducibility = _keep_tf32
    except Exception as exc:
        LOGGER.info("TF32 enabled on CUDA, but pyannote patch failed: %s", exc)
        return

    LOGGER.info("TF32 enabled on CUDA for pyannote diarization.")


def _get_pyannote_pipeline_class() -> Any | None:
    global _PYANNOTE_PIPELINE_CLASS, PYANNOTE_AVAILABLE
    if _PYANNOTE_PIPELINE_CLASS is not None:
        return _PYANNOTE_PIPELINE_CLASS
    if not PYANNOTE_AVAILABLE:
        return None
    try:
        module = importlib.import_module("pyannote.audio")
        _enable_tf32_for_pyannote()
        _PYANNOTE_PIPELINE_CLASS = getattr(module, "Pipeline", None)
        if _PYANNOTE_PIPELINE_CLASS is None:
            PYANNOTE_AVAILABLE = False
        return _PYANNOTE_PIPELINE_CLASS
    except Exception:
        PYANNOTE_AVAILABLE = False
        return None


def _is_auth_related_error(error_value: Exception | str) -> bool:
    message = str(error_value).lower()
    return any(token in message for token in _AUTH_ERROR_TOKENS)


def _build_pyannote_auth_kwargs(
    pipeline_class: Any,
    hf_token: str | None,
) -> dict[str, Any]:
    if not hf_token:
        return {}
    try:
        signature = inspect.signature(pipeline_class.from_pretrained)
        parameters = signature.parameters
    except Exception:
        # Conservative fallback for older pyannote APIs.
        return {"use_auth_token": hf_token}

    if "token" in parameters:
        return {"token": hf_token}
    if "use_auth_token" in parameters:
        return {"use_auth_token": hf_token}
    return {}


def _load_pyannote_pipeline(pipeline_class: Any) -> Any:
    hf_token = os.getenv("HF_TOKEN", None)
    auth_kwargs = _build_pyannote_auth_kwargs(pipeline_class, hf_token)
    candidates: list[tuple[str, dict[str, Any]]] = []
    if hf_token:
        candidates.append(
            (
                "pyannote/speaker-diarization-3.1",
                dict(auth_kwargs),
            )
        )
    candidates.append(
        (
            "pyannote/speaker-diarization",
            dict(auth_kwargs),
        )
    )

    last_exc: Exception | None = None
    for model_id, kwargs in candidates:
        try:
            LOGGER.info("Loading pyannote pipeline: %s", model_id)
            return pipeline_class.from_pretrained(model_id, **kwargs)
        except Exception as exc:
            last_exc = exc
            LOGGER.info("pyannote pipeline %s unavailable: %s", model_id, exc)
            continue

    if last_exc is not None:
        raise last_exc
    raise RuntimeError("no_pyannote_pipeline_available")


def _iter_speaker_segments(diarization_output: Any) -> list[dict[str, Any]]:
    """
    Normalize pyannote diarization outputs across API versions.

    Newer pyannote may return a DiarizeOutput wrapper exposing
    `exclusive_speaker_diarization` / `speaker_diarization` instead of
    an Annotation with `itertracks()` directly.
    """
    annotation = diarization_output

    if hasattr(diarization_output, "exclusive_speaker_diarization"):
        candidate = getattr(diarization_output, "exclusive_speaker_diarization")
        if candidate is not None:
            annotation = candidate
    elif hasattr(diarization_output, "speaker_diarization"):
        candidate = getattr(diarization_output, "speaker_diarization")
        if candidate is not None:
            annotation = candidate

    segments: list[dict[str, Any]] = []
    if hasattr(annotation, "itertracks"):
        for turn, _, speaker in annotation.itertracks(yield_label=True):
            start = float(turn.start)
            end = float(turn.end)
            if end <= start:
                continue
            segments.append(
                {
                    "start": start,
                    "end": end,
                    "speaker": str(speaker),
                }
            )
        return segments

    if hasattr(diarization_output, "serialize"):
        serialized = diarization_output.serialize()
        diarization_entries = []
        if isinstance(serialized, dict):
            diarization_entries = (
                serialized.get("exclusive_diarization")
                or serialized.get("diarization")
                or []
            )
        if isinstance(diarization_entries, list):
            for item in diarization_entries:
                if not isinstance(item, dict):
                    continue
                start = float(item.get("start", 0.0))
                end = float(item.get("end", start))
                if end <= start:
                    continue
                segments.append(
                    {
                        "start": start,
                        "end": end,
                        "speaker": str(item.get("speaker", "")),
                    }
                )
            return segments

    if isinstance(diarization_output, dict):
        diarization_entries = (
            diarization_output.get("exclusive_diarization")
            or diarization_output.get("diarization")
            or []
        )
        if isinstance(diarization_entries, list):
            for item in diarization_entries:
                if not isinstance(item, dict):
                    continue
                start = float(item.get("start", 0.0))
                end = float(item.get("end", start))
                if end <= start:
                    continue
                segments.append(
                    {
                        "start": start,
                        "end": end,
                        "speaker": str(item.get("speaker", "")),
                    }
                )
            return segments

    raise TypeError(
        f"Unsupported diarization output type: {type(diarization_output).__name__}"
    )


def _build_pyannote_input(audio_path: Path) -> Any:
    """
    Build an in-memory AudioFile payload for pyannote when possible.

    This avoids pyannote internal decoding paths that rely on torchcodec.
    Fallback to plain path string when in-memory loading is unavailable.
    """
    try:
        import soundfile as sf
        import torch

        waveform, sample_rate = sf.read(
            str(audio_path),
            dtype="float32",
            always_2d=True,
        )
        if waveform.size == 0:
            return str(audio_path)

        # soundfile returns (time, channels); pyannote expects (channels, time)
        tensor = torch.from_numpy(waveform.T)
        return {
            "waveform": tensor,
            "sample_rate": int(sample_rate),
        }
    except Exception:
        return str(audio_path)


def _get_speaker_diarization(audio_path: Path, duration: float) -> list[dict[str, Any]]:
    """
    Uses pyannote.audio to identify who speaks when.

    Format: [{"start": 0.0, "end": 3.5, "speaker": "SPEAKER_00"}, ...]
    """
    global _PYANNOTE_PIPELINE_CACHE, _PYANNOTE_DISABLED

    _ = duration
    cache_key = str(audio_path)
    if cache_key in _DIARIZATION_CACHE:
        return _DIARIZATION_CACHE[cache_key]

    if _PYANNOTE_DISABLED:
        return []

    pipeline_class = _get_pyannote_pipeline_class()
    if pipeline_class is None:
        return []

    # Load pipeline once and reuse it for subsequent calls.
    if _PYANNOTE_PIPELINE_CACHE is None:
        try:
            _PYANNOTE_PIPELINE_CACHE = _load_pyannote_pipeline(pipeline_class)
            LOGGER.info("pyannote speaker diarization pipeline loaded")
        except Exception as e:
            LOGGER.warning("Unable to load pyannote diarization pipeline: %s", e)
            if _is_auth_related_error(e):
                _PYANNOTE_DISABLED = True
            return []

    pipeline = _PYANNOTE_PIPELINE_CACHE
    try:
        diarization = pipeline(_build_pyannote_input(audio_path))
    except Exception as e:
        LOGGER.warning("Speaker diarization run failed: %s", e)
        return []

    try:
        segments = _iter_speaker_segments(diarization)
        segments.sort(key=lambda item: item["start"])

        _cache_set_bounded(
            _DIARIZATION_CACHE,
            cache_key,
            segments,
            ANALYSIS_CACHE_MAX_ITEMS,
        )
        LOGGER.info(
            "Diarization: %d segments, %d speakers",
            len(segments),
            len(set(s["speaker"] for s in segments)),
        )
        return segments

    except Exception as e:
        LOGGER.warning("Speaker diarization failed: %s", e)
        return []
