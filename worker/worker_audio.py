from __future__ import annotations

from pathlib import Path
import os
import re
import subprocess
import wave
from typing import Any

import numpy as np

from worker.worker_config import ANALYSIS_WINDOW_SECONDS, ANALYSIS_CACHE_MAX_ITEMS
from worker.worker_logging import LOGGER
from worker.worker_utils import _cache_set_bounded, _moving_average

# librosa pour analyse de prosodie (pitch/intonation)
try:
    import librosa
    LIBROSA_AVAILABLE = True
except Exception:
    librosa = None
    LIBROSA_AVAILABLE = False

# silero-vad pour détection de voix (plus précis, nécessite torch)
try:
    import torch
    from silero_vad import load_silero_vad, read_audio, get_speech_timestamps
    SILERO_AVAILABLE = True
except Exception:
    torch = None
    load_silero_vad = None
    read_audio = None
    get_speech_timestamps = None
    SILERO_AVAILABLE = False

# webrtcvad pour détection de voix (fallback léger)
try:
    import webrtcvad
    WEBCVAD_AVAILABLE = True
except Exception:
    webrtcvad = None
    WEBCVAD_AVAILABLE = False

_PITCH_SERIES_CACHE: dict[str, list[tuple[float, float]]] = {}
_ONSET_CACHE: dict[str, list[tuple[float, float]]] = {}
_VAD_CACHE: dict[str, list[tuple[float, float]]] = {}
_CAR_DYNAMICS_CACHE: dict[str, list[tuple[float, float]]] = {}
_CAR_START_STOP_CACHE: dict[str, tuple[list[tuple[float, float]], list[tuple[float, float]]]] = {}
_FFMPEG_SILENCE_CACHE: dict[str, list[tuple[float, float]]] = {}
_SILERO_MODEL = None
_SILENCE_START_RE = re.compile(r"silence_start:\s*([0-9]+(?:\.[0-9]+)?)")
_SILENCE_END_RE = re.compile(r"silence_end:\s*([0-9]+(?:\.[0-9]+)?)")


