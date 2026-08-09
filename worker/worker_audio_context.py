from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from worker.worker_config import (
    ANALYSIS_CACHE_MAX_ITEMS,
    ANALYSIS_WINDOW_SECONDS,
    INASPEECH_CONTEXT_SMOOTH_SECONDS,
    OPENSMILE_FEATURE_SET,
    OPENSMILE_SMOOTH_SECONDS,
)
from worker.worker_logging import LOGGER
from worker.worker_utils import _cache_set_bounded, _moving_average

try:
    import opensmile

    OPENSMILE_AVAILABLE = True
except Exception:
    opensmile = None
    OPENSMILE_AVAILABLE = False

try:
    from inaSpeechSegmenter import Segmenter as InaSpeechSegmenter

    INASPEECH_AVAILABLE = True
except Exception:
    InaSpeechSegmenter = None
    INASPEECH_AVAILABLE = False

_OPENSMILE_EXTRACTOR: Any | None = None
_OPENSMILE_DISABLED = False
_INASPEECH_SEGMENTER: Any | None = None
_INASPEECH_DISABLED = False

_OPENSMILE_SERIES_CACHE: dict[str, list[tuple[float, float]]] = {}
_INASPEECH_CONTEXT_CACHE: dict[str, list[tuple[float, float, float, float]]] = {}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize(values: np.ndarray) -> np.ndarray:
    if values.size == 0:
        return values
    v_min = float(np.min(values))
    v_max = float(np.max(values))
    if (v_max - v_min) < 1e-9:
        return np.zeros_like(values, dtype=np.float64)
    return (values - v_min) / (v_max - v_min)


def _value_to_seconds(value: Any) -> float | None:
    if value is None:
        return None
    if hasattr(value, "total_seconds"):
        try:
            return float(value.total_seconds())
        except Exception:
            return None
    if isinstance(value, tuple):
        for item in value:
            seconds = _value_to_seconds(item)
            if seconds is not None:
                return seconds
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _resolve_opensmile_feature_set() -> Any | None:
    if opensmile is None:
        return None

    requested = OPENSMILE_FEATURE_SET.strip().lower()
    aliases = {
        "egemaps": "eGeMAPSv02",
        "egemapsv02": "eGeMAPSv02",
        "compare": "ComParE_2016",
        "compare_2016": "ComParE_2016",
        "emobase": "emobase",
    }
    wanted = aliases.get(requested, OPENSMILE_FEATURE_SET)

    for attr in dir(opensmile.FeatureSet):
        if attr.lower() == str(wanted).lower():
            return getattr(opensmile.FeatureSet, attr)

    if hasattr(opensmile.FeatureSet, "eGeMAPSv02"):
        return getattr(opensmile.FeatureSet, "eGeMAPSv02")
    return None


def _get_opensmile_extractor() -> Any | None:
    global _OPENSMILE_EXTRACTOR, _OPENSMILE_DISABLED
    if not OPENSMILE_AVAILABLE or opensmile is None:
        return None
    if _OPENSMILE_DISABLED:
        return None
    if _OPENSMILE_EXTRACTOR is not None:
        return _OPENSMILE_EXTRACTOR

    feature_set = _resolve_opensmile_feature_set()
    if feature_set is None:
        _OPENSMILE_DISABLED = True
        return None

    feature_level = getattr(opensmile.FeatureLevel, "LowLevelDescriptors", None)
    if feature_level is None:
        _OPENSMILE_DISABLED = True
        return None

    try:
        _OPENSMILE_EXTRACTOR = opensmile.Smile(
            feature_set=feature_set,
            feature_level=feature_level,
        )
        return _OPENSMILE_EXTRACTOR
    except Exception as exc:
        LOGGER.info("openSMILE unavailable: %s", exc)
        _OPENSMILE_EXTRACTOR = None
        _OPENSMILE_DISABLED = True
        return None


def _get_inaspeech_segmenter() -> Any | None:
    global _INASPEECH_SEGMENTER, _INASPEECH_DISABLED
    if not INASPEECH_AVAILABLE or InaSpeechSegmenter is None:
        return None
    if _INASPEECH_DISABLED:
        return None
    if _INASPEECH_SEGMENTER is not None:
        return _INASPEECH_SEGMENTER

    try:
        _INASPEECH_SEGMENTER = InaSpeechSegmenter()
        return _INASPEECH_SEGMENTER
    except Exception as exc:
        LOGGER.info("inaSpeechSegmenter unavailable: %s", exc)
        _INASPEECH_SEGMENTER = None
        _INASPEECH_DISABLED = True
        return None


