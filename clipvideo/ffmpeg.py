from __future__ import annotations

import subprocess
from pathlib import Path


def _run_ffmpeg(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args],
        capture_output=True,
        text=True,
    )


def _run_ffprobe(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["ffprobe", "-v", "error", *args],
        capture_output=True,
        text=True,
    )


def get_duration_seconds(path: Path) -> float:
    result = _run_ffprobe(
        [
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe failed")
    return float(result.stdout.strip())


def extract_audio_wav(source: Path, output: Path, sample_rate: int = 16000) -> None:
    result = _run_ffmpeg(
        [
            "-i",
            str(source),
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-sample_fmt",
            "s16",
            "-vn",
            str(output),
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffmpeg audio extract failed")


def encode_clip(
    source: Path,
    start_seconds: float,
    duration_seconds: float,
    output: Path,
    video_filter: str | None = None,
) -> None:
    base_args = [
        "-ss",
        f"{start_seconds:.3f}",
        "-t",
        f"{duration_seconds:.3f}",
        "-i",
        str(source),
    ]
    if video_filter:
        base_args += ["-vf", video_filter]
    nvenc_args = base_args + [
        "-c:v",
        "h264_nvenc",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(output),
    ]
    result = _run_ffmpeg(nvenc_args)
    if result.returncode == 0:
        return

    cpu_args = base_args + [
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(output),
    ]
    cpu_result = _run_ffmpeg(cpu_args)
    if cpu_result.returncode != 0:
        message = cpu_result.stderr.strip() or result.stderr.strip() or "ffmpeg failed"
        raise RuntimeError(message)


def export_vertical(
    source: Path,
    start_seconds: float,
    duration_seconds: float,
    output: Path,
    mode: str,
) -> None:
    if mode == "talking":
        export_with_aspect(source, start_seconds, duration_seconds, output, 1080, 1920, mode="crop")
        return
    export_with_aspect(source, start_seconds, duration_seconds, output, 1080, 1920, mode="fit")


def export_with_aspect(
    source: Path,
    start_seconds: float,
    duration_seconds: float,
    output: Path,
    target_width: int,
    target_height: int,
    mode: str = "crop",
) -> None:
    if mode == "crop":
        video_filter = (
            f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
            f"crop={target_width}:{target_height}"
        )
    elif mode == "fit":
        video_filter = (
            f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
            f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:color=black"
        )
    else:
        raise ValueError(f"Unknown export mode: {mode}")
    encode_clip(source, start_seconds, duration_seconds, output, video_filter=video_filter)