def _analyze_pitch_contour(audio_path: Path, start: float, end: float) -> dict[str, Any]:
    """
    Analyse la prosodie (intonation) d'un segment audio.
    - Intonation descendante en fin = bonne fin de phrase
    - Intonation montante en fin = question ou phrase incomplète
    
    Retourne:
    - end_pitch_trend: "falling" | "rising" | "flat" | "unknown"
    - is_good_end: bool - True si l'intonation suggère une fin de phrase
    - pitch_score: float - Score de qualité de fin (0-1)
    """
    default = {
        "end_pitch_trend": "unknown",
        "is_good_end": True,  # Permissif par défaut
        "pitch_score": 0.5,
    }
    
    if not LIBROSA_AVAILABLE or librosa is None:
        return default
    
    try:
        # Charge uniquement le segment concerné
        y, sr = librosa.load(str(audio_path), sr=22050, offset=start, duration=end - start)
        
        if len(y) < sr * 0.5:  # Moins de 0.5s = pas assez pour analyser
            return default
        
        # Extraction du pitch (F0) avec piptrack
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr, fmin=75, fmax=400)
        
        # Prend le pitch dominant pour chaque frame
        pitch_values = []
        for t in range(pitches.shape[1]):
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            if pitch > 0:
                pitch_values.append(pitch)
        
        if len(pitch_values) < 10:
            return default
        
        # Analyse les dernières 0.5 secondes pour la tendance finale
        frames_per_sec = len(pitch_values) / (end - start)
        last_frames = int(0.5 * frames_per_sec)
        if last_frames < 5:
            last_frames = min(5, len(pitch_values))
        
        end_pitches = pitch_values[-last_frames:]
        
        # Calcule la tendance (régression linéaire simplifiée)
        if len(end_pitches) >= 3:
            first_half = np.mean(end_pitches[:len(end_pitches)//2])
            second_half = np.mean(end_pitches[len(end_pitches)//2:])
            
            diff = second_half - first_half
            threshold = 15  # Hz - seuil pour considérer une variation significative
            
            if diff < -threshold:
                trend = "falling"
                is_good = True
                score = 0.9
            elif diff > threshold:
                trend = "rising"
                is_good = False  # Intonation montante = probablement pas fini
                score = 0.3
            else:
                trend = "flat"
                is_good = True
                score = 0.6
        else:
            trend = "unknown"
            is_good = True
            score = 0.5
        
        return {
            "end_pitch_trend": trend,
            "is_good_end": is_good,
            "pitch_score": score,
        }
        
    except Exception as e:
        LOGGER.debug("Pitch analysis failed: %s", e)
        return default

def _compute_pitch_series(
    audio_path: Path, window_seconds: float = ANALYSIS_WINDOW_SECONDS
) -> list[tuple[float, float]]:
    """
    Calcule une série de pitch (fréquence fondamentale) sur toute la vidéo.
    Retourne une liste de (timestamp, pitch).
    """
    if not LIBROSA_AVAILABLE or librosa is None:
        return []

    cache_key = f"{audio_path}|pitch|{window_seconds:.3f}"
    if cache_key in _PITCH_SERIES_CACHE:
        return _PITCH_SERIES_CACHE[cache_key]

    try:
        y, sr = librosa.load(str(audio_path), sr=22050)
        if len(y) < sr * 0.5:
            return []

        hop_length = max(1, int(sr * window_seconds))
        pitches, magnitudes = librosa.piptrack(
            y=y, sr=sr, fmin=75, fmax=400, hop_length=hop_length
        )

        pitch_values = []
        for t in range(pitches.shape[1]):
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            pitch_values.append(float(pitch) if pitch > 0 else 0.0)

        times = librosa.frames_to_time(
            np.arange(len(pitch_values)), sr=sr, hop_length=hop_length
        )
        series = list(zip(times.tolist(), pitch_values))
        _cache_set_bounded(_PITCH_SERIES_CACHE, cache_key, series, ANALYSIS_CACHE_MAX_ITEMS)
        return series
    except Exception as e:
        LOGGER.debug("Pitch series failed: %s", e)
        return []


def _analyze_pitch_trend_from_series(
    pitch_series: list[tuple[float, float]], start: float, end: float
) -> dict[str, Any]:
    """
    Analyse la tendance du pitch depuis une série pré-calculée.
    """
    default = {
        "end_pitch_trend": "unknown",
        "is_good_end": True,
        "pitch_score": 0.5,
    }
    if not pitch_series:
        return default

    # Récupère les valeurs de pitch dans la fenêtre
    pitch_values = [
        pitch for ts, pitch in pitch_series if start <= ts <= end and pitch > 0
    ]
    if len(pitch_values) < 5:
        return default

    # Analyse la tendance sur la dernière moitié
    mid = len(pitch_values) // 2
    first_half = np.mean(pitch_values[:mid]) if mid > 0 else np.mean(pitch_values)
    second_half = np.mean(pitch_values[mid:]) if mid > 0 else np.mean(pitch_values)

    diff = second_half - first_half
    threshold = 15  # Hz

    if diff < -threshold:
        return {"end_pitch_trend": "falling", "is_good_end": True, "pitch_score": 0.9}
    if diff > threshold:
        return {"end_pitch_trend": "rising", "is_good_end": False, "pitch_score": 0.3}
    return {"end_pitch_trend": "flat", "is_good_end": True, "pitch_score": 0.6}


def _compute_onset_series(
    audio_path: Path, window_seconds: float = ANALYSIS_WINDOW_SECONDS
) -> list[tuple[float, float]]:
    """
    Calcule une série d'onset (changements rapides d'énergie spectrale).
    Retourne une liste (timestamp, onset_strength).
    """
    if not LIBROSA_AVAILABLE or librosa is None:
        return []

    cache_key = f"{audio_path}|onset|{window_seconds:.3f}"
    if cache_key in _ONSET_CACHE:
        return _ONSET_CACHE[cache_key]

    try:
        y, sr = librosa.load(str(audio_path), sr=22050)
        hop_length = max(1, int(sr * window_seconds))
        onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
        times = librosa.frames_to_time(
            np.arange(len(onset_env)), sr=sr, hop_length=hop_length
        )
        series = list(zip(times.tolist(), onset_env.tolist()))
        _cache_set_bounded(_ONSET_CACHE, cache_key, series, ANALYSIS_CACHE_MAX_ITEMS)
        return series
    except Exception as e:
        LOGGER.debug("Onset series failed: %s", e)
        return []


def _minmax_normalize(values: np.ndarray) -> np.ndarray:
    """Min-max normalization with stable fallback for near-constant arrays."""
    if values.size == 0:
        return values
    v_min = float(np.min(values))
    v_max = float(np.max(values))
    if v_max - v_min < 1e-9:
        return np.zeros_like(values, dtype=np.float64)
    return (values - v_min) / (v_max - v_min)


def _compute_car_dynamics_series(
    audio_path: Path, window_seconds: float = ANALYSIS_WINDOW_SECONDS
) -> list[tuple[float, float]]:
    """
    Detects "car dynamics" events (revving/acceleration moments) from audio only.

    Returns a time series (timestamp, score_0_to_1) where high values represent
    likely acceleration/revving moments in automotive videos.
    """
    if not LIBROSA_AVAILABLE or librosa is None:
        return []

    cache_key = f"{audio_path}|car_dynamics|{window_seconds:.3f}"
    if cache_key in _CAR_DYNAMICS_CACHE:
        return _CAR_DYNAMICS_CACHE[cache_key]

    try:
        y, sr = librosa.load(str(audio_path), sr=22050)
        if len(y) < sr:
            return []

        hop_length = max(1, int(sr * window_seconds))
        frame_length = max(2048, hop_length)

        rms = librosa.feature.rms(
            y=y, frame_length=frame_length, hop_length=hop_length
        )[0]
        onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
        centroid = librosa.feature.spectral_centroid(
            y=y, sr=sr, hop_length=hop_length
        )[0]
        rolloff = librosa.feature.spectral_rolloff(
            y=y, sr=sr, hop_length=hop_length, roll_percent=0.85
        )[0]

        n = min(len(rms), len(onset), len(centroid), len(rolloff))
        if n <= 1:
            return []

        rms = rms[:n].astype(np.float64)
        onset = onset[:n].astype(np.float64)
        centroid = centroid[:n].astype(np.float64)
        rolloff = rolloff[:n].astype(np.float64)

        rms_n = _minmax_normalize(rms)
        onset_n = _minmax_normalize(onset)
        centroid_n = _minmax_normalize(centroid)
        rolloff_n = _minmax_normalize(rolloff)

        # Positive deltas capture rising engine load/acceleration phases.
        rms_delta = np.maximum(0.0, np.diff(rms_n, prepend=rms_n[0]))
        centroid_delta = np.maximum(0.0, np.diff(centroid_n, prepend=centroid_n[0]))

        score = (
            rms_n * 0.20
            + onset_n * 0.30
            + rms_delta * 0.25
            + centroid_delta * 0.15
            + rolloff_n * 0.10
        )
        score = np.clip(score, 0.0, 1.0)

        times = librosa.frames_to_time(np.arange(n), sr=sr, hop_length=hop_length)
        series = list(zip(times.tolist(), score.astype(float).tolist()))
        _cache_set_bounded(_CAR_DYNAMICS_CACHE, cache_key, series, ANALYSIS_CACHE_MAX_ITEMS)
        return series
    except Exception as e:
        LOGGER.debug("Car dynamics series failed: %s", e)
        return []


def _compute_car_start_stop_events(
    audio_path: Path,
    *,
    window_seconds: float = ANALYSIS_WINDOW_SECONDS,
    start_threshold: float = 0.58,
    stop_threshold: float = 0.46,
    min_delta: float = 0.12,
    smooth_seconds: float = 1.5,
    cooldown_seconds: float = 2.5,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """
    Detects likely car start/stop events from the car dynamics time-series.

    Returns:
    - start_events: [(timestamp, confidence_0_to_1)]
    - stop_events: [(timestamp, confidence_0_to_1)]
    """
    if not LIBROSA_AVAILABLE or librosa is None:
        return [], []

    cache_key = (
        f"{audio_path}|car_start_stop|{window_seconds:.3f}|{start_threshold:.3f}|"
        f"{stop_threshold:.3f}|{min_delta:.3f}|{smooth_seconds:.3f}|{cooldown_seconds:.3f}"
    )
    if cache_key in _CAR_START_STOP_CACHE:
        return _CAR_START_STOP_CACHE[cache_key]

    car_series = _compute_car_dynamics_series(audio_path, window_seconds=window_seconds)
    if len(car_series) < 4:
        _cache_set_bounded(
            _CAR_START_STOP_CACHE,
            cache_key,
            ([], []),
            ANALYSIS_CACHE_MAX_ITEMS,
        )
        return [], []

    times = np.array([ts for ts, _ in car_series], dtype=np.float64)
    values = np.array([score for _, score in car_series], dtype=np.float64)
    values = np.clip(values, 0.0, 1.0)

    frame_seconds = max(window_seconds, 0.05)
    smooth_frames = max(1, int(round(smooth_seconds / frame_seconds)))
    cooldown_frames = max(1, int(round(cooldown_seconds / frame_seconds)))
    lookback_frames = max(2, int(round(2.0 / frame_seconds)))

    smoothed = _moving_average(values, smooth_frames)
    slope = np.diff(smoothed, prepend=smoothed[0])

    start_events: list[tuple[float, float]] = []
    stop_events: list[tuple[float, float]] = []

    last_start_idx = -cooldown_frames
    last_stop_idx = -cooldown_frames
    safe_delta = max(min_delta, 1e-6)

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
            if local_high >= start_threshold * 0.80 and drop >= min_delta * 0.80 and slope[idx] < 0.0:
                margin = max(0.0, float(stop_threshold - smoothed[idx]))
                conf = (
                    0.45 * min(1.0, margin / max(1e-6, stop_threshold))
                    + 0.35 * min(1.0, drop / safe_delta)
                    + 0.20 * min(1.0, max(0.0, -float(slope[idx])) / safe_delta)
                )
                stop_events.append((float(times[idx]), float(np.clip(conf, 0.0, 1.0))))
                last_stop_idx = idx

    _cache_set_bounded(
        _CAR_START_STOP_CACHE,
        cache_key,
        (start_events, stop_events),
        ANALYSIS_CACHE_MAX_ITEMS,
    )
    return start_events, stop_events


def _compute_ffmpeg_silence_segments(
    audio_path: Path,
    *,
    noise_db: float = -35.0,
    min_silence_seconds: float = 0.25,
) -> list[tuple[float, float]]:
    """
    Detect silence ranges using ffmpeg silencedetect.

    Returns a list of (silence_start, silence_end) in seconds.
    """
    cache_key = f"{audio_path}|silencedetect|{noise_db:.2f}|{min_silence_seconds:.3f}"
    if cache_key in _FFMPEG_SILENCE_CACHE:
        return _FFMPEG_SILENCE_CACHE[cache_key]

    safe_duration = max(0.05, float(min_silence_seconds))
    null_sink = "NUL" if os.name == "nt" else "/dev/null"
    filter_value = f"silencedetect=noise={noise_db:.2f}dB:d={safe_duration:.3f}"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        str(audio_path),
        "-af",
        filter_value,
        "-f",
        "null",
        null_sink,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as e:
        LOGGER.debug("ffmpeg silencedetect failed to start: %s", e)
        return []

    if result.returncode != 0 and "silence_start" not in result.stderr:
        LOGGER.debug("ffmpeg silencedetect failed: %s", result.stderr.strip())
        return []

    segments: list[tuple[float, float]] = []
    current_start: float | None = None

    for line in result.stderr.splitlines():
        start_match = _SILENCE_START_RE.search(line)
        if start_match:
            current_start = max(0.0, float(start_match.group(1)))
            continue

        end_match = _SILENCE_END_RE.search(line)
        if end_match:
            end_value = max(0.0, float(end_match.group(1)))
            if current_start is not None and end_value > current_start:
                segments.append((current_start, end_value))
            current_start = None

    _cache_set_bounded(
        _FFMPEG_SILENCE_CACHE,
        cache_key,
        segments,
        ANALYSIS_CACHE_MAX_ITEMS,
    )
    return segments


def _compute_vad_series(
    wav_path: Path,
    window_seconds: float = ANALYSIS_WINDOW_SECONDS,
    vad_mode: int = 2,
) -> list[tuple[float, float]]:
    """
    Calcule une série VAD (ratio de voix par fenêtre).
    Retourne une liste (timestamp, speech_ratio).
    """
    cache_key = f"{wav_path}|vad|{window_seconds:.3f}|{vad_mode}"
    if cache_key in _VAD_CACHE:
        return _VAD_CACHE[cache_key]

    # 1) Silero VAD (plus précis)
    if SILERO_AVAILABLE and load_silero_vad and read_audio and get_speech_timestamps:
        try:
            global _SILERO_MODEL
            if _SILERO_MODEL is None:
                _SILERO_MODEL = load_silero_vad()

            sampling_rate = 16000
            audio = read_audio(str(wav_path), sampling_rate=sampling_rate)
            speech_segments = get_speech_timestamps(
                audio, _SILERO_MODEL, sampling_rate=sampling_rate
            )

            window_samples = max(1, int(window_seconds * sampling_rate))
            total_samples = len(audio)
            series: list[tuple[float, float]] = []

            seg_idx = 0
            for window_start in range(0, total_samples, window_samples):
                window_end = min(total_samples, window_start + window_samples)
                speech_in_window = 0

                while seg_idx < len(speech_segments) and speech_segments[seg_idx]["end"] <= window_start:
                    seg_idx += 1

                j = seg_idx
                while j < len(speech_segments) and speech_segments[j]["start"] < window_end:
                    seg_start = max(window_start, speech_segments[j]["start"])
                    seg_end = min(window_end, speech_segments[j]["end"])
                    if seg_end > seg_start:
                        speech_in_window += seg_end - seg_start
                    j += 1

                ratio = speech_in_window / (window_end - window_start) if window_end > window_start else 0.0
                timestamp = window_start / sampling_rate
                series.append((timestamp, float(ratio)))

            _cache_set_bounded(_VAD_CACHE, cache_key, series, ANALYSIS_CACHE_MAX_ITEMS)
            return series
        except Exception as e:
            LOGGER.debug("Silero VAD failed: %s", e)

    # 2) Fallback WebRTC VAD (léger)
    if not WEBCVAD_AVAILABLE or webrtcvad is None:
        return []

    try:
        with wave.open(str(wav_path), "rb") as wf:
            sample_rate = wf.getframerate()
            sample_width = wf.getsampwidth()
            channels = wf.getnchannels()
            if channels != 1 or sample_width != 2:
                return []
            if sample_rate not in (8000, 16000, 32000, 48000):
                return []

            vad = webrtcvad.Vad(vad_mode)
            raw_data = wf.readframes(wf.getnframes())

        frame_ms = 20
        bytes_per_frame = int(sample_rate * frame_ms / 1000) * sample_width
        if bytes_per_frame <= 0:
            return []

        frames_per_window = max(1, int((window_seconds * 1000) / frame_ms))
        total_frames = len(raw_data) // bytes_per_frame

        series: list[tuple[float, float]] = []
        speech_count = 0
        frame_count = 0
        window_index = 0

        for i in range(total_frames):
            offset = i * bytes_per_frame
            frame = raw_data[offset : offset + bytes_per_frame]
            if len(frame) < bytes_per_frame:
                break
            if vad.is_speech(frame, sample_rate):
                speech_count += 1
            frame_count += 1

            if frame_count >= frames_per_window:
                ratio = speech_count / frame_count if frame_count > 0 else 0.0
                timestamp = window_index * window_seconds
                series.append((timestamp, ratio))
                window_index += 1
                speech_count = 0
                frame_count = 0

        if frame_count > 0:
            ratio = speech_count / frame_count
            timestamp = window_index * window_seconds
            series.append((timestamp, ratio))

        _cache_set_bounded(_VAD_CACHE, cache_key, series, ANALYSIS_CACHE_MAX_ITEMS)
        return series
    except Exception as e:
        LOGGER.debug("VAD series failed: %s", e)
        return []
def _compute_rms_series(
    wav_path: Path, window_seconds: float = ANALYSIS_WINDOW_SECONDS
) -> list[tuple[float, float]]:
    """Compute RMS energy series using numpy for 3-5x speedup."""
    with wave.open(str(wav_path), "rb") as wf:
        sample_rate = wf.getframerate()
        sample_width = wf.getsampwidth()
        channels = wf.getnchannels()
        if channels != 1:
            raise RuntimeError("Expected mono audio for analysis")
        
        # Read all frames at once (much faster than chunked reads)
        n_frames = wf.getnframes()
        raw_data = wf.readframes(n_frames)
        
        # Convert to numpy array based on sample width
        if sample_width == 2:
            dtype = np.int16
        elif sample_width == 4:
            dtype = np.int32
        else:
            raise RuntimeError("Unsupported sample width")
        
        audio = np.frombuffer(raw_data, dtype=dtype).astype(np.float64)
        
        # Calculate RMS per window using numpy (vectorized)
        frames_per_window = max(1, int(sample_rate * window_seconds))
        n_windows = len(audio) // frames_per_window
        
        # Trim audio to fit exact windows
        audio_trimmed = audio[:n_windows * frames_per_window]
        # Reshape into windows
        windows = audio_trimmed.reshape(n_windows, frames_per_window)
        # Calculate RMS for each window (vectorized)
        rms_values = np.sqrt(np.mean(windows ** 2, axis=1))
        
        # Build series with timestamps
        timestamps = np.arange(n_windows) * window_seconds
        series = list(zip(timestamps.tolist(), rms_values.tolist()))
        
        return series


