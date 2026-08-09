from __future__ import annotations

from pathlib import Path

from worker.worker_config import ANALYSIS_CACHE_MAX_ITEMS
from worker.worker_logging import LOGGER
from worker.worker_utils import _cache_set_bounded

# scenedetect for video scene change detection.
try:
    from scenedetect import AdaptiveDetector, ContentDetector, detect

    SCENEDETECT_AVAILABLE = True
except Exception:
    detect = None
    ContentDetector = None
    AdaptiveDetector = None
    SCENEDETECT_AVAILABLE = False

_SCENE_CACHE: dict[str, list[tuple[float, float]]] = {}


def _detect_scene_changes(
    video_path: Path,
    downscale_factor: int = 4,
    frame_skip: int = 2,
) -> list[tuple[float, float]]:
    """
    Detects scene changes in the video and returns [(scene_start, scene_end)].
    """
    cache_key = str(video_path)
    if cache_key in _SCENE_CACHE:
        return _SCENE_CACHE[cache_key]

    if not SCENEDETECT_AVAILABLE or detect is None:
        return []

    try:
        from scenedetect import SceneManager, open_video

        video = open_video(str(video_path))

        scene_manager = SceneManager()
        scene_manager.add_detector(AdaptiveDetector())
        scene_manager.downscale = downscale_factor

        LOGGER.info(
            "Scene detection: %dx downscale, analyzing 1 frame out of %d...",
            downscale_factor,
            frame_skip,
        )

        scene_manager.detect_scenes(video, frame_skip=frame_skip)
        scene_list = scene_manager.get_scene_list()

        result: list[tuple[float, float]] = []
        for scene in scene_list:
            start_time = scene[0].get_seconds()
            end_time = scene[1].get_seconds()
            result.append((start_time, end_time))

        _cache_set_bounded(_SCENE_CACHE, cache_key, result, ANALYSIS_CACHE_MAX_ITEMS)
        LOGGER.info("Scene detection: %d scenes found", len(result))
        return result

    except Exception as e:
        LOGGER.warning("Scene detection failed: %s", e)
        return []
