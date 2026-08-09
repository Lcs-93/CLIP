from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from clipvideo.config import EXPORTS_DIR, PREVIEWS_DIR, TEMP_DIR
from clipvideo.ffmpeg import (
    encode_clip,
    export_with_aspect,
    extract_audio_wav,
    get_duration_seconds,
)
from clipvideo.utils import now_iso, new_id

from worker.worker_audio import _compute_rms_series
from worker.worker_config import (
    EXPORT_PRESETS,
    LEGACY_EXPORT_MAP,
    OLLAMA_VISION_ENABLED,
    OLLAMA_VISION_GPU_HANDOFF,
)
from worker.worker_gpu import _prepare_cuda_for_ollama_vision
from worker.worker_logging import LOGGER
from worker.worker_selection import _fallback_segments, _select_segments
from worker.worker_transcript import _load_transcript_segments, _transcribe_video
from worker.worker_utils import _safe_unlink


def _fetch_one(conn, query: str, params: tuple = ()) -> dict | None:
    row = conn.execute(query, params).fetchone()
    return dict(row) if row else None


def _update_job(conn, job_id: str, status: str, message: str | None = None) -> None:
    conn.execute(
        "UPDATE jobs SET status = ?, message = ?, finished_at = ? WHERE id = ?",
        (status, message, now_iso(), job_id),
    )


def _update_job_message(conn, job_id: str, message: str) -> None:
    conn.execute(
        "UPDATE jobs SET message = ? WHERE id = ?",
        (message, job_id),
    )


def _mark_job_running(conn, job_id: str) -> None:
    conn.execute(
        "UPDATE jobs SET status = ?, started_at = ? WHERE id = ?",
        ("running", now_iso(), job_id),
    )


def _clear_video_clips(conn, video_id: str) -> None:
    clips = conn.execute(
        "SELECT id, preview_path FROM clips WHERE video_id = ?",
        (video_id,),
    ).fetchall()
    for clip in clips:
        exports = conn.execute(
            "SELECT output_path FROM exports WHERE clip_id = ?",
            (clip["id"],),
        ).fetchall()
        for export in exports:
            _safe_unlink(export["output_path"])
        _safe_unlink(clip["preview_path"])
    conn.execute(
        "DELETE FROM exports WHERE clip_id IN (SELECT id FROM clips WHERE video_id = ?)",
        (video_id,),
    )
    conn.execute("DELETE FROM clips WHERE video_id = ?", (video_id,))


def handle_analyze(conn, job: dict) -> None:
    video = _fetch_one(conn, "SELECT * FROM videos WHERE id = ?", (job["video_id"],))
    if not video:
        raise RuntimeError("Video not found for analyze job")
    source_path = Path(video["source_path"])
    LOGGER.info("Analyze start: %s", video["id"])
    _update_job_message(conn, job["id"], "Analyse: durée + transcription")
    conn.commit()  # Commit so progress updates are visible
    duration = get_duration_seconds(source_path)
    transcript_path = _transcribe_video(video["id"], source_path, duration, job["id"], conn)

    # Note: On ne décharge plus Whisper manuellement - ctranslate2 gère sa propre mémoire
    # et l'unloading causait des crashes CUDA

    conn.execute(
        "UPDATE videos SET duration_seconds = ?, transcript_path = ?, status = ? WHERE id = ?",
        (duration, str(transcript_path), "analyzed", video["id"]),
    )
    LOGGER.info("Analyze done: %s (duration %.2fs)", video["id"], duration)


