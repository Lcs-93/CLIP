from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Iterable

from clipvideo.ffmpeg import extract_audio_wav

from clipvideo.config import TEMP_DIR, TRANSCRIPTS_DIR
from worker.worker_logging import LOGGER
from worker.worker_utils import _safe_unlink


def _configure_windows_dll_paths() -> None:
    """
    Ensure FFmpeg and Torch DLL directories are registered on Windows.

    Python on Windows may require explicit DLL directories for transitive
    dependencies (notably torchcodec -> FFmpeg shared libraries).
    """
    if os.name != "nt" or not hasattr(os, "add_dll_directory"):
        return

    candidates: list[Path] = []

    ffmpeg_exe = shutil.which("ffmpeg")
    if ffmpeg_exe:
        try:
            candidates.append(Path(ffmpeg_exe).resolve().parent)
        except Exception:
            candidates.append(Path(ffmpeg_exe).parent)

    candidates.append(Path("C:/ffmpeg/bin"))
    candidates.append(Path(sys.prefix) / "Lib" / "site-packages" / "torch" / "lib")

    seen: set[str] = set()
    for directory in candidates:
        try:
            resolved = directory.resolve()
        except Exception:
            resolved = directory

        key = str(resolved).lower()
        if key in seen:
            continue
        seen.add(key)

        if not resolved.exists():
            continue

        try:
            os.add_dll_directory(str(resolved))
        except Exception:
            continue


_configure_windows_dll_paths()

try:
    from faster_whisper import WhisperModel
except Exception:  # pragma: no cover - optional dependency
    WhisperModel = None

try:
    import whisperx
except Exception:  # pragma: no cover - optional dependency
    whisperx = None

_WHISPER_MODEL_CACHE: dict[str, Any] = {}
_WHISPERX_MODEL_CACHE: dict[str, Any] = {}
_WHISPERX_ALIGN_CACHE: dict[str, tuple[Any, Any]] = {}
TXT_SEGMENT_RE = re.compile(r"^\[(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)\]\s*(.+)$")
WORD_TOKEN_RE = re.compile(r"[\w']+", re.UNICODE)
JUNK_TRANSCRIPT_PATTERNS = (
    re.compile(r"\bteksting\s+av\b", re.IGNORECASE),
    re.compile(r"\bsubtitles?\s+by\b", re.IGNORECASE),
    re.compile(r"\bcaptions?\s+by\b", re.IGNORECASE),
    re.compile(r"\btranscrib(?:ed|ing)\s+by\b", re.IGNORECASE),
    re.compile(r"\bthanks?\s+for\s+watching\b", re.IGNORECASE),
    re.compile(r"\bmerci\s+d[' ]avoir\s+regard", re.IGNORECASE),
)


def _release_transcription_model_cache() -> int:
    """
    Drop in-process Whisper/WhisperX model references.
    Returns the number of cache entries released.
    """
    released = (
        len(_WHISPER_MODEL_CACHE)
        + len(_WHISPERX_MODEL_CACHE)
        + len(_WHISPERX_ALIGN_CACHE)
    )
    _WHISPER_MODEL_CACHE.clear()
    _WHISPERX_MODEL_CACHE.clear()
    _WHISPERX_ALIGN_CACHE.clear()
    if released > 0:
        LOGGER.info("Transcription model cache released: %d entries", released)
    return released


def _segment_word_count(segment: dict[str, Any]) -> int:
    words = segment.get("words", [])
    if isinstance(words, list) and words:
        count = 0
        for word in words:
            if not isinstance(word, dict):
                continue
            token = str(word.get("word", "")).strip()
            if token:
                count += 1
        if count > 0:
            return count
    text = str(segment.get("text", "")).strip()
    return len(WORD_TOKEN_RE.findall(text))


