from __future__ import annotations

from pathlib import Path
import csv

import numpy as np

from worker.worker_config import ANALYSIS_CACHE_MAX_ITEMS, YAMNET_HANDLE, YAMNET_LOCAL_ONLY
from worker.worker_logging import LOGGER
from worker.worker_utils import _cache_set_bounded, _moving_average

try:
    import librosa
    LIBROSA_AVAILABLE = True
except Exception:
    librosa = None
    LIBROSA_AVAILABLE = False

try:
    import tensorflow as tf
    import tensorflow_hub as hub

    YAMNET_AVAILABLE = True
except Exception:
    tf = None
    hub = None
    YAMNET_AVAILABLE = False

_YAMNET_MODEL = None
_YAMNET_CLASS_NAMES: list[str] = []
_YAMNET_ENGINE_CACHE: dict[str, list[tuple[float, float]]] = {}
_YAMNET_EVENT_CACHE: dict[str, tuple[list[tuple[float, float]], list[tuple[float, float]]]] = {}
_YAMNET_DISABLED = False
YAMNET_PATCH_HOP_SECONDS = 0.48


def _load_yamnet() -> tuple[object | None, list[str]]:
    global _YAMNET_MODEL, _YAMNET_CLASS_NAMES, _YAMNET_DISABLED
    if not YAMNET_AVAILABLE or hub is None:
        return None, []
    if _YAMNET_DISABLED:
        return None, []

    if _YAMNET_MODEL is not None and _YAMNET_CLASS_NAMES:
        return _YAMNET_MODEL, _YAMNET_CLASS_NAMES

    handle = YAMNET_HANDLE.strip()
    if YAMNET_LOCAL_ONLY:
        if handle.startswith(("http://", "https://")):
            LOGGER.info(
                "YAMNet local-only enabled; remote handle disabled (%s).",
                handle,
            )
            _YAMNET_DISABLED = True
            return None, []
        if not Path(handle).exists():
            LOGGER.info("YAMNet local-only enabled; model path not found: %s", handle)
            _YAMNET_DISABLED = True
            return None, []

    try:
        _YAMNET_MODEL = hub.load(handle)
        class_map_path = _YAMNET_MODEL.class_map_path().numpy()
        if isinstance(class_map_path, bytes):
            class_map_path = class_map_path.decode("utf-8")

        names: list[str] = []
        with open(class_map_path, "r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                names.append(str(row.get("display_name", "")).strip())
        _YAMNET_CLASS_NAMES = names
        LOGGER.info("YAMNet loaded (%d classes)", len(_YAMNET_CLASS_NAMES))
        return _YAMNET_MODEL, _YAMNET_CLASS_NAMES
    except Exception as exc:
        LOGGER.info("YAMNet unavailable: %s", exc)
        _YAMNET_MODEL = None
        _YAMNET_CLASS_NAMES = []
        _YAMNET_DISABLED = True
        return None, []


def _indices_for_tokens(class_names: list[str], tokens: tuple[str, ...]) -> list[int]:
    out: list[int] = []
    for idx, name in enumerate(class_names):
        lowered = name.lower()
        if any(tok in lowered for tok in tokens):
            out.append(idx)
    return out


def _reduce_score(scores: np.ndarray, indices: list[int]) -> np.ndarray:
    if not indices:
        return np.zeros(scores.shape[0], dtype=np.float64)
    return np.max(scores[:, indices], axis=1).astype(np.float64)


def _compute_yamnet_engine_series(audio_path: Path) -> list[tuple[float, float]]:
    """
    Compute an engine-related series with YAMNet (AudioSet classes).
    Returns [(timestamp, score_0_to_1)].
    """
    if not YAMNET_AVAILABLE or not LIBROSA_AVAILABLE or librosa is None:
        return []

    cache_key = str(audio_path)
    if cache_key in _YAMNET_ENGINE_CACHE:
        return _YAMNET_ENGINE_CACHE[cache_key]

    model, class_names = _load_yamnet()
    if model is None or not class_names:
        return []

    try:
        waveform, sr = librosa.load(str(audio_path), sr=16000, mono=True)
        if waveform.size < int(sr * 0.96):
            return []

        if tf is None:
            return []

        scores, _, _ = model(tf.convert_to_tensor(waveform, dtype=tf.float32))
        scores_np = np.array(scores.numpy(), dtype=np.float64)
        if scores_np.size == 0:
            return []

        start_idx = _indices_for_tokens(class_names, ("engine starting",))
        accel_idx = _indices_for_tokens(class_names, ("accelerating, revving, vroom", "revving", "vroom"))
        idle_idx = _indices_for_tokens(class_names, ("idling",))
        # Broad engine/motor cues (kept as supportive, not standalone).
        engine_idx = _indices_for_tokens(class_names, ("engine", "motor vehicle"))

        start_scores = _reduce_score(scores_np, start_idx)
        accel_scores = _reduce_score(scores_np, accel_idx)
        idle_scores = _reduce_score(scores_np, idle_idx)
        engine_scores = _reduce_score(scores_np, engine_idx)

        combined = np.maximum.reduce(
            [
                start_scores * 1.00,
                accel_scores * 0.95,
                idle_scores * 0.60,
                engine_scores * 0.75,
            ]
        )
        combined = np.clip(combined, 0.0, 1.0)

        times = np.arange(combined.shape[0], dtype=np.float64) * YAMNET_PATCH_HOP_SECONDS
        series = list(zip(times.tolist(), combined.astype(float).tolist()))
        _cache_set_bounded(
            _YAMNET_ENGINE_CACHE,
            cache_key,
            series,
            ANALYSIS_CACHE_MAX_ITEMS,
        )
        return series
    except Exception as exc:
        LOGGER.info("YAMNet engine series failed: %s", exc)
        return []


def _compute_yamnet_car_start_stop_events(
    audio_path: Path,
    *,
    start_threshold: float = 0.35,
    stop_threshold: float = 0.30,
    min_delta: float = 0.08,
    smooth_seconds: float = 1.0,
    cooldown_seconds: float = 2.0,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """
    Detect start/stop events from YAMNet engine-related series.
    Returns (start_events, stop_events) where each event is (timestamp, confidence).
    """
    cache_key = (
        f"{audio_path}|{start_threshold:.3f}|{stop_threshold:.3f}|{min_delta:.3f}|"
        f"{smooth_seconds:.3f}|{cooldown_seconds:.3f}"
    )
    if cache_key in _YAMNET_EVENT_CACHE:
        return _YAMNET_EVENT_CACHE[cache_key]

    series = _compute_yamnet_engine_series(audio_path)
    if len(series) < 4:
        _cache_set_bounded(
            _YAMNET_EVENT_CACHE,
            cache_key,
            ([], []),
            ANALYSIS_CACHE_MAX_ITEMS,
        )
        return [], []

    times = np.array([ts for ts, _ in series], dtype=np.float64)
    values = np.array([score for _, score in series], dtype=np.float64)
    values = np.clip(values, 0.0, 1.0)

    frame_seconds = max(0.05, YAMNET_PATCH_HOP_SECONDS)
    smooth_frames = max(1, int(round(max(0.1, smooth_seconds) / frame_seconds)))
    cooldown_frames = max(1, int(round(max(0.1, cooldown_seconds) / frame_seconds)))
    lookback_frames = max(2, int(round(2.0 / frame_seconds)))
    safe_delta = max(min_delta, 1e-6)

    smoothed = _moving_average(values, smooth_frames)
    slope = np.diff(smoothed, prepend=smoothed[0])

    start_events: list[tuple[float, float]] = []
    stop_events: list[tuple[float, float]] = []
    last_start_idx = -cooldown_frames
    last_stop_idx = -cooldown_frames

    for idx in range(1, len(smoothed)):
        left = max(0, idx - lookback_frames)
        recent = smoothed[left : idx + 1]
        if recent.size == 0:
            continue

        crossed_start = smoothed[idx - 1] < start_threshold <= smoothed[idx]
        if crossed_start and (idx - last_start_idx) >= cooldown_frames:
            local_low = float(np.min(recent))
            ramp = float(smoothed[idx] - local_low)
            if ramp >= min_delta and slope[idx] > 0.0:
                margin = max(0.0, float(smoothed[idx] - start_threshold))
                conf = (
                    0.45 * min(1.0, margin / max(1e-6, 1.0 - start_threshold))
                    + 0.35 * min(1.0, ramp / safe_delta)
                    + 0.20 * min(1.0, max(0.0, float(slope[idx])) / safe_delta)
                )
                start_events.append((float(times[idx]), float(np.clip(conf, 0.0, 1.0))))
                last_start_idx = idx

        crossed_stop = smoothed[idx - 1] > stop_threshold >= smoothed[idx]
        if crossed_stop and (idx - last_stop_idx) >= cooldown_frames:
            local_high = float(np.max(recent))
            drop = float(local_high - smoothed[idx])
            if local_high >= start_threshold * 0.70 and drop >= min_delta * 0.70 and slope[idx] < 0.0:
                margin = max(0.0, float(stop_threshold - smoothed[idx]))
                conf = (
                    0.45 * min(1.0, margin / max(1e-6, stop_threshold))
                    + 0.35 * min(1.0, drop / safe_delta)
                    + 0.20 * min(1.0, max(0.0, -float(slope[idx])) / safe_delta)
                )
                stop_events.append((float(times[idx]), float(np.clip(conf, 0.0, 1.0))))
                last_stop_idx = idx

    _cache_set_bounded(
        _YAMNET_EVENT_CACHE,
        cache_key,
        (start_events, stop_events),
        ANALYSIS_CACHE_MAX_ITEMS,
    )
    return start_events, stop_events