def _pick_column_names(columns: list[str], tokens: tuple[str, ...]) -> list[str]:
    selected: list[str] = []
    for name in columns:
        lowered = name.lower()
        if any(token in lowered for token in tokens):
            selected.append(name)
    return selected


def _bucket_series(
    times: list[float],
    values: np.ndarray,
    window_seconds: float,
) -> list[tuple[float, float]]:
    bucket_values: dict[int, list[float]] = {}
    safe_window = max(0.05, window_seconds)

    for ts, value in zip(times, values):
        if ts < 0:
            continue
        idx = int(ts / safe_window)
        bucket_values.setdefault(idx, []).append(float(value))

    series: list[tuple[float, float]] = []
    for idx in sorted(bucket_values):
        vals = bucket_values[idx]
        if not vals:
            continue
        series.append((idx * safe_window, float(np.mean(vals))))
    return series


def _compute_opensmile_voice_activity_series(
    audio_path: Path,
    window_seconds: float = ANALYSIS_WINDOW_SECONDS,
) -> list[tuple[float, float]]:
    """
    Compute a voice dynamics series using openSMILE low-level descriptors.

    Returns [(timestamp, score_0_to_1)], where higher values indicate stronger
    voice arousal/prosodic change.
    """
    if not OPENSMILE_AVAILABLE:
        return []

    cache_key = f"{audio_path}|opensmile|{window_seconds:.3f}|{OPENSMILE_FEATURE_SET}"
    if cache_key in _OPENSMILE_SERIES_CACHE:
        return _OPENSMILE_SERIES_CACHE[cache_key]

    extractor = _get_opensmile_extractor()
    if extractor is None:
        return []

    try:
        frame_df = extractor.process_file(str(audio_path))
    except Exception as exc:
        LOGGER.info("openSMILE extraction failed: %s", exc)
        return []

    if frame_df is None or getattr(frame_df, "empty", True):
        _cache_set_bounded(
            _OPENSMILE_SERIES_CACHE,
            cache_key,
            [],
            ANALYSIS_CACHE_MAX_ITEMS,
        )
        return []

    numeric_df = frame_df.select_dtypes(include=["number"])
    if numeric_df.empty:
        _cache_set_bounded(
            _OPENSMILE_SERIES_CACHE,
            cache_key,
            [],
            ANALYSIS_CACHE_MAX_ITEMS,
        )
        return []

    col_names = [str(col) for col in numeric_df.columns]
    energy_cols = _pick_column_names(
        col_names,
        ("loudness", "energy", "rms", "intensity", "pcm"),
    )
    pitch_cols = _pick_column_names(
        col_names,
        ("f0", "pitch", "semitone"),
    )
    quality_cols = _pick_column_names(
        col_names,
        ("jitter", "shimmer", "hnr", "harmonic", "voicing"),
    )

    if energy_cols:
        energy = np.asarray(numeric_df[energy_cols].mean(axis=1), dtype=np.float64)
    else:
        energy = np.asarray(numeric_df.mean(axis=1), dtype=np.float64)

    if pitch_cols:
        pitch = np.asarray(numeric_df[pitch_cols].mean(axis=1), dtype=np.float64)
    else:
        pitch = np.zeros_like(energy)

    if quality_cols:
        quality = np.asarray(numeric_df[quality_cols].mean(axis=1), dtype=np.float64)
    else:
        quality = np.zeros_like(energy)

    energy_n = _normalize(np.nan_to_num(energy, nan=0.0))
    pitch_n = _normalize(np.nan_to_num(pitch, nan=0.0))
    quality_n = _normalize(np.nan_to_num(quality, nan=0.0))

    energy_delta = np.maximum(0.0, np.diff(energy_n, prepend=energy_n[0]))
    pitch_delta = np.abs(np.diff(pitch_n, prepend=pitch_n[0]))

    score = (
        energy_n * 0.45
        + energy_delta * 0.30
        + pitch_delta * 0.17
        + quality_n * 0.08
    )
    score = np.clip(score, 0.0, 1.0)

    times: list[float] = []
    for idx_value in list(frame_df.index):
        seconds = _value_to_seconds(idx_value)
        if seconds is None:
            seconds = len(times) * 0.01
        times.append(max(0.0, seconds))

    series = _bucket_series(times, score, window_seconds)
    if series:
        smooth_frames = max(
            1,
            int(round(max(0.1, OPENSMILE_SMOOTH_SECONDS) / max(0.05, window_seconds))),
        )
        if smooth_frames > 1:
            vals = np.array([v for _, v in series], dtype=np.float64)
            smoothed = _moving_average(vals, smooth_frames)
            series = [
                (series[idx][0], float(np.clip(smoothed[idx], 0.0, 1.0)))
                for idx in range(len(series))
            ]

    _cache_set_bounded(
        _OPENSMILE_SERIES_CACHE,
        cache_key,
        series,
        ANALYSIS_CACHE_MAX_ITEMS,
    )
    return series


