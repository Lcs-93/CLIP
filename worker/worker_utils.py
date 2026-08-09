from __future__ import annotations

from pathlib import Path
from statistics import mean, pstdev
from math import floor, ceil
from typing import Any

import numpy as np

from worker.worker_config import ANALYSIS_WINDOW_SECONDS


def _safe_unlink(path_value: str | Path | None) -> None:
    if not path_value:
        return
    try:
        Path(path_value).unlink(missing_ok=True)
    except Exception:
        return


def _cache_set_bounded(cache: dict[str, Any], key: str, value: Any, max_items: int) -> None:
    """
    Insert into a dict-like cache and evict oldest entries when over capacity.
    Python dict preserves insertion order, so next(iter(cache)) is oldest.
    """
    if key in cache:
        cache.pop(key, None)
    cache[key] = value
    if max_items <= 0:
        cache.clear()
        return
    while len(cache) > max_items:
        oldest = next(iter(cache), None)
        if oldest is None:
            break
        cache.pop(oldest, None)


def _moving_average(values: np.ndarray, window_size: int) -> np.ndarray:
    if values.size == 0 or window_size <= 1:
        return values
    kernel = np.ones(window_size, dtype=np.float64) / float(window_size)
    return np.convolve(values, kernel, mode="same")


def _percentile(sorted_values: list[float], percentile: float) -> float:
    if not sorted_values:
        return 0.0
    if percentile <= 0:
        return sorted_values[0]
    if percentile >= 1:
        return sorted_values[-1]
    k = (len(sorted_values) - 1) * percentile
    f = floor(k)
    c = ceil(k)
    if f == c:
        return sorted_values[int(k)]
    d0 = sorted_values[f] * (c - k)
    d1 = sorted_values[c] * (k - f)
    return d0 + d1


def _normalize_series(series: list[tuple[float, float]]) -> tuple[list[float], float, float]:
    values = [value for _, value in series]
    if not values:
        return [], 0.0, 0.0

    sorted_values = sorted(values)
    p10 = _percentile(sorted_values, 0.10)
    p90 = _percentile(sorted_values, 0.90)

    # Fallback min/max si la distribution est trop plate
    if p90 <= p10:
        p10 = sorted_values[0]
        p90 = sorted_values[-1]

    if p90 == p10:
        normalized = [0.0 for _ in values]
    else:
        denom = p90 - p10
        normalized = [
            max(0.0, min(1.0, (value - p10) / denom)) for value in values
        ]

    avg = mean(normalized)
    deviation = pstdev(normalized) if len(normalized) > 1 else 0.0
    return normalized, avg, deviation


def _find_peak_indices(values: list[float], threshold: float) -> list[int]:
    indices: list[int] = []
    for idx in range(1, len(values) - 1):
        current = values[idx]
        if current >= threshold and current >= values[idx - 1] and current >= values[idx + 1]:
            indices.append(idx)
    return indices


def _find_peak_indices_local(
    values: list[float],
    window_seconds: float,
    sample_window: float,
    base_offset: float = 0.12,
    deviation_scale: float = 0.25,
) -> list[int]:
    """
    Détecte des pics locaux avec un seuil calculé dans une fenêtre glissante.
    """
    if not values:
        return []

    window_size = max(3, int(window_seconds / sample_window))
    half = max(1, window_size // 2)
    indices: list[int] = []

    for idx in range(1, len(values) - 1):
        start = max(0, idx - half)
        end = min(len(values), idx + half + 1)
        local = values[start:end]
        if not local:
            continue
        local_avg = mean(local)
        local_dev = pstdev(local) if len(local) > 1 else 0.0
        threshold = max(base_offset, local_avg + local_dev * deviation_scale)
        current = values[idx]
        if current >= threshold and current >= values[idx - 1] and current >= values[idx + 1]:
            indices.append(idx)

    return indices


def _window_slice(
    values: list[float], center: int, window_seconds: float, sample_window: float
) -> tuple[int, int]:
    half = int(window_seconds / sample_window)
    start = max(0, center - half)
    end = min(len(values) - 1, center + half)
    return start, end


def _snap_to_silence(values: list[float], index: int, direction: int, avg: float) -> int:
    silence_threshold = max(0.06, avg * 0.6)
    steps = int(3.0 / ANALYSIS_WINDOW_SECONDS)
    for offset in range(steps + 1):
        idx = index + direction * offset
        if 0 <= idx < len(values) and values[idx] <= silence_threshold:
            return idx
    return index


def _expand_arc(
    series: list[tuple[float, float]],
    values: list[float],
    index: int,
    avg: float,
    duration: float,
) -> tuple[float, float]:
    low_threshold = max(0.06, avg * 0.6)
    max_steps = int(60.0 / ANALYSIS_WINDOW_SECONDS)
    left = index
    right = index
    for _ in range(max_steps):
        if left > 0 and values[left - 1] >= low_threshold:
            left -= 1
        else:
            break
    for _ in range(max_steps):
        if right < len(values) - 1 and values[right + 1] >= low_threshold:
            right += 1
        else:
            break
    left = _snap_to_silence(values, left, -1, avg)
    right = _snap_to_silence(values, right, 1, avg)
    start = series[left][0]
    end = series[right][0] + ANALYSIS_WINDOW_SECONDS
    start = max(0.0, min(start, duration))
    end = max(start, min(end, duration))
    return start, end
