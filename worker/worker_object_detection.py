from __future__ import annotations

from pathlib import Path
import math
from typing import Any

from worker.worker_config import ANALYSIS_CACHE_MAX_ITEMS
from worker.worker_logging import LOGGER
from worker.worker_utils import _cache_set_bounded

try:
    import cv2

    OPENCV_AVAILABLE = True
except Exception:
    cv2 = None
    OPENCV_AVAILABLE = False

try:
    from ultralytics import YOLO

    ULTRALYTICS_AVAILABLE = True
except Exception:
    YOLO = None
    ULTRALYTICS_AVAILABLE = False


OBJECT_CAR_DETECTION_AVAILABLE = bool(OPENCV_AVAILABLE and ULTRALYTICS_AVAILABLE)
_CAR_CLASS_IDS = (2, 5, 7)  # COCO: car, bus, truck
_CAR_OBJECT_CACHE: dict[str, list[tuple[float, float]]] = {}
_YOLO_MODEL_CACHE: dict[str, Any] = {}


def _get_yolo_model(model_name: str) -> Any | None:
    if not ULTRALYTICS_AVAILABLE or YOLO is None:
        return None
    cache_key = str(model_name).strip() or "yolov8n.pt"
    if cache_key in _YOLO_MODEL_CACHE:
        return _YOLO_MODEL_CACHE[cache_key]
    try:
        model = YOLO(cache_key)
        _cache_set_bounded(_YOLO_MODEL_CACHE, cache_key, model, max_items=2)
        return model
    except Exception as exc:
        LOGGER.warning("YOLO load failed (%s): %s", cache_key, exc)
        return None


def _compute_car_object_presence_series(
    video_path: Path,
    *,
    sample_fps: float = 2.5,
    resize_width: int = 640,
    conf_threshold: float = 0.30,
    min_area_ratio: float = 0.012,
    model_name: str = "yolov8n.pt",
) -> list[tuple[float, float]]:
    """
    Returns [(timestamp, score_0_to_1)] where score indicates confidence that
    a car/truck/bus is clearly visible in the frame.
    """
    if not OBJECT_CAR_DETECTION_AVAILABLE or cv2 is None:
        return []
    if not isinstance(video_path, Path) or not video_path.exists():
        return []

    safe_fps = max(0.5, float(sample_fps))
    safe_resize = max(224, int(resize_width))
    safe_conf = max(0.0, min(1.0, float(conf_threshold)))
    safe_min_area = max(0.001, min(0.50, float(min_area_ratio)))
    safe_model = str(model_name).strip() or "yolov8n.pt"

    try:
        stat = video_path.stat()
        file_stamp = f"{int(stat.st_mtime_ns)}:{int(stat.st_size)}"
    except Exception:
        file_stamp = "na"

    cache_key = (
        f"{video_path}|{file_stamp}|car_object|{safe_fps:.3f}|{safe_resize}|"
        f"{safe_conf:.3f}|{safe_min_area:.4f}|{safe_model}"
    )
    if cache_key in _CAR_OBJECT_CACHE:
        return _CAR_OBJECT_CACHE[cache_key]

    model = _get_yolo_model(safe_model)
    if model is None:
        return []

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

            frame_h, frame_w = frame.shape[:2]
            if frame_w > safe_resize:
                scale = safe_resize / float(frame_w)
                new_h = max(160, int(frame_h * scale))
                frame = cv2.resize(frame, (safe_resize, new_h), interpolation=cv2.INTER_AREA)
                frame_h, frame_w = frame.shape[:2]

            frame_area = max(1.0, float(frame_h * frame_w))
            score = 0.0

            try:
                img_size = max(320, int(math.ceil(max(frame_h, frame_w) / 32.0) * 32))
                try:
                    results = model.predict(
                        source=frame,
                        conf=safe_conf,
                        classes=list(_CAR_CLASS_IDS),
                        imgsz=img_size,
                        verbose=False,
                    )
                except TypeError:
                    results = model.predict(
                        source=frame,
                        conf=safe_conf,
                        classes=list(_CAR_CLASS_IDS),
                        verbose=False,
                    )
            except Exception as exc:
                LOGGER.debug("YOLO predict failed at frame %d: %s", frame_index, exc)
                results = []

            if results:
                result = results[0]
                boxes = getattr(result, "boxes", None)
                if boxes is not None and len(boxes) > 0:
                    max_conf = 0.0
                    max_area_ratio = 0.0
                    total_area_ratio = 0.0
                    kept_detections = 0

                    for det_idx in range(len(boxes)):
                        try:
                            cls_id = int(boxes.cls[det_idx].item())
                        except Exception:
                            cls_id = -1
                        if cls_id not in _CAR_CLASS_IDS:
                            continue

                        try:
                            conf = float(boxes.conf[det_idx].item())
                        except Exception:
                            conf = 0.0

                        try:
                            x1, y1, x2, y2 = [float(v) for v in boxes.xyxy[det_idx].tolist()]
                        except Exception:
                            continue

                        width = max(0.0, x2 - x1)
                        height = max(0.0, y2 - y1)
                        area_ratio = (width * height) / frame_area
                        if area_ratio < (safe_min_area * 0.35):
                            continue

                        kept_detections += 1
                        max_conf = max(max_conf, conf)
                        max_area_ratio = max(max_area_ratio, area_ratio)
                        total_area_ratio += area_ratio

                    if kept_detections > 0:
                        size_factor = min(1.0, max_area_ratio / max(safe_min_area, 1e-6))
                        coverage_factor = min(
                            1.0,
                            total_area_ratio / max(safe_min_area * 2.6, 1e-6),
                        )
                        score = (
                            max_conf * 0.66
                            + size_factor * 0.22
                            + coverage_factor * 0.12
                        )
                        if kept_detections >= 2 and total_area_ratio >= (safe_min_area * 2.4):
                            score += 0.04
                        score = max(0.0, min(1.0, score))

            times.append(frame_index / fps)
            raw_scores.append(score)
            frame_index += 1

        if not raw_scores:
            _cache_set_bounded(_CAR_OBJECT_CACHE, cache_key, [], ANALYSIS_CACHE_MAX_ITEMS)
            return []

        if len(raw_scores) >= 3:
            smoothed: list[float] = []
            for idx, raw in enumerate(raw_scores):
                left = max(0, idx - 1)
                right = min(len(raw_scores), idx + 2)
                avg_local = sum(raw_scores[left:right]) / max(1, right - left)
                smoothed_score = raw * 0.65 + avg_local * 0.35
                smoothed.append(max(0.0, min(1.0, smoothed_score)))
            raw_scores = smoothed

        series = list(zip(times, raw_scores))
        _cache_set_bounded(_CAR_OBJECT_CACHE, cache_key, series, ANALYSIS_CACHE_MAX_ITEMS)
        return series
    except Exception as exc:
        LOGGER.debug("Car object detection failed: %s", exc)
        return []
    finally:
        cap.release()