def _compute_inaspeech_context_series(
    audio_path: Path,
    window_seconds: float = ANALYSIS_WINDOW_SECONDS,
) -> list[tuple[float, float, float, float]]:
    """
    Compute context ratios from inaSpeechSegmenter.

    Returns [(timestamp, speech_ratio, music_ratio, noise_ratio)].
    """
    if not INASPEECH_AVAILABLE:
        return []

    cache_key = f"{audio_path}|inaspeech|{window_seconds:.3f}"
    if cache_key in _INASPEECH_CONTEXT_CACHE:
        return _INASPEECH_CONTEXT_CACHE[cache_key]

    segmenter = _get_inaspeech_segmenter()
    if segmenter is None:
        return []

    try:
        raw_segments = segmenter(str(audio_path))
    except Exception as exc:
        LOGGER.info("inaSpeechSegmenter failed: %s", exc)
        return []

    parsed: list[tuple[str, float, float]] = []
    max_end = 0.0

    for item in raw_segments or []:
        if not isinstance(item, (tuple, list)) or len(item) < 3:
            continue
        label = str(item[0]).strip().lower()
        start = _safe_float(item[1], -1.0)
        end = _safe_float(item[2], -1.0)
        if start < 0 or end <= start:
            continue

        kind = ""
        if "music" in label:
            kind = "music"
        elif "noise" in label or "noenergy" in label:
            kind = "noise"
        elif (
            "speech" in label
            or "male" in label
            or "female" in label
            or "voice" in label
        ):
            kind = "speech"

        if not kind:
            continue

        parsed.append((kind, start, end))
        if end > max_end:
            max_end = end

    if not parsed or max_end <= 0:
        _cache_set_bounded(
            _INASPEECH_CONTEXT_CACHE,
            cache_key,
            [],
            ANALYSIS_CACHE_MAX_ITEMS,
        )
        return []

    safe_window = max(0.05, window_seconds)
    total_windows = max(1, int(np.ceil(max_end / safe_window)))

    speech = np.zeros(total_windows, dtype=np.float64)
    music = np.zeros(total_windows, dtype=np.float64)
    noise = np.zeros(total_windows, dtype=np.float64)

    for idx in range(total_windows):
        win_start = idx * safe_window
        win_end = win_start + safe_window

        speech_overlap = 0.0
        music_overlap = 0.0
        noise_overlap = 0.0

        for kind, seg_start, seg_end in parsed:
            overlap = max(0.0, min(win_end, seg_end) - max(win_start, seg_start))
            if overlap <= 0:
                continue
            if kind == "speech":
                speech_overlap += overlap
            elif kind == "music":
                music_overlap += overlap
            elif kind == "noise":
                noise_overlap += overlap

        speech[idx] = min(1.0, speech_overlap / safe_window)
        music[idx] = min(1.0, music_overlap / safe_window)
        noise[idx] = min(1.0, noise_overlap / safe_window)

    smooth_frames = max(
        1,
        int(
            round(
                max(0.1, INASPEECH_CONTEXT_SMOOTH_SECONDS)
                / max(0.05, safe_window)
            )
        ),
    )
    if smooth_frames > 1:
        speech = np.clip(_moving_average(speech, smooth_frames), 0.0, 1.0)
        music = np.clip(_moving_average(music, smooth_frames), 0.0, 1.0)
        noise = np.clip(_moving_average(noise, smooth_frames), 0.0, 1.0)

    series: list[tuple[float, float, float, float]] = []
    for idx in range(total_windows):
        ts = idx * safe_window
        series.append((ts, float(speech[idx]), float(music[idx]), float(noise[idx])))

    _cache_set_bounded(
        _INASPEECH_CONTEXT_CACHE,
        cache_key,
        series,
        ANALYSIS_CACHE_MAX_ITEMS,
    )
    return series
