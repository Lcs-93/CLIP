from __future__ import annotations

from pathlib import Path

import numpy as np

from worker.worker_config import ANALYSIS_CACHE_MAX_ITEMS
from worker.worker_logging import LOGGER
from worker.worker_utils import _cache_set_bounded, _moving_average

try:
    import cv2

    OPENCV_AVAILABLE = True
except Exception:
    cv2 = None
    OPENCV_AVAILABLE = False

_VISUAL_MOTION_CACHE: dict[str, list[tuple[float, float]]] = {}
_VISUAL_EVENT_CACHE: dict[str, tuple[list[tuple[float, float]], list[tuple[float, float]]]] = {}

def _compute_visual_motion_series(
    video_path: Path,
    *,
    sample_fps: float = 6.0,
    resize_width: int = 320,
    roi_bottom_ratio: float = 0.60,
) -> list[tuple[float, float]]:
    """
    Computes a normalized visual motion score (0..1) per sampled frame.
    Uses optical flow and focuses on the lower part of the frame (road area).
    """
    if not OPENCV_AVAILABLE or cv2 is None:
        return []

    safe_fps = max(1.0, float(sample_fps))
    safe_resize = max(96, int(resize_width))
    safe_roi = min(0.95, max(0.0, float(roi_bottom_ratio)))
    cache_key = f"{video_path}|motion|{safe_fps:.3f}|{safe_resize}|{safe_roi:.3f}"
    if cache_key in _VISUAL_MOTION_CACHE:
        return _VISUAL_MOTION_CACHE[cache_key]

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return []

    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        if fps <= 1.0:
            fps = 30.0
        frame_step = max(1, int(round(fps / safe_fps)))

        prev_gray = None
        frame_index = 0
        times: list[float] = []
        raw_scores: list[float] = []

        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                break

            if frame_index % frame_step != 0:
                frame_index += 1
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if gray.shape[1] > safe_resize:
                scale = safe_resize / float(gray.shape[1])
                new_h = max(72, int(gray.shape[0] * scale))
                gray = cv2.resize(gray, (safe_resize, new_h), interpolation=cv2.INTER_AREA)
            gray = cv2.GaussianBlur(gray, (5, 5), 0)

            if prev_gray is not None and gray.shape == prev_gray.shape:
                flow = cv2.calcOpticalFlowFarneback(
                    prev_gray,
                    gray,
                    None,
                    0.5,
                    3,
                    15,
                    3,
                    5,
                    1.2,
                    0,
                )
                mag = cv2.magnitude(flow[..., 0], flow[..., 1])
                if 0.0 < safe_roi < 1.0:
                    y0 = int(mag.shape[0] * safe_roi)
                    if 0 <= y0 < mag.shape[0] - 2:
                        mag = mag[y0:, :]
                raw = float(np.percentile(mag, 75))
                raw_scores.append(raw)
                times.append(frame_index / fps)

            prev_gray = gray
            frame_index += 1

        if not raw_scores:
            _cache_set_bounded(
                _VISUAL_MOTION_CACHE,
                cache_key,
                [],
                ANALYSIS_CACHE_MAX_ITEMS,
            )
            return []

        values = np.array(raw_scores, dtype=np.float64)
        p10, p95 = np.percentile(values, [10, 95])
        denom = max(1e-6, float(p95 - p10))
        normalized = np.clip((values - p10) / denom, 0.0, 1.0)
        series = list(zip(times, normalized.astype(float).tolist()))
        _cache_set_bounded(
            _VISUAL_MOTION_CACHE,
            cache_key,
            series,
            ANALYSIS_CACHE_MAX_ITEMS,
        )
        return series
    except Exception as exc:
        LOGGER.debug("Visual motion series failed: %s", exc)
        return []
    finally:
        cap.release()


def _compute_visual_car_start_stop_events(
    video_path: Path,
    *,
    sample_fps: float = 6.0,
    resize_width: int = 320,
    roi_bottom_ratio: float = 0.60,
    start_threshold: float = 0.52,
    stop_threshold: float = 0.42,
    min_delta: float = 0.08,
    smooth_seconds: float = 1.2,
    cooldown_seconds: float = 2.0,
    motion_series: list[tuple[float, float]] | None = None,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """
    Detects visual start/stop events from the visual motion series.
    Returns (start_events, stop_events) where each event is (timestamp, confidence_0_to_1).
    """
    if not OPENCV_AVAILABLE:
        return [], []

    safe_fps = max(1.0, float(sample_fps))
    safe_resize = max(96, int(resize_width))
    safe_roi = min(0.95, max(0.0, float(roi_bottom_ratio)))
    cache_key = (
        f"{video_path}|events|{safe_fps:.3f}|{safe_resize}|{safe_roi:.3f}|"
        f"{start_threshold:.3f}|{stop_threshold:.3f}|{min_delta:.3f}|"
        f"{smooth_seconds:.3f}|{cooldown_seconds:.3f}"
    )
    if cache_key in _VISUAL_EVENT_CACHE:
        return _VISUAL_EVENT_CACHE[cache_key]

    series = motion_series or _compute_visual_motion_series(
        video_path,
        sample_fps=safe_fps,
        resize_width=safe_resize,
        roi_bottom_ratio=safe_roi,
    )
    if len(series) < 4:
        _cache_set_bounded(
            _VISUAL_EVENT_CACHE,
            cache_key,
            ([], []),
            ANALYSIS_CACHE_MAX_ITEMS,
        )
        return [], []

    times = np.array([ts for ts, _ in series], dtype=np.float64)
    values = np.array([score for _, score in series], dtype=np.float64)
    values = np.clip(values, 0.0, 1.0)

    frame_seconds = max(1.0 / safe_fps, 0.05)
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
            if local_high >= start_threshold * 0.75 and drop >= min_delta * 0.70 and slope[idx] < 0.0:
                margin = max(0.0, float(stop_threshold - smoothed[idx]))
                conf = (
                    0.45 * min(1.0, margin / max(1e-6, stop_threshold))
                    + 0.35 * min(1.0, drop / safe_delta)
                    + 0.20 * min(1.0, max(0.0, -float(slope[idx])) / safe_delta)
                )
                stop_events.append((float(times[idx]), float(np.clip(conf, 0.0, 1.0))))
                last_stop_idx = idx

    _cache_set_bounded(
        _VISUAL_EVENT_CACHE,
        cache_key,
        (start_events, stop_events),
        ANALYSIS_CACHE_MAX_ITEMS,
    )
    return start_events, stop_events