def _sanitize_transcript_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sanitized: list[dict[str, Any]] = []
    dropped = 0
    for segment in segments:
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        normalized = re.sub(r"\s+", " ", text).strip().lower()
        if any(pattern.search(normalized) for pattern in JUNK_TRANSCRIPT_PATTERNS):
            dropped += 1
            continue
        sanitized.append(segment)

    if dropped > 0:
        LOGGER.info("Transcript sanitization dropped %d low-value segment(s)", dropped)
    return sanitized


def _is_low_value_transcript(segments: list[dict[str, Any]]) -> tuple[bool, str]:
    if not segments:
        return True, "empty"

    total_words = 0
    total_duration = 0.0
    word_timestamps = 0
    for segment in segments:
        total_words += _segment_word_count(segment)
        start = _safe_float(segment.get("start"), 0.0)
        end = _safe_float(segment.get("end"), start)
        if end > start:
            total_duration += end - start
        words = segment.get("words", [])
        if isinstance(words, list):
            for word in words:
                if not isinstance(word, dict):
                    continue
                if str(word.get("word", "")).strip():
                    word_timestamps += 1

    if len(segments) <= 1 and total_words <= 6 and total_duration <= 1.5 and word_timestamps == 0:
        return True, "single_short_no_word_timestamps"
    if total_words <= 4 and total_duration <= 1.2:
        return True, "too_few_words"
    return False, ""


def _update_transcription_progress(
    job_id: str | None,
    conn_for_progress: Any,
    message: str,
) -> None:
    if not job_id or conn_for_progress is None:
        return
    try:
        conn_for_progress.execute(
            "UPDATE jobs SET message = ? WHERE id = ?",
            (message, job_id),
        )
        conn_for_progress.commit()
    except Exception:
        return


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_word(word: dict[str, Any]) -> dict[str, Any] | None:
    word_text = str(word.get("word", word.get("text", ""))).strip()
    if not word_text:
        return None

    start = _safe_float(word.get("start"), -1.0)
    end = _safe_float(word.get("end"), -1.0)
    if start < 0 or end < 0 or end < start:
        return None

    entry: dict[str, Any] = {
        "word": word_text,
        "start": start,
        "end": end,
    }
    probability = word.get("probability", word.get("score"))
    if probability is not None:
        entry["probability"] = _safe_float(probability, 1.0)
    return entry


