from __future__ import annotations

from pathlib import Path

import numpy as np

from worker.worker_config import (
    ANALYSIS_CACHE_MAX_ITEMS,
    FACIAL_EMOTION_EVENT_MIN_SCORE,
    FACIAL_EMOTION_MIN_ACTIVE_RATIO,
)
from worker.worker_logging import LOGGER
from worker.worker_utils import _cache_set_bounded, _moving_average

try:
    import cv2

    OPENCV_AVAILABLE = True
except Exception:
    cv2 = None
    OPENCV_AVAILABLE = False

try:
    from fer import FER
    FER_AVAILABLE = True
except Exception:
    try:
        # Newer package builds may not re-export FER at top level.
        from fer.fer import FER  # type: ignore
        FER_AVAILABLE = True
    except Exception:
        FER = None
        FER_AVAILABLE = False


FACIAL_EMOTION_AVAILABLE = OPENCV_AVAILABLE

_FACIAL_EMOTION_CACHE: dict[str, list[tuple[float, float]]] = {}
_FER_DETECTOR = None
_FER_DISABLED = False
_FACE_CASCADE = None
_SMILE_CASCADE = None
_FACIAL_EMOTION_CACHE_VERSION = "v2"


def _load_cascade(filename: str):
    if not OPENCV_AVAILABLE or cv2 is None:
        return None
    try:
        base = Path(getattr(cv2.data, "haarcascades", ""))
        if not base:
            return None
        path = base / filename
        if not path.exists():
            return None
        detector = cv2.CascadeClassifier(str(path))
        if detector is None or detector.empty():
            return None
        return detector
    except Exception:
        return None


def _get_face_cascade():
    global _FACE_CASCADE
    if _FACE_CASCADE is None:
        _FACE_CASCADE = _load_cascade("haarcascade_frontalface_default.xml")
    return _FACE_CASCADE


def _get_smile_cascade():
    global _SMILE_CASCADE
    if _SMILE_CASCADE is None:
        _SMILE_CASCADE = _load_cascade("haarcascade_smile.xml")
    return _SMILE_CASCADE


def _get_fer_detector():
    global _FER_DETECTOR, _FER_DISABLED
    if not FER_AVAILABLE or FER is None or _FER_DISABLED:
        return None
    if _FER_DETECTOR is None:
        try:
            _FER_DETECTOR = FER(mtcnn=False)
        except Exception as exc:
            LOGGER.warning("FER init failed, fallback to OpenCV mode: %s", exc)
            _FER_DISABLED = True
            return None
    return _FER_DETECTOR


def _emotion_score_from_fer(
    frame_rgb: np.ndarray,
    min_face_area_ratio: float,
) -> float:
    detector = _get_fer_detector()
    if detector is None:
        return 0.0

    try:
        results = detector.detect_emotions(frame_rgb)
    except Exception as exc:
        LOGGER.debug("FER detect_emotions failed: %s", exc)
        return 0.0

    if not results:
        return 0.0

    frame_area = float(frame_rgb.shape[0] * frame_rgb.shape[1]) if frame_rgb.size else 0.0
    if frame_area <= 0:
        return 0.0

    expressive_keys = ("angry", "disgust", "fear", "happy", "sad", "surprise")
    best = 0.0
    for item in results:
        emotions = item.get("emotions", {}) if isinstance(item, dict) else {}
        box = item.get("box", [0, 0, 0, 0]) if isinstance(item, dict) else [0, 0, 0, 0]
        if not emotions or len(box) < 4:
            continue

        face_w = max(0.0, float(box[2]))
        face_h = max(0.0, float(box[3]))
        area_ratio = (face_w * face_h) / frame_area
        if area_ratio < min_face_area_ratio:
            continue

        expressive = max(float(emotions.get(key, 0.0)) for key in expressive_keys)
        neutral = float(emotions.get("neutral", 0.0))
        score = max(0.0, expressive - neutral * 0.20)
        score += min(0.20, area_ratio * 1.6)
        best = max(best, min(1.0, score))

    return best


def _emotion_score_from_smile(
    gray: np.ndarray,
    min_face_area_ratio: float,
) -> float:
    face_detector = _get_face_cascade()
    smile_detector = _get_smile_cascade()
    if face_detector is None:
        return 0.0

    frame_area = float(gray.shape[0] * gray.shape[1]) if gray.size else 0.0
    if frame_area <= 0:
        return 0.0

    try:
        faces = face_detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(36, 36),
        )
    except Exception:
        return 0.0

    if len(faces) == 0:
        return 0.0

    best = 0.0
    for x, y, w, h in faces:
        area_ratio = (float(w) * float(h)) / frame_area
        if area_ratio < min_face_area_ratio:
            continue

        local_score = 0.0
        if smile_detector is not None:
            roi = gray[y : y + h, x : x + w]
            if roi.size > 0:
                try:
                    smiles = smile_detector.detectMultiScale(
                        roi,
                        scaleFactor=1.7,
                        minNeighbors=22,
                        minSize=(16, 16),
                    )
                except Exception:
                    smiles = ()
                for _, _, sw, sh in smiles:
                    smile_ratio = (float(sw) * float(sh)) / max(1.0, float(w * h))
                    local_score = max(local_score, min(1.0, smile_ratio * 4.0))

        # If smile cascade is unavailable, no reliable fallback score.
        if local_score <= 0.0:
            continue

        local_score = 0.18 + local_score * 0.82
        local_score += min(0.10, area_ratio * 0.8)
        best = max(best, min(1.0, local_score))

    return best