def handle_generate(conn, job: dict) -> None:
    video = _fetch_one(conn, "SELECT * FROM videos WHERE id = ?", (job["video_id"],))
    if not video:
        raise RuntimeError("Video not found for generate job")

    source_path = Path(video["source_path"])
    duration = video.get("duration_seconds")
    if duration is None:
        duration = get_duration_seconds(source_path)
        conn.execute(
            "UPDATE videos SET duration_seconds = ? WHERE id = ?",
            (duration, video["id"]),
        )

    _clear_video_clips(conn, video["id"])

    LOGGER.info("Generate start: %s", video["id"])
    _update_job_message(conn, job["id"], "Génération: analyse audio")
    conn.commit()  # Commit so progress state is visible while selection is running

    if OLLAMA_VISION_ENABLED and OLLAMA_VISION_GPU_HANDOFF:
        _prepare_cuda_for_ollama_vision(
            reason="generate_start",
            release_whisper=True,
            release_diarization=True,
        )

    transcript_segments = _load_transcript_segments(video.get("transcript_path"))
    LOGGER.info("Transcript segments loaded: %s", len(transcript_segments))

    temp_wav = TEMP_DIR / f"{video['id']}_analysis.wav"
    try:
        extract_audio_wav(source_path, temp_wav)
        series = _compute_rms_series(temp_wav)
        LOGGER.info("Audio RMS windows: %s", len(series))
        _update_job_message(conn, job["id"], "Génération: sélection des segments")

        # Passe les chemins audio/vidéo pour les analyses avancées
        segments = _select_segments(
            float(duration),
            series,
            video["id"],
            transcript_segments,
            audio_path=temp_wav,  # Pour prosodie et diarization
            video_path=source_path,  # Pour scene detection
        )
    except Exception as exc:
        LOGGER.exception("Segment selection failed, fallback to default: %s", exc)
        _update_job_message(conn, job["id"], f"Fallback segments (selection error): {exc}")
        conn.commit()
        segments = _fallback_segments(float(duration), video["id"])
    finally:
        _safe_unlink(temp_wav)

    LOGGER.info("Segments selected: %s", len(segments))

    # Prepare clip data for parallel encoding
    clip_tasks = []
    for start_seconds, length, score, tag, reason, features in segments:
        clip_id = new_id("clip")
        preview_path = PREVIEWS_DIR / f"{clip_id}.mp4"
        tiktok_title = features.get("tiktok_title") or f"{tag.upper()}: moment à voir"
        clip_tasks.append({
            "clip_id": clip_id,
            "start_seconds": start_seconds,
            "length": length,
            "score": score,
            "tag": tag,
            "reason": reason,
            "features": features,
            "tiktok_title": tiktok_title,
            "preview_path": preview_path,
        })

    # Encode clips in parallel (up to 3 concurrent)
    max_workers = min(3, len(clip_tasks)) if clip_tasks else 1
    encoded_clips = []

    def encode_single_clip(task: dict) -> dict:
        encode_clip(source_path, task["start_seconds"], task["length"], task["preview_path"])
        return task

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(encode_single_clip, task): i for i, task in enumerate(clip_tasks)}
        for i, future in enumerate(as_completed(futures)):
            task = future.result()
            encoded_clips.append(task)
            # Progress tracking
            progress_pct = int(((i + 1) / len(clip_tasks)) * 100)
            _update_job_message(conn, job["id"], f"Encodage clips: {progress_pct}% ({i + 1}/{len(clip_tasks)})")
            conn.commit()
            LOGGER.info("Clip encoded: %s (%d/%d)", task["clip_id"], i + 1, len(clip_tasks))

    # Insert clips into database
    for task in encoded_clips:
        conn.execute(
            "INSERT INTO clips (id, video_id, start_seconds, end_seconds, score, tag, reason, signals, tiktok_title, preview_path, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                task["clip_id"],
                video["id"],
                task["start_seconds"],
                task["start_seconds"] + task["length"],
                task["score"],
                task["tag"],
                task["reason"],
                json.dumps(task["features"], ensure_ascii=False),
                task["tiktok_title"],
                str(task["preview_path"]),
                "ready",
                now_iso(),
            ),
        )

    conn.execute(
        "UPDATE videos SET status = ? WHERE id = ?",
        ("ready", video["id"]),
    )
    LOGGER.info("Generate done: %s", video["id"])


def handle_export(conn, job: dict) -> None:
    payload = json.loads(job.get("payload") or "{}")
    clip_id = payload.get("clip_id")
    export_id = payload.get("export_id")
    mode = payload.get("mode")
    preset = payload.get("preset")

    if not clip_id or not export_id:
        raise RuntimeError("Invalid export payload")

    if not preset and mode in LEGACY_EXPORT_MAP:
        preset = LEGACY_EXPORT_MAP[mode]

    if not preset or preset not in EXPORT_PRESETS:
        raise RuntimeError("Invalid export payload")

    clip = _fetch_one(conn, "SELECT * FROM clips WHERE id = ?", (clip_id,))
    if not clip:
        raise RuntimeError("Clip not found for export job")
    video = _fetch_one(conn, "SELECT * FROM videos WHERE id = ?", (clip["video_id"],))
    if not video:
        raise RuntimeError("Video not found for export job")

    output_path = EXPORTS_DIR / f"{clip_id}_{preset}.mp4"
    source_path = Path(video["source_path"])
    duration = clip["end_seconds"] - clip["start_seconds"]
    preset_config = EXPORT_PRESETS[preset]
    LOGGER.info("Export start: clip=%s preset=%s", clip_id, preset)
    export_with_aspect(
        source_path,
        clip["start_seconds"],
        duration,
        output_path,
        preset_config["width"],
        preset_config["height"],
        mode=preset_config["mode"],
    )

    conn.execute(
        "UPDATE exports SET status = ? WHERE id = ?",
        ("done", export_id),
    )
    LOGGER.info("Export done: clip=%s", clip_id)


def _mark_export_error(conn, job: dict, message: str) -> None:
    payload = json.loads(job.get("payload") or "{}")
    export_id = payload.get("export_id")
    if export_id:
        conn.execute(
            "UPDATE exports SET status = ? WHERE id = ?",
            ("error", export_id),
        )


def _mark_video_error(conn, job: dict) -> None:
    video_id = job.get("video_id")
    if video_id:
        conn.execute(
            "UPDATE videos SET status = ? WHERE id = ?",
            ("error", video_id),
        )