def _normalize_segments(raw_segments: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for seg in raw_segments:
        text = str(seg.get("text", "")).strip()
        if not text:
            continue

        start = _safe_float(seg.get("start"), 0.0)
        end = _safe_float(seg.get("end"), start)
        if end < start:
            end = start

        words_cleaned: list[dict[str, Any]] = []
        raw_words = seg.get("words", [])
        if isinstance(raw_words, list):
            for word in raw_words:
                if not isinstance(word, dict):
                    continue
                normalized = _normalize_word(word)
                if normalized is not None:
                    words_cleaned.append(normalized)

        cleaned.append(
            {
                "start": start,
                "end": end,
                "text": text,
                "words": words_cleaned,
            }
        )
    return cleaned


def _load_transcript_segments(path_value: str | None) -> list[dict[str, Any]]:
    if not path_value:
        return []
    path = Path(path_value)
    if not path.exists():
        LOGGER.warning("Transcript file missing: %s", path)
        return []
    suffix = path.suffix.lower()
    if suffix == ".txt":
        segments: list[dict[str, Any]] = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                m = TXT_SEGMENT_RE.match(line)
                if not m:
                    continue
                start = float(m.group(1))
                end = float(m.group(2))
                text = m.group(3).strip()
                if not text:
                    continue
                segments.append(
                    {
                        "start": start,
                        "end": end,
                        "text": text,
                        "words": [],
                    }
                )
            if segments:
                LOGGER.info("Transcript TXT parsed: %s (%d segments)", path, len(segments))
            else:
                LOGGER.info("Transcript TXT has no parsable segments: %s", path)
            return segments
        except Exception:
            LOGGER.exception("Failed to read transcript TXT: %s", path)
            return []
    if suffix != ".json":
        LOGGER.info("Transcript file format unsupported, skipping: %s", path)
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        LOGGER.exception("Failed to read transcript JSON: %s", path)
        return []
    if data.get("error"):
        LOGGER.warning("Transcript JSON has error: %s", data.get("error"))
        return []
    segments = data.get("segments", [])
    if not isinstance(segments, list):
        return []
    return _normalize_segments(segments)


def _write_transcript_files(
    video_id: str,
    source_path: Path,
    duration: float,
    segments: Iterable[dict[str, Any]],
    language: str | None = None,
    error: str | None = None,
) -> Path:
    segments_list = list(segments)
    json_path = TRANSCRIPTS_DIR / f"{video_id}.json"
    text_path = TRANSCRIPTS_DIR / f"{video_id}.txt"

    json_path.write_text(
        json.dumps(
            {"language": language, "segments": segments_list, "error": error},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    if error:
        text_path.write_text(
            f"Transcription placeholder for {source_path.name}\nDuration: {duration:.2f}s\nError: {error}\n",
            encoding="utf-8",
        )
        LOGGER.warning("Transcript failed for %s: %s", video_id, error)
    else:
        lines = [
            f"[{seg['start']:.2f}-{seg['end']:.2f}] {seg['text']}" for seg in segments_list
        ]
        text_path.write_text("\n".join(lines), encoding="utf-8")
        LOGGER.info("Transcript written for %s (%s segments)", video_id, len(segments_list))
    LOGGER.info("Transcript JSON path: %s", json_path)
    return json_path


def _get_faster_whisper_model(model_size: str, device: str, compute_type: str) -> Any:
    if WhisperModel is None:
        raise RuntimeError("faster_whisper_not_installed")

    requested_key = f"{model_size}|{device}|{compute_type}"
    if requested_key in _WHISPER_MODEL_CACHE:
        return _WHISPER_MODEL_CACHE[requested_key]

    try:
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
        _WHISPER_MODEL_CACHE[requested_key] = model
        return model
    except Exception:
        LOGGER.warning("Whisper CUDA init failed, falling back to CPU.")
        cpu_key = f"{model_size}|cpu|int8"
        if cpu_key not in _WHISPER_MODEL_CACHE:
            _WHISPER_MODEL_CACHE[cpu_key] = WhisperModel(
                model_size,
                device="cpu",
                compute_type="int8",
            )
        return _WHISPER_MODEL_CACHE[cpu_key]


def _transcribe_with_faster_whisper(
    path: Path,
    *,
    duration: float,
    model_size: str,
    device: str,
    compute_type: str,
    whisper_language: str,
    force_language: bool,
    job_id: str | None,
    conn_for_progress: Any,
) -> tuple[list[dict[str, Any]], str | None]:
    model = _get_faster_whisper_model(model_size, device, compute_type)

    LOGGER.info("faster-whisper transcription started: %s", path)
    _update_transcription_progress(job_id, conn_for_progress, "Transcription: 5%")

    start_time = time.monotonic()
    last_log = start_time
    transcribe_options: dict[str, Any] = {
        "beam_size": 5,
        "word_timestamps": True,
        "vad_filter": True,
        "vad_parameters": {"min_silence_duration_ms": 300},
    }
    if force_language:
        transcribe_options["language"] = whisper_language

    try:
        segments_iter, info = model.transcribe(str(path), **transcribe_options)
    except Exception as exc:
        if force_language:
            LOGGER.warning(
                "Whisper failed with WHISPER_LANGUAGE=%s (%s). Retrying with auto-detect.",
                whisper_language,
                exc,
            )
            transcribe_options.pop("language", None)
            segments_iter, info = model.transcribe(str(path), **transcribe_options)
        else:
            raise

    segments: list[dict[str, Any]] = []
    audio_duration = max(duration, 0.1)
    for segment in segments_iter:
        text = str(getattr(segment, "text", "")).strip()
        if not text:
            continue

        words: list[dict[str, Any]] = []
        segment_words = getattr(segment, "words", None)
        if segment_words:
            for word in segment_words:
                word_text = str(getattr(word, "word", "")).strip()
                if not word_text:
                    continue
                word_start = _safe_float(getattr(word, "start", None), -1.0)
                word_end = _safe_float(getattr(word, "end", None), -1.0)
                if word_start < 0 or word_end < 0 or word_end < word_start:
                    continue
                words.append(
                    {
                        "word": word_text,
                        "start": word_start,
                        "end": word_end,
                        "probability": _safe_float(
                            getattr(word, "probability", 1.0),
                            1.0,
                        ),
                    }
                )

        seg_start = _safe_float(getattr(segment, "start", 0.0), 0.0)
        seg_end = _safe_float(getattr(segment, "end", seg_start), seg_start)
        segments.append(
            {
                "start": seg_start,
                "end": max(seg_start, seg_end),
                "text": text,
                "words": words,
            }
        )

        now = time.monotonic()
        if now - last_log >= 5:
            elapsed = now - start_time
            progress_pct = min(98, int((seg_end / audio_duration) * 100))
            LOGGER.info(
                "Transcription: %d%% (%d segments, %.1fs elapsed)",
                progress_pct,
                len(segments),
                elapsed,
            )
            _update_transcription_progress(
                job_id,
                conn_for_progress,
                f"Transcription: {progress_pct}%",
            )
            last_log = now

    LOGGER.info("faster-whisper transcription done: %d segments", len(segments))
    _update_transcription_progress(job_id, conn_for_progress, "Transcription: 99%")
    return segments, getattr(info, "language", None)


def _get_whisperx_model(
    model_size: str,
    device: str,
    compute_type: str,
    language: str | None,
) -> tuple[Any, str]:
    if whisperx is None:
        raise RuntimeError("whisperx_not_installed")

    language_key = language or "auto"
    cache_key = f"{model_size}|{device}|{compute_type}|{language_key}"
    if cache_key in _WHISPERX_MODEL_CACHE:
        return _WHISPERX_MODEL_CACHE[cache_key], device

    load_kwargs: dict[str, Any] = {
        "device": device,
        "compute_type": compute_type,
    }
    if language:
        load_kwargs["language"] = language

    try:
        model = whisperx.load_model(model_size, **load_kwargs)
        _WHISPERX_MODEL_CACHE[cache_key] = model
        return model, device
    except Exception:
        if device == "cpu":
            raise
        LOGGER.warning("WhisperX CUDA init failed, falling back to CPU.")
        cpu_key = f"{model_size}|cpu|int8|{language_key}"
        if cpu_key not in _WHISPERX_MODEL_CACHE:
            cpu_kwargs: dict[str, Any] = {
                "device": "cpu",
                "compute_type": "int8",
            }
            if language:
                cpu_kwargs["language"] = language
            _WHISPERX_MODEL_CACHE[cpu_key] = whisperx.load_model(
                model_size,
                **cpu_kwargs,
            )
        return _WHISPERX_MODEL_CACHE[cpu_key], "cpu"


def _get_whisperx_align_model(
    language_code: str,
    device: str,
) -> tuple[Any, Any, str]:
    if whisperx is None:
        raise RuntimeError("whisperx_not_installed")

    key = f"{language_code}|{device}"
    if key in _WHISPERX_ALIGN_CACHE:
        align_model, metadata = _WHISPERX_ALIGN_CACHE[key]
        return align_model, metadata, device

    try:
        align_model, metadata = whisperx.load_align_model(
            language_code=language_code,
            device=device,
        )
        _WHISPERX_ALIGN_CACHE[key] = (align_model, metadata)
        return align_model, metadata, device
    except Exception:
        if device == "cpu":
            raise
        cpu_key = f"{language_code}|cpu"
        if cpu_key in _WHISPERX_ALIGN_CACHE:
            align_model, metadata = _WHISPERX_ALIGN_CACHE[cpu_key]
            return align_model, metadata, "cpu"
        align_model, metadata = whisperx.load_align_model(
            language_code=language_code,
            device="cpu",
        )
        _WHISPERX_ALIGN_CACHE[cpu_key] = (align_model, metadata)
        return align_model, metadata, "cpu"


def _transcribe_with_whisperx(
    path: Path,
    *,
    duration: float,
    model_size: str,
    device: str,
    compute_type: str,
    whisper_language: str,
    force_language: bool,
    job_id: str | None,
    conn_for_progress: Any,
) -> tuple[list[dict[str, Any]], str | None]:
    if whisperx is None:
        raise RuntimeError("whisperx_not_installed")

    LOGGER.info("WhisperX transcription started: %s", path)
    _update_transcription_progress(job_id, conn_for_progress, "Transcription WhisperX: 8%")

    batch_size = int(os.getenv("WHISPERX_BATCH_SIZE", "8"))
    if batch_size < 1:
        batch_size = 1
    align_enabled = os.getenv("WHISPERX_ALIGN", "true").lower() == "true"

    language_for_model = whisper_language if force_language else None
    model, model_device = _get_whisperx_model(
        model_size,
        device,
        compute_type,
        language_for_model,
    )

    audio = whisperx.load_audio(str(path))
    _update_transcription_progress(job_id, conn_for_progress, "Transcription WhisperX: 35%")

    transcribe_kwargs: dict[str, Any] = {
        "batch_size": batch_size,
    }
    if force_language:
        transcribe_kwargs["language"] = whisper_language

    try:
        result = model.transcribe(audio, **transcribe_kwargs)
    except TypeError:
        transcribe_kwargs.pop("language", None)
        result = model.transcribe(audio, **transcribe_kwargs)

    if not isinstance(result, dict):
        raise RuntimeError("whisperx_invalid_result")

    segments_raw = result.get("segments", [])
    if not isinstance(segments_raw, list):
        segments_raw = []

    detected_language = str(result.get("language", "")).strip().lower() or None

    if align_enabled and segments_raw:
        align_language = whisper_language if force_language else detected_language
        if align_language:
            try:
                align_model, metadata, align_device = _get_whisperx_align_model(
                    align_language,
                    model_device,
                )
                aligned_result = whisperx.align(
                    segments_raw,
                    align_model,
                    metadata,
                    audio,
                    align_device,
                    return_char_alignments=False,
                )
                if isinstance(aligned_result, dict) and isinstance(
                    aligned_result.get("segments"),
                    list,
                ):
                    segments_raw = aligned_result["segments"]
            except Exception as exc:
                LOGGER.warning(
                    "WhisperX alignment skipped (%s): %s",
                    align_language,
                    exc,
                )

    cleaned_segments = _normalize_segments(segments_raw)

    # WhisperX can return no words for some languages/audio; keep transcript anyway.
    if not cleaned_segments:
        raise RuntimeError("whisperx_empty_transcript")

    elapsed_hint = max(1, int(round(duration)))
    LOGGER.info(
        "WhisperX transcription done: %d segments (duration %.1fs)",
        len(cleaned_segments),
        float(elapsed_hint),
    )
    _update_transcription_progress(job_id, conn_for_progress, "Transcription WhisperX: 99%")
    return cleaned_segments, detected_language


def _pick_backends(requested_backend: str, enable_whisperx: bool) -> list[str]:
    normalized = requested_backend.strip().lower()
    if normalized in {"faster", "faster-whisper"}:
        order = ["faster-whisper", "whisperx"]
    elif normalized in {"auto", "whisperx"}:
        order = ["whisperx", "faster-whisper"]
    else:
        order = ["whisperx", "faster-whisper"]

    available: list[str] = []
    for backend in order:
        if backend == "whisperx":
            if enable_whisperx and whisperx is not None:
                available.append(backend)
            continue
        if backend == "faster-whisper" and WhisperModel is not None:
            available.append(backend)

    return available


def _transcribe_video(
    video_id: str,
    source_path: Path,
    duration: float,
    job_id: str | None = None,
    conn=None,
) -> Path:
    """Transcribe video with WhisperX/faster-whisper and word-level timestamps."""
    model_size = os.getenv("WHISPER_MODEL", "large-v3")
    device = os.getenv("WHISPER_DEVICE", "cuda")
    compute_type = os.getenv(
        "WHISPER_COMPUTE_TYPE",
        "float16" if device == "cuda" else "int8",
    )
    whisper_language = os.getenv("WHISPER_LANGUAGE", "auto").strip().lower()
    force_language = whisper_language not in {"", "auto", "detect"}
    if force_language:
        LOGGER.info("Whisper language forced via WHISPER_LANGUAGE=%s", whisper_language)
    else:
        LOGGER.info("Whisper language auto-detect enabled")

    enable_whisperx = os.getenv("ENABLE_WHISPERX", "true").lower() == "true"
    requested_backend = os.getenv("WHISPER_BACKEND", "whisperx")
    backends = _pick_backends(requested_backend, enable_whisperx)

    if not backends:
        LOGGER.warning("No Whisper backend available.")
        return _write_transcript_files(
            video_id,
            source_path,
            duration,
            segments=[],
            error="whisper_not_installed",
        )

    LOGGER.info("Transcription backend order: %s", ", ".join(backends))

    def _run_with_backends(path: Path) -> tuple[list[dict[str, Any]], str | None]:
        errors: list[str] = []
        low_value_seen = False
        for backend in backends:
            try:
                if backend == "whisperx":
                    segments, language = _transcribe_with_whisperx(
                        path,
                        duration=duration,
                        model_size=model_size,
                        device=device,
                        compute_type=compute_type,
                        whisper_language=whisper_language,
                        force_language=force_language,
                        job_id=job_id,
                        conn_for_progress=conn,
                    )
                else:
                    segments, language = _transcribe_with_faster_whisper(
                        path,
                        duration=duration,
                        model_size=model_size,
                        device=device,
                        compute_type=compute_type,
                        whisper_language=whisper_language,
                        force_language=force_language,
                        job_id=job_id,
                        conn_for_progress=conn,
                    )

                segments = _sanitize_transcript_segments(segments)
                low_value, reason = _is_low_value_transcript(segments)
                if low_value:
                    low_value_seen = True
                    LOGGER.warning(
                        "%s produced low-value transcript (%s) on %s; trying next backend.",
                        backend,
                        reason,
                        path,
                    )
                    errors.append(f"{backend}:low_value_transcript:{reason}")
                    continue

                return segments, language
            except Exception as exc:
                LOGGER.warning("%s failed on %s: %s", backend, path, exc)
                errors.append(f"{backend}:{exc}")
                continue

        if low_value_seen:
            LOGGER.warning(
                "No reliable transcript on %s (details: %s). Using empty transcript.",
                path,
                "; ".join(errors) if errors else "low-value transcript",
            )
            return [], None

        raise RuntimeError("; ".join(errors) if errors else "transcription_failed")

    try:
        try:
            segments, language = _run_with_backends(source_path)
            return _write_transcript_files(
                video_id,
                source_path,
                duration,
                segments=segments,
                language=language,
            )
        except Exception:
            LOGGER.warning("Transcription failed on source video, retry with WAV.")
            temp_wav = TEMP_DIR / f"{video_id}_whisper.wav"
            try:
                extract_audio_wav(source_path, temp_wav)
                segments, language = _run_with_backends(temp_wav)
                return _write_transcript_files(
                    video_id,
                    source_path,
                    duration,
                    segments=segments,
                    language=language,
                )
            finally:
                _safe_unlink(temp_wav)
    except Exception as exc:
        LOGGER.exception("Whisper transcription failed: %s", exc)
        return _write_transcript_files(
            video_id,
            source_path,
            duration,
            segments=[],
            error=f"whisper_failed: {exc}",
        )