def _facial_emotion_backend_name(use_fer: bool = True) -> str:
    if use_fer and _get_fer_detector() is not None:
        return "fer"
    return "opencv_smile"


def _compute_facial_emotion_series(
    video_path: Path,
    *,
    sample_fps: float = 3.0,
    resize_width: int = 480,
    use_fer: bool = True,
    min_face_area_ratio: float = 0.012,
) -> list[tuple[float, float]]:
    """
    Computes a normalized facial emotion score (0..1) per sampled frame.
    - Preferred backend: FER (multi-emotion classifier)
    - Fallback backend: OpenCV face+smile proxy
    """
    if not OPENCV_AVAILABLE or cv2 is None:
        return []

    safe_fps = max(1.0, float(sample_fps))
    safe_resize = max(160, int(resize_width))
    safe_face_ratio = min(0.35, max(0.001, float(min_face_area_ratio)))
    backend = _facial_emotion_backend_name(use_fer=use_fer)
    cache_key = (
        f"{video_path}|face_emotion|{_FACIAL_EMOTION_CACHE_VERSION}|{backend}|"
        f"{safe_fps:.3f}|{safe_resize}|{safe_face_ratio:.4f}|"
        f"min_active={FACIAL_EMOTION_MIN_ACTIVE_RATIO:.3f}"
    )
    if cache_key in _FACIAL_EMOTION_CACHE:
        return _FACIAL_EMOTION_CACHE[cache_key]

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return []

    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        if fps <= 1.0:
            fps = 30.0
        frame_step = max(1, int(round(fps / safe_fps)))

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

            if frame.shape[1] > safe_resize:
                scale = safe_resize / float(frame.shape[1])
                new_h = max(96, int(frame.shape[0] * scale))
                frame = cv2.resize(frame, (safe_resize, new_h), interpolation=cv2.INTER_AREA)

            score = 0.0
            if backend == "fer":
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                score = _emotion_score_from_fer(frame_rgb, safe_face_ratio)
            else:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.equalizeHist(gray)
                score = _emotion_score_from_smile(gray, safe_face_ratio)

            raw_scores.append(float(np.clip(score, 0.0, 1.0)))
            times.append(frame_index / fps)
            frame_index += 1

        if not raw_scores:
            _cache_set_bounded(
                _FACIAL_EMOTION_CACHE,
                cache_key,
                [],
                ANALYSIS_CACHE_MAX_ITEMS,
            )
            return []

        values = np.array(raw_scores, dtype=np.float64)
        values = _moving_average(values, window_size=3)

        # Avoid inflating sparse/weak detections into strong peaks.
        # When spread is too small, keep original bounded values instead
        # of percentile normalization.
        positive_count = int(np.count_nonzero(values > 0.0))
        p10, p95 = np.percentile(values, [10, 95])
        spread = float(p95 - p10)
        if positive_count < 4 or spread < 0.10:
            normalized = np.clip(values, 0.0, 1.0)
        else:
            denom = max(1e-6, spread)
            normalized = np.clip((values - p10) / denom, 0.0, 1.0)

        # Guardrail: if "emotion-active" frames are too sparse on the full video,
        # treat the signal as unreliable (typical false positives on no-face videos).
        active_threshold = max(0.25, FACIAL_EMOTION_EVENT_MIN_SCORE * 0.70)
        active_ratio = float(np.count_nonzero(normalized >= active_threshold)) / float(len(normalized))
        if active_ratio < FACIAL_EMOTION_MIN_ACTIVE_RATIO:
            LOGGER.info(
                "Facial emotion ignored: active_ratio=%.3f < min_active_ratio=%.3f",
                active_ratio,
                FACIAL_EMOTION_MIN_ACTIVE_RATIO,
            )
            _cache_set_bounded(
                _FACIAL_EMOTION_CACHE,
                cache_key,
                [],
                ANALYSIS_CACHE_MAX_ITEMS,
            )
            return []

        series = list(zip(times, normalized.astype(float).tolist()))
        _cache_set_bounded(
            _FACIAL_EMOTION_CACHE,
            cache_key,
            series,
            ANALYSIS_CACHE_MAX_ITEMS,
        )
        return series
    except Exception as exc:
        LOGGER.debug("Facial emotion series failed: %s", exc)
        return []
    finally:
        cap.release()
