from __future__ import annotations

import gc

from worker.worker_logging import LOGGER


def _bytes_to_mib(value: int) -> float:
    return float(value) / (1024.0 * 1024.0)


def _cuda_memory_snapshot() -> tuple[int, int] | None:
    try:
        import torch
    except Exception:
        return None

    if not torch.cuda.is_available():
        return None

    try:
        allocated = int(torch.cuda.memory_allocated())
        reserved = int(torch.cuda.memory_reserved())
    except Exception:
        return None
    return allocated, reserved


def _release_cuda_cache(reason: str) -> None:
    before = _cuda_memory_snapshot()

    gc.collect()
    try:
        import torch
    except Exception:
        return

    if not torch.cuda.is_available():
        return

    try:
        torch.cuda.empty_cache()
    except Exception:
        pass

    try:
        torch.cuda.ipc_collect()
    except Exception:
        pass

    after = _cuda_memory_snapshot()
    if before is not None and after is not None:
        LOGGER.info(
            "CUDA cache release (%s): alloc %.1f -> %.1f MiB, reserved %.1f -> %.1f MiB",
            reason,
            _bytes_to_mib(before[0]),
            _bytes_to_mib(after[0]),
            _bytes_to_mib(before[1]),
            _bytes_to_mib(after[1]),
        )
    else:
        LOGGER.info("CUDA cache release (%s)", reason)


def _prepare_cuda_for_ollama_vision(
    *,
    reason: str,
    release_whisper: bool,
    release_diarization: bool,
) -> None:
    whisper_released = 0
    diarization_released = False

    if release_whisper:
        try:
            from worker.worker_transcript import _release_transcription_model_cache

            whisper_released = int(_release_transcription_model_cache())
        except Exception as exc:
            LOGGER.debug("Whisper cache release skipped: %s", exc)

    if release_diarization:
        try:
            from worker.worker_diarization import _release_pyannote_pipeline_cache

            diarization_released = bool(
                _release_pyannote_pipeline_cache(clear_segments_cache=False)
            )
        except Exception as exc:
            LOGGER.debug("Diarization cache release skipped: %s", exc)

    _release_cuda_cache(reason)
    if release_whisper or release_diarization:
        LOGGER.info(
            "GPU handoff (%s): whisper_models=%d, diarization_pipeline_released=%s",
            reason,
            whisper_released,
            diarization_released,
        )
