from __future__ import annotations

from pathlib import Path
import random
import re
import time
import unicodedata
from typing import Any

from worker.worker_audio import (
    LIBROSA_AVAILABLE,
    SILERO_AVAILABLE,
    WEBCVAD_AVAILABLE,
    _analyze_pitch_contour,
    _analyze_pitch_trend_from_series,
    _compute_car_dynamics_series,
    _compute_car_start_stop_events,
    _compute_ffmpeg_silence_segments,
    _compute_onset_series,
    _compute_pitch_series,
    _compute_vad_series,
)
from worker.worker_audio_events import (
    YAMNET_AVAILABLE,
    _compute_yamnet_car_start_stop_events,
)
from worker.worker_audio_context import (
    INASPEECH_AVAILABLE,
    OPENSMILE_AVAILABLE,
    _compute_inaspeech_context_series,
    _compute_opensmile_voice_activity_series,
)
from worker.worker_config import (
    ALLOW_LOW_SCORE_CLIPS,
    AUDIO_CONTEXT_MUSIC_MIN_RATIO,
    AUDIO_CONTEXT_NOISE_MIN_RATIO,
    AUDIO_CONTEXT_PROVIDER,
    AUDIO_CONTEXT_SPEECH_MIN_RATIO,
    AUDIO_EVENT_COOLDOWN_SECONDS,
    AUDIO_EVENT_MIN_DELTA,
    AUDIO_EVENT_MIN_SCORE,
    AUDIO_EVENT_PROVIDER,
    AUDIO_EVENT_SMOOTH_SECONDS,
    AUDIO_EVENT_START_THRESHOLD,
    AUDIO_EVENT_STOP_THRESHOLD,
    ANALYSIS_WINDOW_SECONDS,
    ENABLE_AUDIO_CONTEXT_DETECTION,
    CAR_EVENT_COOLDOWN_SECONDS,
    CAR_EVENT_MIN_DELTA,
    CAR_EVENT_MIN_SCORE,
    CAR_SIGNALS_ONLY_IN_CAR_PROFILE,
    CAR_EVENT_SMOOTH_SECONDS,
    CAR_START_EVENT_THRESHOLD,
    CAR_STOP_EVENT_THRESHOLD,
    CLIP_VARIATION_JITTER,
    CLIP_VARIATION_SCORE_JITTER,
    CLIP_VARIATION_TOP_K,
    COMMERCIAL_REJECT_THRESHOLD,
    CLIP_MAX_SECONDS,
    CLIP_MIN_SECONDS,
    CLIP_PROFILE,
    BOUNDARY_LOW_SCORE_THRESHOLD,
    BOUNDARY_SNAP_MAX_SHIFT_SECONDS,
    CAR_ACCEL_THRESHOLD,
    CAR_GUARD_MIN_AUDIO,
    CAR_LOW_DIALOGUE_WPS,
    CAR_MIN_SUSTAIN_SECONDS,
    ENABLE_BOUNDARY_SNAP,
    ENABLE_CLIP_VARIATION,
    ENABLE_ADAPTIVE_SCORE,
    ENABLE_AUDIO_EVENT_DETECTION,
    ENABLE_CAR_DETECTION,
    ENABLE_CAR_START_STOP_DETECTION,
    ENABLE_FFMPEG_SILENCE_DETECTION,
    ENABLE_FACIAL_EMOTION_DETECTION,
    ENABLE_OPENSMILE,
    ENABLE_OBJECT_CAR_DETECTION,
    ENABLE_VISUAL_CAR_DETECTION,
    ENABLE_LOCAL_PEAKS,
    ENABLE_NMS,
    ENABLE_ONSET,
    ENABLE_VAD,
    FFMPEG_SILENCE_MIN_SECONDS,
    FFMPEG_SILENCE_NOISE_DB,
    MAX_CLIP_LENGTH,
    MERGE_GAP_SECONDS,
    MIN_CLIP_LENGTH,
    MIN_DISTANCE_SECONDS,
    MIN_SCORE,
    MERGE_KEEP_BEST_ONLY,
    OLLAMA_APPLY_TRIM_HINTS,
    OLLAMA_CHUNK_PAUSE_SECONDS,
    OLLAMA_CHUNK_SIZE,
    OLLAMA_HARD_REJECT,
    OLLAMA_TEXT_MIN_SEGMENTS,
    OLLAMA_TEXT_MIN_WORDS,
    OLLAMA_TEXT_MIN_UNIQUE_WORDS,
    OLLAMA_TEXT_MIN_SPOKEN_SECONDS,
    OLLAMA_TEXT_MIN_COVERAGE_RATIO,
    OLLAMA_TEXT_MIN_AVG_WORDS_PER_SEGMENT,
    OLLAMA_TEXT_MIN_WPS,
    OLLAMA_TRIM_MAX_SHIFT_SECONDS,
    OLLAMA_VISION_MAX_CLIPS,
    OLLAMA_VISION_ALL_CLIPS,
    OLLAMA_VISION_ENABLED,
    OLLAMA_VISION_GPU_HANDOFF,
    OLLAMA_VISION_ONLY_LOW_TEXT,
    OLLAMA_VISION_REQUIRE_GPU,
    OLLAMA_VISION_TIMEOUT,
    OLLAMA_VISION_TIMEOUT_STREAK_LIMIT,
    OLLAMA_VISION_TITLE_ONLY,
    PAUSE_THRESHOLD_PARAGRAPH,
    PAUSE_THRESHOLD_PHRASE,
    PAUSE_THRESHOLD_SENTENCE,
    POST_ROLL_SECONDS,
    PROFILE_AUTO_CAR_PEAKS_PER_MIN,
    PROFILE_AUTO_TALKING_WPS,
    PROFILE_CAR_MAX_SECONDS,
    PROFILE_CAR_MIN_SECONDS,
    PROFILE_GENERAL_MAX_SECONDS,
    PROFILE_GENERAL_MIN_SECONDS,
    PROFILE_TALKING_MAX_SECONDS,
    PROFILE_TALKING_MIN_SECONDS,
    PRE_ROLL_SECONDS,
    REJECT_COMMERCIAL_CLIPS,
    SMART_TRIM_LONG_CLIPS,
    SMART_TRIM_MIN_REDUCTION_SECONDS,
    SMART_TRIM_SEARCH_WINDOW_SECONDS,
    SMART_TRIM_TARGET_SECONDS,
    SMART_TRIM_TRIGGER_SECONDS,
    SCORE_COMBO_BONUS_CAP,
    OPENSMILE_EVENT_MIN_SCORE,
    FACIAL_EMOTION_EVENT_MIN_SCORE,
    FACIAL_EMOTION_MIN_FACE_AREA_RATIO,
    FACIAL_EMOTION_RESIZE_WIDTH,
    FACIAL_EMOTION_SAMPLE_FPS,
    FACIAL_EMOTION_USE_FER,
    VISUAL_EVENT_COOLDOWN_SECONDS,
    VISUAL_EVENT_MIN_DELTA,
    VISUAL_EVENT_MIN_SCORE,
    VISUAL_EVENT_SMOOTH_SECONDS,
    OBJECT_CAR_CONF_THRESHOLD,
    OBJECT_CAR_MIN_AREA_RATIO,
    OBJECT_CAR_MIN_SCORE,
    OBJECT_CAR_MODEL,
    OBJECT_CAR_RESIZE_WIDTH,
    OBJECT_CAR_SAMPLE_FPS,
    VISUAL_MOTION_RESIZE_WIDTH,
    VISUAL_MOTION_ROI_BOTTOM_RATIO,
    VISUAL_MOTION_SAMPLE_FPS,
    VISUAL_START_EVENT_THRESHOLD,
    VISUAL_STOP_EVENT_THRESHOLD,
)
from worker.worker_diarization import PYANNOTE_AVAILABLE, _get_speaker_diarization
from worker.worker_keywords import (
    DIALOGUE_MARKERS,
    EMOTION_INTENSIFIERS,
    FORBIDDEN_END_WORDS,
    HOOK_MARKERS,
    LAUGHTER_TOKENS,
    PUNCHLINE_MARKERS,
    STORY_END_MARKERS,
    STORY_START_MARKERS,
)
from worker.worker_logging import LOGGER
from worker.worker_models import CutSignal, SignalType
from worker.worker_ollama import (
    _ollama_analyze_clip_advanced,
    _ollama_check_available,
    _ollama_check_vision_available,
    _ollama_vision_analyze_clip,
)
from worker.worker_scene import SCENEDETECT_AVAILABLE, _detect_scene_changes
from worker.worker_scoring import _feature_bundle, _tag_and_reason
from worker.worker_text import (
    _align_to_transcript,
    _analyze_grammar_ending,
    _text_features_for_range,
    _find_story_windows,
    _merge_audio_and_story_candidates,
)
from worker.worker_titles import _build_tiktok_title
from worker.worker_utils import _expand_arc, _find_peak_indices, _find_peak_indices_local, _normalize_series
from worker.worker_gpu import _prepare_cuda_for_ollama_vision
from worker.worker_video_motion import (
    OPENCV_AVAILABLE,
    _compute_visual_car_start_stop_events,
    _compute_visual_motion_series,
)
from worker.worker_object_detection import (
    OBJECT_CAR_DETECTION_AVAILABLE,
    _compute_car_object_presence_series,
)
from worker.worker_face_emotion import (
    FACIAL_EMOTION_AVAILABLE,
    _compute_facial_emotion_series,
    _facial_emotion_backend_name,
)
from worker.worker_config import SENTENCE_END_PATTERNS


SIGNAL_WEIGHTS = {
    SignalType.PAUSE_PARAGRAPH: 1.0,    # Meilleur signal
    SignalType.SCENE_CUT: 0.95,
    SignalType.SPEAKER_CHANGE: 0.93,
    SignalType.PAUSE_LONG: 0.90,
    SignalType.SENTENCE_END: 0.90,
    SignalType.STORY_END: 0.87,
    SignalType.STORY_START: 0.85,
    SignalType.PITCH_FALLING: 0.75,
    SignalType.GRAMMAR_COMPLETE: 0.84,
    SignalType.PAUSE_SHORT: 0.42,
    SignalType.SILENCE_AUDIO: 0.68,
    SignalType.VAD_SILENCE: 0.88,
    SignalType.PITCH_RISING: 0.20,      # Mauvais pour fin
    SignalType.GRAMMAR_INCOMPLETE: 0.05, # Très mauvais
}

_CAR_PROFILE_HINT_TERMS = (
    "voiture",
    "automobile",
    "moteur",
    "accel",
    "acceleration",
    "accél",
    "frein",
    "drift",
    "circuit",
    "piste",
    "turbo",
    "essence",
    "diesel",
    "embrayage",
    "boite",
    "vitesse",
    "volant",
    "rpm",
    "burnout",
    "pilotage",
    "0 a 100",
    "0-100",
)

_CAR_EXTERIOR_HINT_PHRASES = (
    "tour de la voiture",
    "tour autour de la voiture",
    "tour exterieur",
    "exterieur de la voiture",
    "on fait le tour",
    "walkaround",
    "walk around",
    "car walkaround",
    "around the car",
    "outside the car",
    "car exterior",
    "exterior tour",
    "full exterior",
    "presentation exterieure",
    "vue exterieure",
    "vue de l exterieur",
    "on voit l exterieur",
)
_CAR_EXTERIOR_HINT_TOKENS = {
    "exterieur",
    "exterior",
    "outside",
    "autour",
    "walkaround",
}
_CAR_VEHICLE_HINT_TOKENS = {
    "voiture",
    "auto",
    "automobile",
    "vehicule",
    "vehicle",
}
_CAR_SHOWCASE_HINT_TOKENS = {
    "tour",
    "presentation",
    "presente",
    "show",
    "montre",
    "detail",
    "details",
    "vue",
}

_TRANSCRIPT_WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9']+", re.UNICODE)


def _extract_pauses_from_words(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Extrait toutes les pauses entre les mots à partir des word_timestamps.
    Retourne une liste de pauses avec leur position, durée et contexte.
    """
    pauses = []
    prev_word_end = None
    prev_word_text = ""
    
    for seg in segments:
        words = seg.get("words", [])
        if not words:
            # Si pas de mots, utilise les timestamps du segment
            if prev_word_end is not None:
                gap = seg["start"] - prev_word_end
                if gap >= PAUSE_THRESHOLD_PHRASE:
                    pauses.append({
                        "time": prev_word_end,
                        "duration": gap,
                        "before_text": prev_word_text,
                        "after_text": seg["text"][:50] if seg.get("text") else "",
                        "type": _classify_pause(gap),
                    })
            prev_word_end = seg["end"]
            prev_word_text = seg.get("text", "")[-20:] if seg.get("text") else ""
            continue
            
        for word in words:
            word_start = word["start"]
            word_end = word["end"]
            word_text = word.get("word", "").strip()
            
            if prev_word_end is not None:
                gap = word_start - prev_word_end
                if gap >= PAUSE_THRESHOLD_PHRASE:
                    pauses.append({
                        "time": prev_word_end,
                        "duration": gap,
                        "before_text": prev_word_text,
                        "after_text": word_text,
                        "type": _classify_pause(gap),
                    })
            
            prev_word_end = word_end
            prev_word_text = word_text
    
    return pauses

def _classify_pause(duration: float) -> str:
    """Classifie une pause selon sa durée."""
    if duration >= PAUSE_THRESHOLD_PARAGRAPH:
        return "paragraph"  # Excellent point de coupe
    elif duration >= PAUSE_THRESHOLD_SENTENCE:
        return "sentence"   # Bon point de coupe
    else:
        return "phrase"     # Point de coupe acceptable


def _sustained_run_seconds(values: list[float], index: int, threshold: float) -> float:
    """
    Returns duration (seconds) of the contiguous run around `index`
    where values stay above `threshold`.
    """
    if not values or not (0 <= index < len(values)):
        return 0.0
    left = index
    right = index
    while left > 0 and values[left - 1] >= threshold:
        left -= 1
    while right < len(values) - 1 and values[right + 1] >= threshold:
        right += 1
    return (right - left + 1) * ANALYSIS_WINDOW_SECONDS


def _estimate_words_per_second(
    transcript_segments: list[dict[str, Any]],
    duration: float,
) -> float:
    if not transcript_segments or duration <= 0:
        return 0.0
    word_count = 0
    for seg in transcript_segments:
        text = str(seg.get("text", "")).strip()
        if not text:
            continue
        word_count += len(text.split())
    return word_count / max(duration, 0.1)


def _transcript_density_stats(
    transcript_segments: list[dict[str, Any]],
    duration: float,
) -> dict[str, float]:
    text_segments = 0
    total_words = 0
    total_chars = 0
    total_speech_seconds = 0.0
    unique_tokens: set[str] = set()
    for seg in transcript_segments:
        text = str(seg.get("text", "")).strip()
        if not text:
            continue
        text_segments += 1
        tokens = _TRANSCRIPT_WORD_RE.findall(text.lower())
        total_words += len(tokens)
        unique_tokens.update(tokens)
        total_chars += len(text)
        start = float(seg.get("start", 0.0) or 0.0)
        end = float(seg.get("end", start) or start)
        if end > start:
            total_speech_seconds += end - start
    words_per_sec = total_words / max(duration, 0.1)
    avg_words_per_segment = total_words / max(1.0, float(text_segments))
    speech_coverage = total_speech_seconds / max(duration, 0.1)
    return {
        "segments": float(text_segments),
        "words": float(total_words),
        "chars": float(total_chars),
        "wps": float(words_per_sec),
        "unique_words": float(len(unique_tokens)),
        "spoken_seconds": float(total_speech_seconds),
        "speech_coverage": float(speech_coverage),
        "avg_words_per_segment": float(avg_words_per_segment),
    }


def _transcript_ok_for_ollama_text(
    transcript_segments: list[dict[str, Any]],
    duration: float,
) -> tuple[bool, dict[str, float]]:
    stats = _transcript_density_stats(transcript_segments, duration)
    seg_count = int(stats["segments"])
    word_count = int(stats["words"])
    unique_words = int(stats["unique_words"])
    spoken_seconds = float(stats["spoken_seconds"])
    speech_coverage = float(stats["speech_coverage"])
    avg_words_per_segment = float(stats["avg_words_per_segment"])
    wps = float(stats["wps"])
    if seg_count <= 0 or word_count <= 0:
        return False, stats

    # Strict multi-criteria gating to avoid noisy/sparse transcripts.
    if seg_count < OLLAMA_TEXT_MIN_SEGMENTS:
        return False, stats
    if word_count < OLLAMA_TEXT_MIN_WORDS:
        return False, stats
    if unique_words < OLLAMA_TEXT_MIN_UNIQUE_WORDS:
        return False, stats
    if spoken_seconds < OLLAMA_TEXT_MIN_SPOKEN_SECONDS:
        return False, stats
    if speech_coverage < OLLAMA_TEXT_MIN_COVERAGE_RATIO:
        return False, stats
    if avg_words_per_segment < OLLAMA_TEXT_MIN_AVG_WORDS_PER_SEGMENT:
        return False, stats
    if wps < OLLAMA_TEXT_MIN_WPS:
        return False, stats
    return True, stats


def _estimate_car_text_hints(
    transcript_segments: list[dict[str, Any]],
) -> tuple[int, float]:
    if not transcript_segments:
        return 0, 0.0
    combined_text = " ".join(
        str(seg.get("text", "")).strip().lower()
        for seg in transcript_segments
        if str(seg.get("text", "")).strip()
    )
    if not combined_text:
        return 0, 0.0
    hit_count = 0
    for term in _CAR_PROFILE_HINT_TERMS:
        if term in combined_text:
            hit_count += 1
    total_words = max(1, len(combined_text.split()))
    # Scaled density: avoid overfitting on long transcripts.
    density = hit_count / max(1.0, total_words / 120.0)
    score = min(1.0, (hit_count / 4.0) + (density * 0.35))
    return hit_count, round(score, 3)


def _normalize_text_for_hint_matching(text: str) -> str:
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", str(text))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip().lower()


def _has_car_exterior_tour_text_hint(text: str) -> bool:
    normalized = _normalize_text_for_hint_matching(text)
    if not normalized:
        return False

    if any(phrase in normalized for phrase in _CAR_EXTERIOR_HINT_PHRASES):
        return True

    tokens = set(_TRANSCRIPT_WORD_RE.findall(normalized))
    if not tokens:
        return False

    exterior_hit = any(token in tokens for token in _CAR_EXTERIOR_HINT_TOKENS)
    if not exterior_hit:
        return False

    vehicle_hit = any(token in tokens for token in _CAR_VEHICLE_HINT_TOKENS)
    showcase_hit = any(token in tokens for token in _CAR_SHOWCASE_HINT_TOKENS)
    return bool(vehicle_hit or showcase_hit)


def _build_car_exterior_story_candidates(
    transcript_segments: list[dict[str, Any]],
    *,
    duration: float,
    min_clip_length: float,
    max_clip_length: float,
) -> list[dict[str, Any]]:
    if not transcript_segments or duration <= 0:
        return []

    target_len = max(min_clip_length, min(36.0, max_clip_length * 0.66))
    raw_candidates: list[dict[str, Any]] = []
    for seg in transcript_segments:
        seg_text = str(seg.get("text", "")).strip()
        if not seg_text or not _has_car_exterior_tour_text_hint(seg_text):
            continue

        seg_start = max(0.0, float(seg.get("start", 0.0) or 0.0))
        seg_end = max(seg_start, float(seg.get("end", seg_start) or seg_start))
        center = (seg_start + seg_end) * 0.5

        start = max(0.0, min(center - target_len * 0.40, max(0.0, duration - target_len)))
        end = min(duration, start + target_len)
        if (end - start) < min_clip_length:
            end = min(duration, start + min_clip_length)
            start = max(0.0, end - min_clip_length)
        if end <= start:
            continue

        normalized = _normalize_text_for_hint_matching(seg_text)
        strong_phrase = any(phrase in normalized for phrase in _CAR_EXTERIOR_HINT_PHRASES)
        score = 0.63 + (0.06 if strong_phrase else 0.0)

        raw_candidates.append(
            {
                "start": start,
                "end": end,
                "score": min(0.78, score),
                "reason": "tour exterieur voiture (texte)",
                "text": seg_text,
            }
        )

    if not raw_candidates:
        return []

    raw_candidates.sort(key=lambda candidate: (candidate["score"], -candidate["start"]), reverse=True)
    dedupe_gap = max(10.0, min_clip_length * 0.45)
    selected: list[dict[str, Any]] = []
    for candidate in raw_candidates:
        center = (float(candidate["start"]) + float(candidate["end"])) * 0.5
        if all(
            abs(center - ((float(existing["start"]) + float(existing["end"])) * 0.5)) >= dedupe_gap
            for existing in selected
        ):
            selected.append(candidate)
        if len(selected) >= 3:
            break

    return selected


def _resolve_profile_settings(
    duration: float,
    transcript_segments: list[dict[str, Any]],
    car_peaks_count: int,
    car_object_peaks_count: int = 0,
) -> tuple[str, float, float, dict[str, float | str]]:
    """
    Auto-selects clip profile and duration targets.
    Profiles:
    - car: acceleration and low-dialogue driving videos
    - talking: dialogue-heavy content
    - general: fallback
    """
    profile_mode = CLIP_PROFILE if CLIP_PROFILE in {"auto", "car", "talking", "general"} else "auto"
    has_transcript = bool(transcript_segments)
    words_per_sec = _estimate_words_per_second(transcript_segments, duration)
    car_peaks_per_min = (car_peaks_count / max(duration, 1.0)) * 60.0
    car_object_peaks_per_min = (car_object_peaks_count / max(duration, 1.0)) * 60.0
    combined_car_peaks_per_min = (
        car_peaks_per_min
        + (car_object_peaks_per_min * 0.85)
    )
    car_text_hits, car_text_score = _estimate_car_text_hints(transcript_segments)
    speech_sparse = words_per_sec < max(0.55, PROFILE_AUTO_TALKING_WPS * 0.45)
    ultra_sparse_speech = words_per_sec <= 0.22
    strong_car_audio = combined_car_peaks_per_min >= PROFILE_AUTO_CAR_PEAKS_PER_MIN
    extreme_car_audio = combined_car_peaks_per_min >= max(
        PROFILE_AUTO_CAR_PEAKS_PER_MIN * 2.20,
        PROFILE_AUTO_CAR_PEAKS_PER_MIN + 10.0,
    )
    strong_car_visual = car_object_peaks_per_min >= max(
        5.0,
        PROFILE_AUTO_CAR_PEAKS_PER_MIN * 0.55,
    )
    likely_car_from_text = car_text_hits >= 2 or car_text_score >= 0.55

    if profile_mode != "auto":
        profile = profile_mode
        reason = "forced_profile"
    elif (
        strong_car_audio
        and words_per_sec < PROFILE_AUTO_TALKING_WPS
        and likely_car_from_text
    ):
        profile = "car"
        reason = "auto_car_audio_text"
    elif (not has_transcript or ultra_sparse_speech) and extreme_car_audio:
        # Fallback for near-silent onboard/driving videos with no useful transcript.
        profile = "car"
        reason = "auto_car_audio_extreme_sparse"
    elif (not has_transcript or speech_sparse) and strong_car_visual:
        profile = "car"
        reason = "auto_car_visual_sparse"
    elif strong_car_visual and words_per_sec < PROFILE_AUTO_TALKING_WPS * 0.85:
        profile = "car"
        reason = "auto_car_visual"
    elif words_per_sec >= PROFILE_AUTO_TALKING_WPS:
        profile = "talking"
        reason = "auto_dialogue_density"
    else:
        profile = "general"
        reason = "auto_default"

    if profile == "car":
        min_len = PROFILE_CAR_MIN_SECONDS
        max_len = PROFILE_CAR_MAX_SECONDS
    elif profile == "talking":
        min_len = PROFILE_TALKING_MIN_SECONDS
        max_len = PROFILE_TALKING_MAX_SECONDS
    else:
        min_len = PROFILE_GENERAL_MIN_SECONDS
        max_len = PROFILE_GENERAL_MAX_SECONDS

    global_min_len = max(15.0, float(CLIP_MIN_SECONDS))
    global_max_len = max(global_min_len + 5.0, float(CLIP_MAX_SECONDS))

    min_len = max(global_min_len, float(min_len))
    max_len = min(float(max_len), global_max_len)
    max_len = max(min_len + 5.0, max_len)
    max_len = min(max_len, max(15.0, duration))
    min_len = min(min_len, max_len)

    metadata: dict[str, float | str] = {
        "reason": reason,
        "words_per_sec": round(words_per_sec, 3),
        "car_peaks_per_min": round(combined_car_peaks_per_min, 2),
        "car_audio_peaks_per_min": round(car_peaks_per_min, 2),
        "car_object_peaks_per_min": round(car_object_peaks_per_min, 2),
        "car_object_peaks_count": float(car_object_peaks_count),
        "car_text_hits": float(car_text_hits),
        "car_text_score": round(car_text_score, 3),
        "speech_sparse": 1.0 if speech_sparse else 0.0,
        "ultra_sparse_speech": 1.0 if ultra_sparse_speech else 0.0,
        "has_transcript": 1.0 if has_transcript else 0.0,
        "mode": profile_mode,
    }
    return profile, min_len, max_len, metadata

def _is_car_showcase_event(
    *,
    car_profile_active: bool,
    visual_motion_score: float,
    visual_motion_event: bool,
    speech_context_ratio: float,
    speech_context_event: bool,
    opensmile_voice_event: bool,
    speaker_change_event: bool,
    strong_car_signal: bool,
    car_start_event: bool,
    car_stop_event: bool,
    car_accel_score: float,
    car_object_score: float = 0.0,
    exterior_tour_text_hint: bool = False,
) -> bool:
    """
    Detects "car showcase / walkaround" moments:
    visual motion + narration, but without strong acceleration/start/stop events.
    """
    if not car_profile_active:
        return False
    if strong_car_signal:
        return False

    transition_event = car_start_event or car_stop_event
    if transition_event and not exterior_tour_text_hint:
        return False

    accel_threshold = max(0.55, CAR_ACCEL_THRESHOLD * 0.88)
    if exterior_tour_text_hint:
        accel_threshold = max(accel_threshold, max(0.64, CAR_ACCEL_THRESHOLD * 0.98))
    if car_accel_score >= accel_threshold:
        return False

    if transition_event and car_accel_score >= max(0.60, CAR_ACCEL_THRESHOLD * 0.94):
        return False

    car_object_event = car_object_score >= OBJECT_CAR_MIN_SCORE
    driving_like_motion = visual_motion_score >= max(0.66, VISUAL_EVENT_MIN_SCORE * 1.35)
    if driving_like_motion and not exterior_tour_text_hint and not transition_event:
        # Avoid classifying sustained highway rolling as "presentation".
        return False

    visual_threshold = max(0.34, VISUAL_EVENT_MIN_SCORE * 0.82)
    if exterior_tour_text_hint:
        visual_threshold = max(0.22, VISUAL_EVENT_MIN_SCORE * 0.56)
    elif speech_context_ratio >= max(0.38, AUDIO_CONTEXT_SPEECH_MIN_RATIO * 0.78):
        visual_threshold = max(0.28, VISUAL_EVENT_MIN_SCORE * 0.68)
    elif (
        speech_context_ratio <= AUDIO_CONTEXT_SPEECH_MIN_RATIO * 0.60
        and not opensmile_voice_event
        and not speaker_change_event
    ):
        # Visual-only walkaround fallback for near-silent car videos.
        visual_threshold = max(0.26, VISUAL_EVENT_MIN_SCORE * 0.60)

    visual_ok = (
        visual_motion_event
        or visual_motion_score >= visual_threshold
        or car_object_event
    )
    narration_ok = (
        speech_context_event
        or speech_context_ratio >= max(0.40, AUDIO_CONTEXT_SPEECH_MIN_RATIO * 0.82)
        or opensmile_voice_event
        or speaker_change_event
    )
    low_dialogue_visual_ok = (
        speech_context_ratio <= AUDIO_CONTEXT_SPEECH_MIN_RATIO * 0.70
        and not opensmile_voice_event
        and not speaker_change_event
        and visual_motion_score <= max(0.60, VISUAL_EVENT_MIN_SCORE * 1.22)
    )
    stationary_visual_ok = (
        visual_motion_score <= max(0.34, VISUAL_EVENT_MIN_SCORE * 0.78)
    )
    stationary_object_showcase = bool(
        car_object_event
        and low_dialogue_visual_ok
        and stationary_visual_ok
        and car_accel_score <= max(0.36, CAR_ACCEL_THRESHOLD * 0.56)
    )
    if exterior_tour_text_hint and visual_ok:
        return True
    if stationary_object_showcase:
        return True
    return visual_ok and (narration_ok or low_dialogue_visual_ok)

def _pick_soft_trim_end_from_transcript(
    start: float,
    current_end: float,
    target_end: float,
    transcript_segments: list[dict[str, Any]],
    min_clip_length: float,
    search_window: float,
) -> float | None:
    """
    Picks a natural transcript end near `target_end` for long-clip soft trimming.
    """
    if not transcript_segments:
        return None

    window = max(2.0, float(search_window))
    min_end = start + min_clip_length
    window_start = max(min_end, target_end - window)
    window_end = min(current_end - 0.4, target_end + window)
    if window_end <= window_start:
        return None

    scored: list[tuple[float, float, float]] = []
    for seg in transcript_segments:
        seg_end = float(seg.get("end", 0.0))
        if seg_end < window_start or seg_end > window_end:
            continue
        seg_text = str(seg.get("text", "")).strip().lower()
        if not seg_text:
            continue

        score = 0.0
        if SENTENCE_END_PATTERNS.search(seg_text):
            score += 1.0
        if any(marker in seg_text for marker in STORY_END_MARKERS):
            score += 0.55

        words = seg_text.split()
        if words:
            last_word = words[-1].rstrip(".,!?;:")
            if last_word in FORBIDDEN_END_WORDS:
                score -= 0.90

        distance = abs(seg_end - target_end)
        proximity = max(0.0, 0.35 - (distance / max(1.0, window)) * 0.35)
        score += proximity
        scored.append((score, -distance, seg_end))

    if not scored:
        return None

    scored.sort(reverse=True)
    best_score, _, best_end = scored[0]
    if best_score < 0.35:
        return None
    return best_end


def _apply_ollama_trim_hint(
    action: str,
    start: float,
    end: float,
    transcript_segments: list[dict[str, Any]],
    min_clip_length: float,
    max_shift_seconds: float,
) -> tuple[float, float, bool, str]:
    """
    Applies local trim hint suggested by Ollama and snaps to transcript boundaries.
    Returns (new_start, new_end, applied, adjustment_label).
    """
    if action not in {"trim_start", "trim_end"} or not transcript_segments:
        return start, end, False, ""

    safe_shift = max(0.5, float(max_shift_seconds))
    min_len = max(1.0, float(min_clip_length))
    new_start = float(start)
    new_end = float(end)

    if action == "trim_end":
        window_start = max(new_start + min_len, new_end - safe_shift)
        candidates: list[tuple[float, float, float]] = []
        for seg in transcript_segments:
            seg_end = float(seg.get("end", 0.0))
            if seg_end < window_start or seg_end >= new_end:
                continue
            seg_text = str(seg.get("text", "")).strip().lower()
            if not seg_text:
                continue
            score = 0.0
            if SENTENCE_END_PATTERNS.search(seg_text):
                score += 1.0
            if any(marker in seg_text for marker in STORY_END_MARKERS):
                score += 0.55
            words = seg_text.split()
            if words and words[-1].rstrip(".,!?;:") in FORBIDDEN_END_WORDS:
                score -= 0.8
            distance = new_end - seg_end
            score += max(0.0, 0.25 - (distance / max(1.0, safe_shift)) * 0.25)
            candidates.append((score, -distance, seg_end))
        if not candidates:
            return start, end, False, ""
        candidates.sort(reverse=True)
        best_end = candidates[0][2]
        if (new_end - best_end) < 0.6 or best_end <= new_start + min_len:
            return start, end, False, ""
        return new_start, best_end, True, "ollama_trim_end"

    # trim_start
    window_end = min(new_end - min_len, new_start + safe_shift)
    candidates: list[tuple[float, float, float]] = []
    for seg in transcript_segments:
        seg_start = float(seg.get("start", 0.0))
        if seg_start <= new_start or seg_start > window_end:
            continue
        distance = seg_start - new_start
        # Prefer a small but meaningful trim near the current start.
        score = max(0.0, 0.30 - (distance / max(1.0, safe_shift)) * 0.30)
        candidates.append((score, -distance, seg_start))
    if not candidates:
        return start, end, False, ""
    candidates.sort(reverse=True)
    best_start = candidates[0][2]
    if (best_start - new_start) < 0.6 or new_end <= best_start + min_len:
        return start, end, False, ""
    return best_start, new_end, True, "ollama_trim_start"


# ============================================================================
# SINGLE-PASS BOUNDARY DETECTION - Collecte et décision unifiées
# ============================================================================

def _collect_all_cut_signals(
    transcript_segments: list[dict[str, Any]],
    diarization: list[dict[str, Any]],
    scenes: list[tuple[float, float]],
    audio_rms_series: list[tuple[float, float]] | None = None,
    audio_vad_series: list[tuple[float, float]] | None = None,
    ffmpeg_silence_segments: list[tuple[float, float]] | None = None,
    audio_path: Path | None = None,
    duration: float = 0.0,
) -> list[CutSignal]:
    """
    Collecte TOUS les signaux de points de coupe potentiels en une seule passe.
    
    Cette fonction centralise la détection de tous les types de signaux :
    - Pauses naturelles (word timestamps)
    - Fins de phrases (ponctuation, marqueurs)
    - Changements de speaker (diarization)
    - Changements de scène (scene detection)
    - Silences audio (RMS)
    - Débuts/fins d'histoires (marqueurs narratifs)
    
    Retourne une liste de CutSignal triée par timestamp.
    """
    signals: list[CutSignal] = []
    
    # === 1. PAUSES NATURELLES (word timestamps) ===
    if transcript_segments:
        pauses = _extract_pauses_from_words(transcript_segments)
        for pause in pauses:
            pause_time = pause["time"]
            pause_duration = pause["duration"]
            pause_type = pause["type"]
            
            # Détermine le type de signal selon la durée
            if pause_type == "paragraph":
                sig_type = SignalType.PAUSE_PARAGRAPH
                base_score = 1.0
            elif pause_type == "sentence":
                sig_type = SignalType.PAUSE_LONG
                base_score = 0.85
            else:
                sig_type = SignalType.PAUSE_SHORT
                base_score = 0.50
            
            # Bonus si le texte avant se termine par ponctuation
            before_text = pause.get("before_text", "")
            if before_text and before_text.strip()[-1:] in ".!?":
                base_score = min(1.0, base_score + 0.15)
            
            # La pause est bonne pour fin (on coupe SUR la pause)
            # et bonne pour début (on coupe APRÈS la pause)
            signals.append(CutSignal(
                time=pause_time,
                signal_type=sig_type,
                score=base_score,
                is_good_for_start=False,  # Pour start, on veut APRÈS la pause
                is_good_for_end=True,
                source="pause"
            ))
            
            # Point de début = juste après la pause
            signals.append(CutSignal(
                time=pause_time + pause_duration,
                signal_type=sig_type,
                score=base_score * 0.95,  # Légèrement moins bon
                is_good_for_start=True,
                is_good_for_end=False,
                source="pause_after"
            ))
    
    # === 2. FINS DE PHRASES (ponctuation et marqueurs) ===
    if transcript_segments:
        for seg in transcript_segments:
            text = seg.get("text", "").strip()
            seg_end = seg["end"]
            seg_start = seg["start"]
            
            if not text:
                continue
            
            lower = text.lower()
            
            # Fin de phrase avec ponctuation forte
            if SENTENCE_END_PATTERNS.search(text):
                signals.append(CutSignal(
                    time=seg_end,
                    signal_type=SignalType.SENTENCE_END,
                    score=0.80,
                    is_good_for_start=False,
                    is_good_for_end=True,
                    source="punctuation"
                ))
            
            # Marqueurs de fin d'histoire
            if any(marker in lower for marker in STORY_END_MARKERS):
                signals.append(CutSignal(
                    time=seg_end,
                    signal_type=SignalType.STORY_END,
                    score=0.85,
                    is_good_for_start=False,
                    is_good_for_end=True,
                    source="story_end_marker"
                ))
            
            # Marqueurs de début d'histoire
            if any(marker in lower for marker in STORY_START_MARKERS):
                signals.append(CutSignal(
                    time=seg_start,
                    signal_type=SignalType.STORY_START,
                    score=0.85,
                    is_good_for_start=True,
                    is_good_for_end=False,
                    source="story_start_marker"
                ))

            # Analyse grammaticale de fin de segment (plus robuste qu'un simple mot interdit).
            grammar = _analyze_grammar_ending(text)
            grammar_score = float(grammar.get("grammar_score", 0.5))

            if grammar.get("is_complete"):
                complete_score = max(0.35, min(0.9, grammar_score))
                signals.append(CutSignal(
                    time=seg_end,
                    signal_type=SignalType.GRAMMAR_COMPLETE,
                    score=complete_score,
                    is_good_for_start=False,
                    is_good_for_end=True,
                    source="grammar_complete"
                ))
            else:
                incomplete_score = 0.05 if grammar.get("forbidden_end") else max(0.08, min(0.25, grammar_score))
                reason = "forbidden_end_word" if grammar.get("forbidden_end") else "grammar_incomplete"
                signals.append(CutSignal(
                    time=seg_end,
                    signal_type=SignalType.GRAMMAR_INCOMPLETE,
                    score=incomplete_score,
                    is_good_for_start=False,
                    is_good_for_end=False,  # NE PAS couper ici !
                    source=reason
                ))
    
    # === 3. CHANGEMENTS DE SPEAKER (diarization) ===
    if diarization:
        prev_speaker = None
        for seg in diarization:
            current_speaker = seg.get("speaker")
            
            if prev_speaker is not None and current_speaker != prev_speaker:
                # Changement de speaker = bon point de coupe
                change_time = seg["start"]
                signals.append(CutSignal(
                    time=change_time,
                    signal_type=SignalType.SPEAKER_CHANGE,
                    score=0.90,
                    is_good_for_start=True,
                    is_good_for_end=True,
                    source="speaker_diarization"
                ))
            
            prev_speaker = current_speaker
    
    # === 4. CHANGEMENTS DE SCÈNE (scene detection) ===
    if scenes:
        for scene_start, scene_end in scenes:
            # Début de scène = bon pour début de clip
            signals.append(CutSignal(
                time=scene_start,
                signal_type=SignalType.SCENE_CUT,
                score=0.95,
                is_good_for_start=True,
                is_good_for_end=False,
                source="scene_start"
            ))
            # Fin de scène = bon pour fin de clip
            signals.append(CutSignal(
                time=scene_end,
                signal_type=SignalType.SCENE_CUT,
                score=0.95,
                is_good_for_start=False,
                is_good_for_end=True,
                source="scene_end"
            ))
    
    # === 5. SILENCES AUDIO (RMS bas) ===
    if audio_rms_series:
        values = [v for _, v in audio_rms_series]
        if values:
            avg_rms = sum(values) / len(values)
            silence_threshold = max(0.05, avg_rms * 0.4)
            
            # Détecte les zones de silence
            in_silence = False
            silence_start = 0.0
            
            for timestamp, rms in audio_rms_series:
                if rms <= silence_threshold:
                    if not in_silence:
                        silence_start = timestamp
                        in_silence = True
                else:
                    if in_silence:
                        # Fin du silence
                        silence_duration = timestamp - silence_start
                        if silence_duration >= 0.3:  # Silence significatif
                            # Point de coupe au milieu du silence
                            mid_silence = silence_start + silence_duration / 2
                            score = min(0.80, 0.50 + silence_duration * 0.15)
                            signals.append(CutSignal(
                                time=mid_silence,
                                signal_type=SignalType.SILENCE_AUDIO,
                                score=score,
                                is_good_for_start=True,
                                is_good_for_end=True,
                                source="audio_silence"
                            ))
                        in_silence = False

    # === 6. SILENCES FFMPEG (silencedetect) ===
    if ffmpeg_silence_segments:
        for silence_start, silence_end in ffmpeg_silence_segments:
            silence_duration = max(0.0, silence_end - silence_start)
            if silence_duration < 0.18:
                continue
            mid_silence = silence_start + silence_duration / 2
            score = min(0.95, 0.68 + silence_duration * 0.22)
            signals.append(CutSignal(
                time=mid_silence,
                signal_type=SignalType.SILENCE_AUDIO,
                score=score,
                is_good_for_start=True,
                is_good_for_end=True,
                source="ffmpeg_silencedetect"
            ))

    # === 7. SILENCES VOIX (VAD) ===
    if audio_vad_series:
        values = [v for _, v in audio_vad_series]
        if values:
            silence_threshold = 0.35  # ratio de voix en dessous = silence probable
            in_silence = False
            silence_start = 0.0

            for timestamp, speech_ratio in audio_vad_series:
                if speech_ratio <= silence_threshold:
                    if not in_silence:
                        silence_start = timestamp
                        in_silence = True
                else:
                    if in_silence:
                        silence_duration = timestamp - silence_start
                        if silence_duration >= 0.3:
                            mid_silence = silence_start + silence_duration / 2
                            score = min(0.90, 0.60 + silence_duration * 0.2)
                            signals.append(CutSignal(
                                time=mid_silence,
                                signal_type=SignalType.VAD_SILENCE,
                                score=score,
                                is_good_for_start=True,
                                is_good_for_end=True,
                                source="vad_silence"
                            ))
                        in_silence = False
            if in_silence:
                silence_duration = audio_vad_series[-1][0] - silence_start
                if silence_duration >= 0.3:
                    mid_silence = silence_start + silence_duration / 2
                    score = min(0.90, 0.60 + silence_duration * 0.2)
                    signals.append(CutSignal(
                        time=mid_silence,
                        signal_type=SignalType.VAD_SILENCE,
                        score=score,
                        is_good_for_start=True,
                        is_good_for_end=True,
                        source="vad_silence"
                    ))
    
    # === 8. ANALYSE PROSODIE (si disponible) ===
    # Note: L'analyse pitch est coûteuse, on la fait seulement sur demande
    # dans _refine_boundaries_single_pass si nécessaire
    
    # Trie les signaux par timestamp
    signals.sort(key=lambda s: s.time)
    
    LOGGER.debug("Collected %d cut signals", len(signals))
    return signals

def _find_best_cut_point(
    signals: list[CutSignal],
    target_time: float,
    search_window: tuple[float, float],
    for_start: bool = True,
) -> tuple[float, float, list[str]]:
    """
    Trouve le meilleur point de coupe dans une fenêtre de recherche.
    
    Args:
        signals: Liste de tous les signaux collectés
        target_time: Timestamp cible initial
        search_window: (min_time, max_time) - fenêtre de recherche
        for_start: True si on cherche un début de clip, False pour une fin
    
    Returns:
        (best_time, best_score, reasons) - Le meilleur point trouvé avec ses raisons
    """
    min_time, max_time = search_window
    
    # Filtre les signaux dans la fenêtre et du bon type (start ou end)
    candidates: list[tuple[float, float, CutSignal]] = []
    
    for signal in signals:
        if not (min_time <= signal.time <= max_time):
            continue
        
        # Vérifie que le signal est approprié pour ce qu'on cherche
        if for_start and not signal.is_good_for_start:
            continue
        if not for_start and not signal.is_good_for_end:
            continue
        
        # Score de base du signal
        base_score = signal.score * SIGNAL_WEIGHTS.get(signal.signal_type, 0.5)

        # Priorise natural ending boundaries for precise cuts.
        if not for_start:
            if signal.signal_type in {
                SignalType.PAUSE_PARAGRAPH,
                SignalType.PAUSE_LONG,
                SignalType.SENTENCE_END,
                SignalType.STORY_END,
                SignalType.GRAMMAR_COMPLETE,
                SignalType.VAD_SILENCE,
            }:
                base_score += 0.08
            if signal.signal_type in {SignalType.PAUSE_SHORT, SignalType.GRAMMAR_INCOMPLETE}:
                base_score -= 0.12
            if signal.source == "ffmpeg_silencedetect":
                base_score += 0.06

        base_score = max(0.0, min(1.0, base_score))
        
        # Bonus de proximité au target (préfère les points proches)
        distance = abs(signal.time - target_time)
        window_size = max_time - min_time
        proximity_bonus = 0.1 * (1 - distance / window_size) if window_size > 0 else 0

        final_score = min(1.0, max(0.0, base_score + proximity_bonus))
        candidates.append((signal.time, final_score, signal))
    
    if not candidates:
        # Aucun signal trouvé, retourne le target original
        return target_time, 0.0, ["no_signal_found"]
    
    # Agrège les scores pour les points très proches (< 0.3s)
    # Plusieurs signaux au même endroit = meilleur point
    aggregated: dict[float, tuple[float, list[str]]] = {}
    
    for time, score, signal in candidates:
        # Arrondi à 0.3s pour grouper les signaux proches
        rounded_time = round(time / 0.3) * 0.3
        
        if rounded_time not in aggregated:
            aggregated[rounded_time] = (0.0, [])
        
        current_score, reasons = aggregated[rounded_time]
        # Combine les scores (moyenne pondérée favorisant le max)
        new_score = max(current_score, score) + min(current_score, score) * 0.3
        reasons.append(f"{signal.signal_type.value}({signal.source})")
        aggregated[rounded_time] = (min(1.0, new_score), reasons)
    
    # Trouve le meilleur point agrégé
    best_time = target_time
    best_score = 0.0
    best_reasons: list[str] = []
    
    for time, (score, reasons) in aggregated.items():
        if score > best_score:
            best_score = score
            best_time = time
            best_reasons = reasons
    
    return best_time, best_score, best_reasons

def _refine_boundaries_single_pass(
    start: float,
    end: float,
    signals: list[CutSignal],
    duration: float,
    audio_path: Path | None = None,
    pitch_series: list[tuple[float, float]] | None = None,
    transcript_segments: list[dict[str, Any]] | None = None,
    min_clip_length: float = MIN_CLIP_LENGTH,
    max_clip_length: float = MAX_CLIP_LENGTH,
) -> tuple[float, float, dict[str, Any]]:
    """
    Ajuste les boundaries en UNE SEULE PASSE en utilisant tous les signaux.
    
    C'est LA fonction principale qui remplace les multi-passes :
    - _expand_arc (supprimé des boundaries)
    - _align_to_transcript (intégré)
    - _smart_align_boundaries (intégré)
    - Ajustements Ollama (intégrés si pertinent)
    
    Args:
        start: Timestamp de début initial
        end: Timestamp de fin initial
        signals: Liste de tous les signaux pré-collectés
        duration: Durée totale de la vidéo
        audio_path: Chemin vers l'audio (pour analyse pitch si besoin)
        pitch_series: Série de pitch pré-calculée (cache)
        transcript_segments: Segments de transcription (pour validation)
    
    Returns:
        (new_start, new_end, metadata) avec metadata contenant les raisons des choix
    """
    metadata = {
        "original_start": start,
        "original_end": end,
        "start_reasons": [],
        "end_reasons": [],
        "start_score": 0.0,
        "end_score": 0.0,
        "adjustments": [],
    }
    snap_threshold = max(0.1, min(0.95, BOUNDARY_LOW_SCORE_THRESHOLD))
    max_shift = max(0.3, float(BOUNDARY_SNAP_MAX_SHIFT_SECONDS))
    
    # === RECHERCHE DU MEILLEUR DÉBUT ===
    # Fenêtre: jusqu'à 5s avant, jusqu'à 3s après
    start_window = (max(0, start - 5.0), min(duration, start + 3.0))
    new_start, start_score, start_reasons = _find_best_cut_point(
        signals, start, start_window, for_start=True
    )
    
    metadata["start_score"] = round(start_score, 3)
    metadata["start_reasons"] = start_reasons[:3]  # Top 3 raisons
    
    # === RECHERCHE DE LA MEILLEURE FIN ===
    # Fenêtre: jusqu'à 3s avant, jusqu'à 5s après
    end_window = (max(0, end - 3.0), min(duration, end + 5.0))
    new_end, end_score, end_reasons = _find_best_cut_point(
        signals, end, end_window, for_start=False
    )
    
    metadata["end_score"] = round(end_score, 3)
    metadata["end_reasons"] = end_reasons[:3]

    # Secondary strict pass: prefer natural sentence endings when confidence is low.
    if end_score < 0.62:
        strict_window = (max(0.0, new_end - 2.0), min(duration, new_end + 2.0))
        strict_candidates: list[tuple[float, float, str]] = []
        for signal in signals:
            if not signal.is_good_for_end:
                continue
            if not (strict_window[0] <= signal.time <= strict_window[1]):
                continue
            if signal.signal_type not in {
                SignalType.PAUSE_PARAGRAPH,
                SignalType.PAUSE_LONG,
                SignalType.SENTENCE_END,
                SignalType.STORY_END,
                SignalType.GRAMMAR_COMPLETE,
                SignalType.VAD_SILENCE,
            }:
                continue
            distance = abs(signal.time - new_end)
            strict_score = signal.score + max(0.0, 0.18 - distance * 0.06)
            strict_candidates.append((strict_score, signal.time, signal.source))
        if strict_candidates:
            strict_candidates.sort(reverse=True)
            strict_score, strict_end, strict_source = strict_candidates[0]
            if strict_score >= max(0.55, end_score + 0.08):
                new_end = strict_end
                end_score = min(1.0, strict_score)
                metadata["end_score"] = round(end_score, 3)
                metadata["end_reasons"] = [f"strict_end:{strict_source}"]
                metadata["adjustments"].append("strict_natural_end_pass")
    
    # === VALIDATION PROSODIE (optionnel, si score fin < 0.7) ===
    if end_score < 0.7 and audio_path and LIBROSA_AVAILABLE:
        # Analyse le pitch pour voir si c'est vraiment une bonne fin
        if pitch_series:
            pitch_analysis = _analyze_pitch_trend_from_series(
                pitch_series, max(0, new_end - 2.0), new_end
            )
        else:
            pitch_analysis = _analyze_pitch_contour(
                audio_path, max(0, new_end - 2.0), new_end
            )
        
        if pitch_analysis.get("end_pitch_trend") == "rising":
            # Intonation montante = probablement pas fini, cherche plus loin
            extended_window = (new_end, min(duration, new_end + 5.0))
            alt_end, alt_score, alt_reasons = _find_best_cut_point(
                signals, new_end + 2.0, extended_window, for_start=False
            )
            
            if alt_score > end_score * 0.8:  # Si on trouve mieux
                new_end = alt_end
                metadata["end_score"] = round(alt_score, 3)
                metadata["end_reasons"] = alt_reasons[:3]
                metadata["adjustments"].append("extended_end_due_to_rising_pitch")
        
        elif pitch_analysis.get("end_pitch_trend") == "falling":
            # Intonation descendante = bonne fin, bonus au score
            metadata["end_score"] = min(1.0, end_score + 0.1)
            metadata["adjustments"].append("pitch_falling_confirmed")
    
    # === VALIDATION GRAMMAIRE (vérifie qu'on ne coupe pas sur mot interdit) ===
    if transcript_segments:
        # Trouve le segment qui contient la fin
        for seg in transcript_segments:
            if seg["start"] <= new_end <= seg["end"]:
                text = seg.get("text", "")
                words = text.split()
                if words:
                    last_word = words[-1].lower().rstrip(".,!?;:")
                    if last_word in FORBIDDEN_END_WORDS:
                        # Cherche un meilleur point avant
                        safe_window = (max(0, new_end - 5.0), new_end - 0.5)
                        safe_end, safe_score, safe_reasons = _find_best_cut_point(
                            signals, new_end - 2.0, safe_window, for_start=False
                        )
                        if safe_score > 0.3:
                            new_end = safe_end
                            metadata["end_reasons"] = safe_reasons[:3]
                            metadata["adjustments"].append(f"avoided_forbidden_word:{last_word}")
                break

    # === SNAP TRANSCRIPT (si score de boundary faible) ===
    if transcript_segments and ENABLE_BOUNDARY_SNAP:
        if start_score < snap_threshold:
            start_candidates = [
                float(seg["start"])
                for seg in transcript_segments
                if abs(float(seg["start"]) - new_start) <= max_shift
                and float(seg["start"]) < new_end - 1.0
            ]
            if start_candidates:
                snapped_start = min(start_candidates, key=lambda t: abs(t - new_start))
                if abs(snapped_start - new_start) > 1e-3:
                    new_start = snapped_start
                    start_score = max(start_score, 0.62)
                    metadata["start_score"] = round(start_score, 3)
                    metadata["adjustments"].append("snapped_start_to_transcript")

        if end_score < snap_threshold:
            scored_end_candidates: list[tuple[float, float, float]] = []
            for seg in transcript_segments:
                seg_end = float(seg.get("end", 0.0))
                if seg_end <= new_start + 1.0:
                    continue
                distance = abs(seg_end - new_end)
                if distance > max_shift:
                    continue
                seg_text = str(seg.get("text", "")).strip().lower()
                punct_bonus = 1.0 if SENTENCE_END_PATTERNS.search(seg_text) else 0.0
                story_bonus = 1.0 if any(marker in seg_text for marker in STORY_END_MARKERS) else 0.0
                scored_end_candidates.append((punct_bonus + story_bonus * 0.6, -distance, seg_end))

            if scored_end_candidates:
                scored_end_candidates.sort(reverse=True)
                snapped_end = scored_end_candidates[0][2]
                if abs(snapped_end - new_end) > 1e-3:
                    new_end = snapped_end
                    end_score = max(end_score, 0.66)
                    metadata["end_score"] = round(end_score, 3)
                    metadata["adjustments"].append("snapped_end_to_transcript")

        # Fallback léger: aligne sur les segments qui chevauchent déjà le clip.
        if start_score < snap_threshold or end_score < snap_threshold:
            aligned_start, aligned_end, aligned_score = _align_to_transcript(
                new_start, new_end, transcript_segments
            )
            if aligned_score >= 0.8:
                if (
                    abs(aligned_start - new_start) <= max_shift
                    and aligned_start < new_end - 1.0
                ):
                    new_start = aligned_start
                    start_score = max(start_score, 0.60)
                    metadata["start_score"] = round(start_score, 3)
                    metadata["adjustments"].append("aligned_start_to_transcript_range")
                if (
                    abs(aligned_end - new_end) <= max_shift
                    and aligned_end > new_start + 1.0
                ):
                    new_end = aligned_end
                    end_score = max(end_score, 0.60)
                    metadata["end_score"] = round(end_score, 3)
                    metadata["adjustments"].append("aligned_end_to_transcript_range")
    
    # === CONTRAINTES DE DURÉE ===
    clip_length = new_end - new_start
    
    # Trop court ? Étend intelligemment
    if clip_length < min_clip_length:
        deficit = min_clip_length - clip_length
        # Essaie d'étendre la fin d'abord
        extended_end_window = (new_end, min(duration, new_end + deficit + 3.0))
        ext_end, ext_score, _ = _find_best_cut_point(
            signals, new_end + deficit/2, extended_end_window, for_start=False
        )
        
        if ext_end - new_start >= min_clip_length:
            new_end = ext_end
            metadata["adjustments"].append(f"extended_to_min_length")
        else:
            # Sinon, recule le début
            new_start = max(0, new_end - min_clip_length)
            metadata["adjustments"].append(f"adjusted_start_for_min_length")

    clip_length = new_end - new_start
    
    # Soft trim: si le clip est anormalement long, tente une fin plus naturelle
    # autour d'une cible (sans imposer une limite dure).
    if (
        SMART_TRIM_LONG_CLIPS
        and transcript_segments
        and clip_length > SMART_TRIM_TRIGGER_SECONDS
    ):
        soft_target = max(
            min_clip_length,
            min(max_clip_length, SMART_TRIM_TARGET_SECONDS),
        )
        target_end = min(new_end - 0.4, new_start + soft_target)
        if target_end > new_start + min_clip_length:
            trimmed_end = _pick_soft_trim_end_from_transcript(
                start=new_start,
                current_end=new_end,
                target_end=target_end,
                transcript_segments=transcript_segments,
                min_clip_length=min_clip_length,
                search_window=SMART_TRIM_SEARCH_WINDOW_SECONDS,
            )
            if trimmed_end is None:
                soft_window = (
                    new_start + min_clip_length,
                    min(new_end, target_end + SMART_TRIM_SEARCH_WINDOW_SECONDS),
                )
                if soft_window[1] > soft_window[0]:
                    soft_end, soft_score, _ = _find_best_cut_point(
                        signals,
                        target_end,
                        soft_window,
                        for_start=False,
                    )
                    if soft_score >= 0.35:
                        trimmed_end = soft_end

            if (
                trimmed_end is not None
                and (new_end - trimmed_end) >= SMART_TRIM_MIN_REDUCTION_SECONDS
                and trimmed_end > new_start + min_clip_length
            ):
                new_end = trimmed_end
                end_score = max(end_score, 0.62)
                metadata["end_score"] = round(end_score, 3)
                metadata["adjustments"].append("smart_trim_long_clip")

    clip_length = new_end - new_start

    # Trop long ? Raccourcis intelligemment
    if clip_length > max_clip_length:
        # Cherche une bonne fin plus tôt
        shorter_window = (new_start + min_clip_length, new_start + max_clip_length)
        short_end, short_score, _ = _find_best_cut_point(
            signals,
            max(new_start + min_clip_length, new_start + max_clip_length - 5),
            shorter_window,
            for_start=False,
        )
        
        if short_score > 0.4:
            new_end = short_end
            metadata["adjustments"].append(f"shortened_to_max_length")
        else:
            new_end = new_start + max_clip_length
            metadata["adjustments"].append(f"hard_cut_at_max_length")

    # Après ajustement de durée, tente un micro-resnap pour éviter les fins abruptes.
    if transcript_segments and ENABLE_BOUNDARY_SNAP:
        post_shift = min(max_shift, 0.9)
        aligned_start, aligned_end, aligned_score = _align_to_transcript(
            new_start, new_end, transcript_segments
        )
        if aligned_score >= 0.8:
            candidate_start = new_start
            candidate_end = new_end
            if (
                abs(aligned_start - new_start) <= post_shift
                and aligned_start < new_end - 1.0
            ):
                candidate_start = aligned_start
            if (
                abs(aligned_end - new_end) <= post_shift
                and aligned_end > candidate_start + 1.0
            ):
                candidate_end = aligned_end

            candidate_len = candidate_end - candidate_start
            if min_clip_length <= candidate_len <= max_clip_length:
                if abs(candidate_start - new_start) > 1e-3:
                    new_start = candidate_start
                    start_score = max(start_score, 0.62)
                    metadata["start_score"] = round(start_score, 3)
                    metadata["adjustments"].append("post_length_snap_start")
                if abs(candidate_end - new_end) > 1e-3:
                    new_end = candidate_end
                    end_score = max(end_score, 0.62)
                    metadata["end_score"] = round(end_score, 3)
                    metadata["adjustments"].append("post_length_snap_end")
    
    # === CLAMP FINAL ===
    new_start = max(0.0, new_start)
    new_end = min(duration, new_end)
    
    # Log des ajustements
    if new_start != start or new_end != end:
        LOGGER.debug(
            "Boundaries refined: %.2f-%.2f -> %.2f-%.2f (reasons: start=%s, end=%s)",
            start, end, new_start, new_end,
            metadata["start_reasons"], metadata["end_reasons"]
        )
    
    return new_start, new_end, metadata


def _temporal_iou(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    """Intersection over Union temporelle."""
    inter = max(0.0, min(a_end, b_end) - max(a_start, b_start))
    union = (a_end - a_start) + (b_end - b_start) - inter
    return inter / union if union > 0 else 0.0


def _nms_segments(
    segments: list[tuple[float, float, float, str, str, dict]],
    iou_threshold: float = 0.6,
) -> list[tuple[float, float, float, str, str, dict]]:
    """Supprime les segments très redondants en gardant le meilleur score."""
    if not segments:
        return []

    ordered = sorted(segments, key=lambda item: item[2], reverse=True)
    kept: list[tuple[float, float, float, str, str, dict]] = []

    for seg in ordered:
        start, length, score, tag, reason, features = seg
        end = start + length
        if all(
            _temporal_iou(start, end, k[0], k[0] + k[1]) < iou_threshold
            for k in kept
        ):
            kept.append(seg)

    return kept


LAUGHTER_TOKENS = {
    "haha",
    "hahaha",
    "ahah",
    "ahahah",
    "hehe",
    "hehehe",
    "lol",
    "lmao",
    "mdr",
    "ptdr",
    "xptdr",
    "rires",
    "rire",
    "laugh",
    "laughter",
    "giggle",
    "marrant",
    "rigole",
    "rigolo",
}
TAG_KEYWORDS = {
    "drôle": {
        "lol",
        "mdr",
        "ptdr",
        "haha",
        "hahaha",
        "rires",
        "rire",
        "blague",
        "vanne",
        "marrant",
        "rigolo",
        "punchline",
        "funny",
    },
    "surprise": {
        "quoi",
        "hein",
        "attends",
        "wtf",
        "wow",
        "incroyable",
        "serieux",
        "sérieux",
        "choqué",
        "choque",
        "impossible",
        "dingue",
        "nope",
    },
    "tension": {
        "putain",
        "merde",
        "fuck",
        "attention",
        "stress",
        "panique",
        "panic",
        "peur",
        "danger",
        "chaud",
        "tendu",
        "angoisse",
    },
    "action": {
        "action",
        "go",
        "let's",
        "lets",
        "boom",
        "explosion",
        "rush",
        "fight",
        "headshot",
        "kill",
        "frag",
        "gg",
    },
    "émotion": {
        "triste",
        "pleure",
        "larmes",
        "émotion",
        "emotion",
        "touchant",
        "amour",
        "heureux",
        "désolé",
        "desole",
    },
    "révélation": {
        "secret",
        "révélation",
        "revelation",
        "plot",
        "twist",
        "spoiler",
        "vérité",
        "verite",
        "enfait",
    },
}
PHRASE_KEYWORDS = {
    "drôle": ["tu vas rire", "c'est drôle", "j'en peux plus", "je suis mort"],
    "surprise": [
        "no way",
        "oh my god",
        "c'est pas vrai",
        "c'est pas possible",
        "attends",
        "quoi",
    ],
    "tension": ["attention", "ça craint", "c'est chaud", "c'est tendu"],
    "révélation": ["en fait", "en réalité", "la vérité", "plot twist", "spoiler alert"],
    "action": ["let's go", "c'est parti", "go go", "on y va"],
    "émotion": ["ça me touche", "j'ai les larmes", "ça fait mal"],
}

def _select_segments(
    duration: float,
    series: list[tuple[float, float]],
    seed: str,
    transcript_segments: list[dict[str, Any]],
    audio_path: Path | None = None,
    video_path: Path | None = None,
) -> list[tuple[float, float, float, str, str, dict]]:
    """
    Sélectionne les meilleurs segments pour en faire des clips.
    
    VERSION 4 - DUAL-SOURCE DETECTION (Audio + Story):
    - Détecte les pics audio (zones d'activité)
    - Détecte les story windows (histoires complètes dans le texte)
    - Fusionne les deux sources de candidats
    - Applique le single-pass boundary refinement
    
    Pipeline:
    1. Détection des pics audio (zones d'intérêt sonores)
    2. Détection des story windows (histoires dans le texte) ← NOUVEAU
    3. Fusion et déduplication des candidats
    4. Collecte unifiée des signaux de coupe
    5. Pour chaque candidat: raffinement single-pass + scoring
    """
    if not series:
        return []
    values, avg, deviation = _normalize_series(series)
    if duration <= 12:
        return [(0.0, duration, 0.5, "moment", "segment court", {"score": 0.5})]

    threshold = max(0.12, avg + deviation * 0.25)
    peak_indices_global = _find_peak_indices(values, threshold)
    if ENABLE_LOCAL_PEAKS:
        peak_indices_local = _find_peak_indices_local(values, 60.0, ANALYSIS_WINDOW_SECONDS)
        peak_indices = sorted(set(peak_indices_global + peak_indices_local))
    else:
        peak_indices = peak_indices_global
    
    has_transcript = bool(transcript_segments)
    transcript_ok_for_ollama_text = False
    transcript_stats = _transcript_density_stats([], duration)
    transcript_dropped_for_quality = False
    if has_transcript:
        transcript_ok_for_ollama_text, transcript_stats = _transcript_ok_for_ollama_text(
            transcript_segments,
            duration,
        )
        if not transcript_ok_for_ollama_text:
            transcript_dropped_for_quality = True
            LOGGER.info(
                "Transcript faible detecte, desactivation transcript pour cette selection "
                "(segments=%d words=%d uniq=%d spoken=%.1fs cov=%.3f avg_w/seg=%.2f wps=%.3f)",
                int(transcript_stats["segments"]),
                int(transcript_stats["words"]),
                int(transcript_stats["unique_words"]),
                float(transcript_stats["spoken_seconds"]),
                float(transcript_stats["speech_coverage"]),
                float(transcript_stats["avg_words_per_segment"]),
                float(transcript_stats["wps"]),
            )
            transcript_segments = []
            has_transcript = False
    
    # === PHASE 1: ANALYSES PRÉ-CALCULÉES (une seule fois pour toute la vidéo) ===
    LOGGER.info("Phase 1: Pré-calcul des analyses...")
    
    # Speaker diarization (qui parle quand)
    diarization = []
    if audio_path and PYANNOTE_AVAILABLE and has_transcript:
        LOGGER.info("  - Speaker diarization...")
        diarization = _get_speaker_diarization(audio_path, duration)
        if diarization:
            LOGGER.info("    → %d segments trouvés", len(diarization))
    elif audio_path and PYANNOTE_AVAILABLE and not has_transcript:
        LOGGER.info("  - Speaker diarization skipped: transcript indisponible/faible")
    speaker_change_by_idx: dict[int, float] = {}
    if diarization:
        prev_speaker: str | None = None
        for seg in sorted(diarization, key=lambda item: float(item.get("start", 0.0))):
            speaker = str(seg.get("speaker", "")).strip()
            ts = float(seg.get("start", 0.0))
            if prev_speaker and speaker and speaker != prev_speaker:
                rms_idx = int(round(ts / ANALYSIS_WINDOW_SECONDS))
                if 0 <= rms_idx < len(values):
                    speaker_change_by_idx[rms_idx] = max(
                        speaker_change_by_idx.get(rms_idx, 0.0),
                        1.0,
                    )
            if speaker:
                prev_speaker = speaker
    
    # Scene detection (changements de scène vidéo)
    scenes = []
    if video_path and SCENEDETECT_AVAILABLE:
        LOGGER.info("  - Scene detection...")
        scenes = _detect_scene_changes(video_path)
        if scenes:
            LOGGER.info("    → %d scènes détectées", len(scenes))

    # Visual motion detection (analyse image)
    visual_motion_by_idx: dict[int, float] = {}
    visual_start_by_idx: dict[int, float] = {}
    visual_stop_by_idx: dict[int, float] = {}
    if ENABLE_VISUAL_CAR_DETECTION and video_path and OPENCV_AVAILABLE:
        LOGGER.info("  - Visual motion detection...")
        visual_motion_series = _compute_visual_motion_series(
            video_path,
            sample_fps=VISUAL_MOTION_SAMPLE_FPS,
            resize_width=VISUAL_MOTION_RESIZE_WIDTH,
            roi_bottom_ratio=VISUAL_MOTION_ROI_BOTTOM_RATIO,
        )
        if visual_motion_series:
            vis_values, vis_avg, vis_dev = _normalize_series(visual_motion_series)
            vis_threshold = max(0.45, vis_avg + vis_dev * 0.25)
            vis_peak_indices = _find_peak_indices(vis_values, vis_threshold)
            for idx in vis_peak_indices:
                ts, _ = visual_motion_series[idx]
                rms_idx = int(round(ts / ANALYSIS_WINDOW_SECONDS))
                if 0 <= rms_idx < len(values):
                    visual_motion_by_idx[rms_idx] = max(
                        visual_motion_by_idx.get(rms_idx, 0.0),
                        vis_values[idx],
                    )
            LOGGER.info("    → %d visual motion peaks", len(visual_motion_by_idx))

            start_events, stop_events = _compute_visual_car_start_stop_events(
                video_path,
                sample_fps=VISUAL_MOTION_SAMPLE_FPS,
                resize_width=VISUAL_MOTION_RESIZE_WIDTH,
                roi_bottom_ratio=VISUAL_MOTION_ROI_BOTTOM_RATIO,
                start_threshold=VISUAL_START_EVENT_THRESHOLD,
                stop_threshold=VISUAL_STOP_EVENT_THRESHOLD,
                min_delta=VISUAL_EVENT_MIN_DELTA,
                smooth_seconds=VISUAL_EVENT_SMOOTH_SECONDS,
                cooldown_seconds=VISUAL_EVENT_COOLDOWN_SECONDS,
                motion_series=visual_motion_series,
            )
            for ts, confidence in start_events:
                rms_idx = int(round(ts / ANALYSIS_WINDOW_SECONDS))
                if 0 <= rms_idx < len(values):
                    visual_start_by_idx[rms_idx] = max(
                        visual_start_by_idx.get(rms_idx, 0.0),
                        confidence,
                    )
            for ts, confidence in stop_events:
                rms_idx = int(round(ts / ANALYSIS_WINDOW_SECONDS))
                if 0 <= rms_idx < len(values):
                    visual_stop_by_idx[rms_idx] = max(
                        visual_stop_by_idx.get(rms_idx, 0.0),
                        confidence,
                    )
            LOGGER.info(
                "    → %d visual start events, %d visual stop events",
                len(visual_start_by_idx),
                len(visual_stop_by_idx),
            )

    # Object-level car detection (YOLO): explicit "car visible" signal.
    car_object_presence_by_idx: dict[int, float] = {}
    if ENABLE_OBJECT_CAR_DETECTION and video_path and OBJECT_CAR_DETECTION_AVAILABLE:
        LOGGER.info("  - Object car detection...")
        car_object_series = _compute_car_object_presence_series(
            video_path,
            sample_fps=OBJECT_CAR_SAMPLE_FPS,
            resize_width=OBJECT_CAR_RESIZE_WIDTH,
            conf_threshold=OBJECT_CAR_CONF_THRESHOLD,
            min_area_ratio=OBJECT_CAR_MIN_AREA_RATIO,
            model_name=OBJECT_CAR_MODEL,
        )
        for ts, score in car_object_series:
            rms_idx = int(round(ts / ANALYSIS_WINDOW_SECONDS))
            if 0 <= rms_idx < len(values):
                car_object_presence_by_idx[rms_idx] = max(
                    car_object_presence_by_idx.get(rms_idx, 0.0),
                    float(score),
                )
        if car_object_presence_by_idx:
            LOGGER.info("    → %d object car windows", len(car_object_presence_by_idx))
    elif ENABLE_OBJECT_CAR_DETECTION and video_path:
        LOGGER.info("  - Object car detection skipped: ultralytics/opencv unavailable")

    # Facial emotion detection (face reactions)
    facial_emotion_by_idx: dict[int, float] = {}
    if ENABLE_FACIAL_EMOTION_DETECTION and video_path and FACIAL_EMOTION_AVAILABLE:
        backend_name = _facial_emotion_backend_name(use_fer=FACIAL_EMOTION_USE_FER)
        LOGGER.info("  - Facial emotion detection (%s)...", backend_name)
        facial_emotion_series = _compute_facial_emotion_series(
            video_path,
            sample_fps=FACIAL_EMOTION_SAMPLE_FPS,
            resize_width=FACIAL_EMOTION_RESIZE_WIDTH,
            use_fer=FACIAL_EMOTION_USE_FER,
            min_face_area_ratio=FACIAL_EMOTION_MIN_FACE_AREA_RATIO,
        )
        if facial_emotion_series:
            # `_compute_facial_emotion_series` already returns values normalized to 0..1.
            # Re-normalizing again here can amplify noise into false peaks.
            emo_values = [
                max(0.0, min(1.0, float(score)))
                for _, score in facial_emotion_series
            ]
            if emo_values:
                emo_avg = sum(emo_values) / float(len(emo_values))
            else:
                emo_avg = 0.0
            if len(emo_values) > 1:
                variance = sum((value - emo_avg) ** 2 for value in emo_values) / float(len(emo_values))
                emo_dev = variance ** 0.5
            else:
                emo_dev = 0.0
            emo_threshold = max(
                FACIAL_EMOTION_EVENT_MIN_SCORE,
                emo_avg + emo_dev * 0.25,
            )
            emo_peak_indices = _find_peak_indices(emo_values, emo_threshold)
            for idx in emo_peak_indices:
                ts, _ = facial_emotion_series[idx]
                rms_idx = int(round(ts / ANALYSIS_WINDOW_SECONDS))
                if 0 <= rms_idx < len(values):
                    facial_emotion_by_idx[rms_idx] = max(
                        facial_emotion_by_idx.get(rms_idx, 0.0),
                        emo_values[idx],
                    )
            LOGGER.info("    → %d facial emotion peaks", len(facial_emotion_by_idx))
    elif ENABLE_FACIAL_EMOTION_DETECTION and video_path:
        LOGGER.info("  - Facial emotion detection skipped: backend unavailable")

    # Voice Activity Detection (silences réels)
    audio_vad_series: list[tuple[float, float]] = []
    if ENABLE_VAD and audio_path and (SILERO_AVAILABLE or WEBCVAD_AVAILABLE):
        LOGGER.info("  - Voice activity detection...")
        audio_vad_series = _compute_vad_series(audio_path)
        if audio_vad_series:
            LOGGER.info("    → %d fenêtres VAD", len(audio_vad_series))

    # Onset detection (changements spectro/rythme)
    onset_strength_by_idx: dict[int, float] = {}
    if ENABLE_ONSET and audio_path and LIBROSA_AVAILABLE:
        LOGGER.info("  - Onset detection...")
        onset_series = _compute_onset_series(audio_path)
        if onset_series:
            onset_values, onset_avg, onset_dev = _normalize_series(onset_series)
            onset_threshold = max(0.12, onset_avg + onset_dev * 0.25)
            onset_peak_indices = _find_peak_indices(onset_values, onset_threshold)
            for idx in onset_peak_indices:
                ts, _ = onset_series[idx]
                rms_idx = int(round(ts / ANALYSIS_WINDOW_SECONDS))
                if 0 <= rms_idx < len(values):
                    onset_strength_by_idx[rms_idx] = max(
                        onset_strength_by_idx.get(rms_idx, 0.0),
                        onset_values[idx],
                    )
            LOGGER.info("    → %d onset peaks", len(onset_strength_by_idx))

    # openSMILE voice dynamics (prosody/arousal-like cues)
    opensmile_voice_by_idx: dict[int, float] = {}
    if ENABLE_OPENSMILE and audio_path and OPENSMILE_AVAILABLE:
        LOGGER.info("  - openSMILE voice dynamics...")
        opensmile_series = _compute_opensmile_voice_activity_series(audio_path)
        if opensmile_series:
            smile_values, smile_avg, smile_dev = _normalize_series(opensmile_series)
            smile_threshold = max(
                OPENSMILE_EVENT_MIN_SCORE,
                smile_avg + smile_dev * 0.20,
            )
            smile_peak_indices = _find_peak_indices(smile_values, smile_threshold)
            for idx in smile_peak_indices:
                ts, _ = opensmile_series[idx]
                rms_idx = int(round(ts / ANALYSIS_WINDOW_SECONDS))
                if 0 <= rms_idx < len(values):
                    opensmile_voice_by_idx[rms_idx] = max(
                        opensmile_voice_by_idx.get(rms_idx, 0.0),
                        smile_values[idx],
                    )
            LOGGER.info("    → %d openSMILE peaks", len(opensmile_voice_by_idx))
    elif ENABLE_OPENSMILE and audio_path:
        LOGGER.info("  - openSMILE skipped: backend unavailable")

    # Audio context (speech/music/noise) from inaSpeechSegmenter.
    speech_context_by_idx: dict[int, float] = {}
    music_context_by_idx: dict[int, float] = {}
    noise_context_by_idx: dict[int, float] = {}
    speech_music_mix_by_idx: dict[int, float] = {}
    if (
        ENABLE_AUDIO_CONTEXT_DETECTION
        and AUDIO_CONTEXT_PROVIDER == "inaspeechsegmenter"
        and audio_path
        and INASPEECH_AVAILABLE
    ):
        LOGGER.info("  - Audio context segmentation (inaSpeechSegmenter)...")
        context_series = _compute_inaspeech_context_series(audio_path)
        for ts, speech_ratio, music_ratio, noise_ratio in context_series:
            rms_idx = int(round(ts / ANALYSIS_WINDOW_SECONDS))
            if not (0 <= rms_idx < len(values)):
                continue
            speech_context_by_idx[rms_idx] = max(
                speech_context_by_idx.get(rms_idx, 0.0),
                float(speech_ratio),
            )
            music_context_by_idx[rms_idx] = max(
                music_context_by_idx.get(rms_idx, 0.0),
                float(music_ratio),
            )
            noise_context_by_idx[rms_idx] = max(
                noise_context_by_idx.get(rms_idx, 0.0),
                float(noise_ratio),
            )
            if (
                speech_ratio >= AUDIO_CONTEXT_SPEECH_MIN_RATIO
                and music_ratio >= AUDIO_CONTEXT_MUSIC_MIN_RATIO
            ):
                speech_music_mix_by_idx[rms_idx] = max(
                    speech_music_mix_by_idx.get(rms_idx, 0.0),
                    min(1.0, (float(speech_ratio) + float(music_ratio)) * 0.5),
                )
        if speech_context_by_idx or music_context_by_idx or noise_context_by_idx:
            LOGGER.info(
                "    → %d speech, %d music, %d noise windows",
                len(speech_context_by_idx),
                len(music_context_by_idx),
                len(noise_context_by_idx),
            )
    elif (
        ENABLE_AUDIO_CONTEXT_DETECTION
        and AUDIO_CONTEXT_PROVIDER == "inaspeechsegmenter"
        and audio_path
    ):
        LOGGER.info("  - Audio context skipped: inaSpeechSegmenter unavailable")

    # ffmpeg silencedetect complements RMS/VAD silence detection.
    ffmpeg_silence_segments: list[tuple[float, float]] = []
    if ENABLE_FFMPEG_SILENCE_DETECTION and audio_path:
        ffmpeg_silence_segments = _compute_ffmpeg_silence_segments(
            audio_path,
            noise_db=FFMPEG_SILENCE_NOISE_DB,
            min_silence_seconds=FFMPEG_SILENCE_MIN_SECONDS,
        )
        if ffmpeg_silence_segments:
            LOGGER.info("  - ffmpeg silences: %d segments", len(ffmpeg_silence_segments))

    # Car dynamics (accélération/revving moteur)
    car_strength_by_idx: dict[int, float] = {}
    car_sustain_by_idx: dict[int, float] = {}
    car_start_by_idx: dict[int, float] = {}
    car_start_inferred_by_idx: dict[int, float] = {}
    car_start_scene_cut_by_idx: dict[int, float] = {}
    car_start_launch_by_idx: dict[int, float] = {}
    car_start_launch_silence_start_by_idx: dict[int, float] = {}
    car_start_launch_silence_end_by_idx: dict[int, float] = {}
    car_stop_by_idx: dict[int, float] = {}
    audio_event_start_by_idx: dict[int, float] = {}
    audio_event_stop_by_idx: dict[int, float] = {}
    if ENABLE_CAR_DETECTION and audio_path and LIBROSA_AVAILABLE:
        LOGGER.info("  - Car dynamics detection...")
        car_series = _compute_car_dynamics_series(audio_path)
        if car_series:
            car_values, car_avg, car_dev = _normalize_series(car_series)
            car_threshold = max(CAR_ACCEL_THRESHOLD, car_avg + car_dev * 0.20)
            car_sustain_threshold = car_threshold * 0.90
            car_peak_indices = _find_peak_indices(car_values, car_threshold)
            for idx in car_peak_indices:
                sustain_seconds = _sustained_run_seconds(car_values, idx, car_sustain_threshold)
                if sustain_seconds < CAR_MIN_SUSTAIN_SECONDS:
                    continue
                ts, _ = car_series[idx]
                rms_idx = int(round(ts / ANALYSIS_WINDOW_SECONDS))
                if 0 <= rms_idx < len(values):
                    car_strength_by_idx[rms_idx] = max(
                        car_strength_by_idx.get(rms_idx, 0.0),
                        car_values[idx],
                    )
                    car_sustain_by_idx[rms_idx] = max(
                        car_sustain_by_idx.get(rms_idx, 0.0),
                        sustain_seconds,
                    )
            LOGGER.info(
                "    → %d car dynamics peaks (>= %.1fs)",
                len(car_strength_by_idx),
                CAR_MIN_SUSTAIN_SECONDS,
            )
    if ENABLE_CAR_DETECTION and ENABLE_CAR_START_STOP_DETECTION and audio_path and LIBROSA_AVAILABLE:
        LOGGER.info("  - Car start/stop detection...")
        start_events, stop_events = _compute_car_start_stop_events(
            audio_path,
            window_seconds=ANALYSIS_WINDOW_SECONDS,
            start_threshold=CAR_START_EVENT_THRESHOLD,
            stop_threshold=CAR_STOP_EVENT_THRESHOLD,
            min_delta=CAR_EVENT_MIN_DELTA,
            smooth_seconds=CAR_EVENT_SMOOTH_SECONDS,
            cooldown_seconds=CAR_EVENT_COOLDOWN_SECONDS,
        )
        for ts, confidence in start_events:
            rms_idx = int(round(ts / ANALYSIS_WINDOW_SECONDS))
            if 0 <= rms_idx < len(values):
                car_start_by_idx[rms_idx] = max(
                    car_start_by_idx.get(rms_idx, 0.0),
                    confidence,
                )
        for ts, confidence in stop_events:
            rms_idx = int(round(ts / ANALYSIS_WINDOW_SECONDS))
            if 0 <= rms_idx < len(values):
                car_stop_by_idx[rms_idx] = max(
                    car_stop_by_idx.get(rms_idx, 0.0),
                    confidence,
                )
        LOGGER.info(
            "    → %d start events, %d stop events",
            len(car_start_by_idx),
            len(car_stop_by_idx),
        )

    if ENABLE_CAR_DETECTION and ENABLE_AUDIO_EVENT_DETECTION and audio_path:
        if AUDIO_EVENT_PROVIDER == "yamnet" and YAMNET_AVAILABLE:
            LOGGER.info("  - Audio event detection (YAMNet)...")
            start_events, stop_events = _compute_yamnet_car_start_stop_events(
                audio_path,
                start_threshold=AUDIO_EVENT_START_THRESHOLD,
                stop_threshold=AUDIO_EVENT_STOP_THRESHOLD,
                min_delta=AUDIO_EVENT_MIN_DELTA,
                smooth_seconds=AUDIO_EVENT_SMOOTH_SECONDS,
                cooldown_seconds=AUDIO_EVENT_COOLDOWN_SECONDS,
            )
            for ts, confidence in start_events:
                rms_idx = int(round(ts / ANALYSIS_WINDOW_SECONDS))
                if 0 <= rms_idx < len(values):
                    audio_event_start_by_idx[rms_idx] = max(
                        audio_event_start_by_idx.get(rms_idx, 0.0),
                        confidence,
                    )
            for ts, confidence in stop_events:
                rms_idx = int(round(ts / ANALYSIS_WINDOW_SECONDS))
                if 0 <= rms_idx < len(values):
                    audio_event_stop_by_idx[rms_idx] = max(
                        audio_event_stop_by_idx.get(rms_idx, 0.0),
                        confidence,
                    )
            LOGGER.info(
                "    → %d audio start events, %d audio stop events",
                len(audio_event_start_by_idx),
                len(audio_event_stop_by_idx),
            )
        elif AUDIO_EVENT_PROVIDER == "yamnet":
            LOGGER.info("  - Audio event detection skipped: YAMNet unavailable")

    # Pitch series (cache)
    pitch_series: list[tuple[float, float]] = []
    if ENABLE_ONSET and audio_path and LIBROSA_AVAILABLE:
        LOGGER.info("  - Pitch series (cache)...")
        pitch_series = _compute_pitch_series(audio_path)
        if pitch_series:
            LOGGER.info("    → %d fenêtres pitch", len(pitch_series))

    # Profil auto/forcé avec durée dynamique (talking/car/general)
    profile, min_clip_length, max_clip_length, profile_meta = _resolve_profile_settings(
        duration=duration,
        transcript_segments=transcript_segments,
        car_peaks_count=len(car_strength_by_idx),
        car_object_peaks_count=len(car_object_presence_by_idx),
    )
    LOGGER.info(
        "  - Clip profile=%s (min=%.1fs max=%.1fs, wps=%.2f, car_peaks/min=%.2f audio=%.2f object=%.2f, car_text=%.0f/%.2f, reason=%s)",
        profile,
        min_clip_length,
        max_clip_length,
        float(profile_meta.get("words_per_sec", 0.0)),
        float(profile_meta.get("car_peaks_per_min", 0.0)),
        float(profile_meta.get("car_audio_peaks_per_min", 0.0)),
        float(profile_meta.get("car_object_peaks_per_min", 0.0)),
        float(profile_meta.get("car_text_hits", 0.0)),
        float(profile_meta.get("car_text_score", 0.0)),
        str(profile_meta.get("reason", "")),
    )
    car_profile_active = ENABLE_CAR_DETECTION and (
        profile == "car" or not CAR_SIGNALS_ONLY_IN_CAR_PROFILE
    )
    LOGGER.info(
        "  - Car signals active=%s (profile=%s, only_in_car_profile=%s)",
        car_profile_active,
        profile,
        CAR_SIGNALS_ONLY_IN_CAR_PROFILE,
    )

    if car_profile_active:
        inference_cooldown_frames = max(1, int(round(CAR_EVENT_COOLDOWN_SECONDS / ANALYSIS_WINDOW_SECONDS)))
        min_inference_idx = max(1, int(round(6.0 / ANALYSIS_WINDOW_SECONDS)))
        existing_starts = set(car_start_by_idx.keys())
        inferred_raw: dict[int, float] = {}

        candidate_indices_for_inference = (
            set(car_strength_by_idx.keys())
            | set(onset_strength_by_idx.keys())
            | set(audio_event_start_by_idx.keys())
            | set(visual_start_by_idx.keys())
            | set(car_object_presence_by_idx.keys())
        )
        min_car_for_inference = max(0.30, CAR_ACCEL_THRESHOLD * 0.52)
        min_onset_for_inference = 0.56
        min_visual_for_inference = VISUAL_EVENT_MIN_SCORE * 0.72
        min_yamnet_for_inference = AUDIO_EVENT_MIN_SCORE * 0.72
        min_rise_for_inference = max(0.04, CAR_EVENT_MIN_DELTA * 0.35)

        for idx in sorted(candidate_indices_for_inference):
            if idx < min_inference_idx:
                continue
            if idx >= len(values):
                continue
            if any(abs(idx - existing_idx) <= inference_cooldown_frames for existing_idx in existing_starts):
                continue

            car_level = max(
                car_strength_by_idx.get(idx - 1, 0.0),
                car_strength_by_idx.get(idx, 0.0),
                car_strength_by_idx.get(idx + 1, 0.0),
            )
            if car_level < min_car_for_inference:
                continue

            onset_level = max(
                onset_strength_by_idx.get(idx - 1, 0.0),
                onset_strength_by_idx.get(idx, 0.0),
                onset_strength_by_idx.get(idx + 1, 0.0),
            )
            visual_level = max(
                visual_start_by_idx.get(idx, 0.0),
                visual_motion_by_idx.get(idx, 0.0),
            )
            object_level = max(
                car_object_presence_by_idx.get(idx - 1, 0.0),
                car_object_presence_by_idx.get(idx, 0.0),
                car_object_presence_by_idx.get(idx + 1, 0.0),
            )
            yamnet_level = max(
                audio_event_start_by_idx.get(idx - 1, 0.0),
                audio_event_start_by_idx.get(idx, 0.0),
                audio_event_start_by_idx.get(idx + 1, 0.0),
            )

            evidence_count = 0
            if onset_level >= min_onset_for_inference:
                evidence_count += 1
            if visual_level >= min_visual_for_inference:
                evidence_count += 1
            if object_level >= max(OBJECT_CAR_MIN_SCORE * 0.80, 0.28):
                evidence_count += 1
            if yamnet_level >= min_yamnet_for_inference:
                evidence_count += 1
            if evidence_count == 0:
                continue

            prev_car = max(
                car_strength_by_idx.get(idx - 5, 0.0),
                car_strength_by_idx.get(idx - 4, 0.0),
                car_strength_by_idx.get(idx - 3, 0.0),
                car_strength_by_idx.get(idx - 2, 0.0),
                car_strength_by_idx.get(idx - 1, 0.0),
            )
            rise = max(0.0, car_level - prev_car)
            if rise < min_rise_for_inference and evidence_count < 2:
                continue

            confidence = (
                0.46
                + min(0.24, rise * 0.90)
                + min(0.18, max(0.0, onset_level - 0.50) * 0.80)
                + min(0.14, max(0.0, visual_level - (VISUAL_EVENT_MIN_SCORE * 0.70)))
                + min(0.10, max(0.0, object_level - max(OBJECT_CAR_MIN_SCORE * 0.70, 0.22)))
            )
            if evidence_count >= 2:
                confidence += 0.08
            confidence = max(
                max(CAR_EVENT_MIN_SCORE * 0.90, 0.48),
                min(1.0, confidence),
            )
            inferred_raw[idx] = max(inferred_raw.get(idx, 0.0), confidence)

        if inferred_raw:
            filtered_inferred: dict[int, float] = {}
            last_kept_idx: int | None = None
            for idx, confidence in sorted(inferred_raw.items()):
                if last_kept_idx is None or (idx - last_kept_idx) > inference_cooldown_frames:
                    filtered_inferred[idx] = confidence
                    last_kept_idx = idx
                    continue
                if confidence > filtered_inferred[last_kept_idx]:
                    filtered_inferred.pop(last_kept_idx, None)
                    filtered_inferred[idx] = confidence
                    last_kept_idx = idx

            for idx, confidence in filtered_inferred.items():
                car_start_by_idx[idx] = max(car_start_by_idx.get(idx, 0.0), confidence)
                car_start_inferred_by_idx[idx] = confidence
            LOGGER.info(
                "  - Car insertion fallback: %d start events inférés",
                len(filtered_inferred),
            )

    if car_profile_active and scenes:
        min_scene_idx = max(1, int(round(5.0 / ANALYSIS_WINDOW_SECONDS)))
        max_scene_idx = max(1, len(values) - 2)
        for scene_start, scene_end in scenes:
            for scene_ts in (scene_start, scene_end):
                scene_idx = int(round(float(scene_ts) / ANALYSIS_WINDOW_SECONDS))
                scene_idx = max(1, min(max_scene_idx, scene_idx))
                if scene_idx < min_scene_idx:
                    continue

                start_near_cut = max(
                    car_start_by_idx.get(scene_idx - 2, 0.0),
                    car_start_by_idx.get(scene_idx - 1, 0.0),
                    car_start_by_idx.get(scene_idx, 0.0),
                    car_start_by_idx.get(scene_idx + 1, 0.0),
                    car_start_by_idx.get(scene_idx + 2, 0.0),
                )
                accel_after_cut = max(
                    car_strength_by_idx.get(scene_idx, 0.0),
                    car_strength_by_idx.get(scene_idx + 1, 0.0),
                    car_strength_by_idx.get(scene_idx + 2, 0.0),
                    car_strength_by_idx.get(scene_idx + 3, 0.0),
                )
                onset_after_cut = max(
                    onset_strength_by_idx.get(scene_idx, 0.0),
                    onset_strength_by_idx.get(scene_idx + 1, 0.0),
                    onset_strength_by_idx.get(scene_idx + 2, 0.0),
                )
                visual_after_cut = max(
                    visual_motion_by_idx.get(scene_idx, 0.0),
                    visual_motion_by_idx.get(scene_idx + 1, 0.0),
                )

                has_start = start_near_cut >= max(0.42, CAR_EVENT_MIN_SCORE * 0.80)
                has_post_cut_impulse = (
                    accel_after_cut >= max(0.30, CAR_ACCEL_THRESHOLD * 0.48)
                    or onset_after_cut >= 0.56
                    or visual_after_cut >= VISUAL_EVENT_MIN_SCORE * 0.80
                )
                if not (has_start and has_post_cut_impulse):
                    continue

                confidence = min(
                    1.0,
                    0.50
                    + min(0.22, start_near_cut * 0.30)
                    + min(0.16, accel_after_cut * 0.25)
                    + min(0.10, onset_after_cut * 0.20),
                )
                scene_transition_idx = max(1, scene_idx + 1)
                car_start_scene_cut_by_idx[scene_transition_idx] = max(
                    car_start_scene_cut_by_idx.get(scene_transition_idx, 0.0),
                    confidence,
                )

        if car_start_scene_cut_by_idx:
            for idx, confidence in car_start_scene_cut_by_idx.items():
                car_start_by_idx[idx] = max(car_start_by_idx.get(idx, 0.0), confidence)
            LOGGER.info(
                "  - Car scene-cut fallback: %d start events scene-cut",
                len(car_start_scene_cut_by_idx),
            )

    if car_profile_active and ffmpeg_silence_segments:
        launch_min_silence = max(0.45, FFMPEG_SILENCE_MIN_SECONDS * 1.9)
        launch_search_start = max(0, int(round(0.20 / ANALYSIS_WINDOW_SECONDS)))
        launch_search_end = max(launch_search_start + 1, int(round(4.8 / ANALYSIS_WINDOW_SECONDS)))
        launch_cooldown = max(2, int(round(2.5 / ANALYSIS_WINDOW_SECONDS)))
        launch_min_car = max(0.28, CAR_ACCEL_THRESHOLD * 0.44)
        launch_min_onset = 0.46
        launch_min_rise = max(0.08, CAR_EVENT_MIN_DELTA * 0.55)

        max_idx = max(2, len(values) - 2)
        last_launch_idx: int | None = None
        for silence_start, silence_end in ffmpeg_silence_segments:
            silence_duration = max(0.0, float(silence_end) - float(silence_start))
            if silence_duration < launch_min_silence:
                continue

            silence_end_idx = int(round(float(silence_end) / ANALYSIS_WINDOW_SECONDS))
            silence_end_idx = max(1, min(max_idx, silence_end_idx))
            if silence_end_idx < 2:
                continue
            if last_launch_idx is not None and (silence_end_idx - last_launch_idx) <= launch_cooldown:
                continue

            pre_idx = max(0, silence_end_idx - 2)
            pre_level = max(
                values[pre_idx],
                values[max(0, pre_idx - 1)],
            )

            best_idx = -1
            best_score = 0.0
            for offset in range(launch_search_start, launch_search_end + 1):
                idx = silence_end_idx + offset
                if idx >= len(values):
                    break

                car_level = max(
                    car_strength_by_idx.get(idx - 1, 0.0),
                    car_strength_by_idx.get(idx, 0.0),
                    car_strength_by_idx.get(idx + 1, 0.0),
                )
                onset_level = max(
                    onset_strength_by_idx.get(idx - 1, 0.0),
                    onset_strength_by_idx.get(idx, 0.0),
                    onset_strength_by_idx.get(idx + 1, 0.0),
                )
                yamnet_level = max(
                    audio_event_start_by_idx.get(idx - 1, 0.0),
                    audio_event_start_by_idx.get(idx, 0.0),
                    audio_event_start_by_idx.get(idx + 1, 0.0),
                )
                visual_level = max(
                    visual_start_by_idx.get(idx - 1, 0.0),
                    visual_start_by_idx.get(idx, 0.0),
                    visual_motion_by_idx.get(idx, 0.0),
                )
                rise = max(0.0, values[idx] - pre_level)
                soft_launch_gate = (
                    rise >= (launch_min_rise * 1.35)
                    and onset_level >= (launch_min_onset * 0.85)
                )

                has_primary_impulse = (
                    car_level >= launch_min_car
                    or yamnet_level >= max(AUDIO_EVENT_MIN_SCORE * 0.72, 0.24)
                    or visual_level >= max(VISUAL_EVENT_MIN_SCORE * 0.72, 0.30)
                    or soft_launch_gate
                )
                has_secondary_impulse = (
                    onset_level >= launch_min_onset
                    or rise >= launch_min_rise
                    or car_level >= (launch_min_car * 1.15)
                )
                if not (has_primary_impulse and has_secondary_impulse):
                    continue

                delay_seconds = max(0.0, (idx - silence_end_idx) * ANALYSIS_WINDOW_SECONDS)
                score = (
                    0.34
                    + min(0.24, car_level * 0.34)
                    + min(0.18, max(0.0, onset_level - 0.40) * 0.36)
                    + min(0.16, yamnet_level * 0.30)
                    + min(0.10, visual_level * 0.20)
                    + min(0.14, rise * 0.70)
                    - min(0.12, delay_seconds * 0.020)
                )
                if score > best_score:
                    best_score = score
                    best_idx = idx

            if best_idx >= 0 and best_score >= 0.42:
                confidence = max(
                    max(CAR_EVENT_MIN_SCORE * 0.84, 0.46),
                    min(1.0, best_score),
                )
                car_start_launch_by_idx[best_idx] = max(
                    car_start_launch_by_idx.get(best_idx, 0.0),
                    confidence,
                )
                car_start_launch_silence_start_by_idx[best_idx] = min(
                    car_start_launch_silence_start_by_idx.get(best_idx, float(silence_start)),
                    float(silence_start),
                )
                car_start_launch_silence_end_by_idx[best_idx] = max(
                    car_start_launch_silence_end_by_idx.get(best_idx, float(silence_end)),
                    float(silence_end),
                )
                car_start_by_idx[best_idx] = max(car_start_by_idx.get(best_idx, 0.0), confidence)
                last_launch_idx = best_idx

        if car_start_launch_by_idx:
            LOGGER.info(
                "  - Car launch fallback (silence→accel): %d starts",
                len(car_start_launch_by_idx),
            )

    if car_profile_active and values:
        launch_rms_cooldown = max(2, int(round(2.8 / ANALYSIS_WINDOW_SECONDS)))
        launch_rms_search_right = max(1, int(round(1.2 / ANALYSIS_WINDOW_SECONDS)))
        launch_rms_max_quiet_back = max(3, int(round(6.0 / ANALYSIS_WINDOW_SECONDS)))
        launch_rms_min_rise = max(0.09, CAR_EVENT_MIN_DELTA * 0.62)
        sorted_values = sorted(values)
        q30_idx = min(len(sorted_values) - 1, max(0, int(len(sorted_values) * 0.30)))
        quiet_threshold = max(0.08, min(0.34, sorted_values[q30_idx] + 0.05))
        last_launch_idx: int | None = None
        rms_added = 0

        for idx in range(3, len(values) - 2):
            if last_launch_idx is not None and (idx - last_launch_idx) <= launch_rms_cooldown:
                continue

            pre_quiet_level = max(values[idx - 1], values[idx - 2], values[idx - 3])
            if pre_quiet_level > quiet_threshold:
                continue

            post_best_car = 0.0
            post_best_onset = 0.0
            post_best_yamnet = 0.0
            post_best_visual = 0.0
            post_best_rise = 0.0
            for right in range(0, launch_rms_search_right + 1):
                probe_idx = idx + right
                if probe_idx >= len(values):
                    break
                post_best_car = max(
                    post_best_car,
                    float(car_strength_by_idx.get(probe_idx, 0.0)),
                )
                post_best_onset = max(
                    post_best_onset,
                    float(onset_strength_by_idx.get(probe_idx, 0.0)),
                )
                post_best_yamnet = max(
                    post_best_yamnet,
                    float(audio_event_start_by_idx.get(probe_idx, 0.0)),
                )
                post_best_visual = max(
                    post_best_visual,
                    float(visual_start_by_idx.get(probe_idx, 0.0)),
                )
                post_best_rise = max(
                    post_best_rise,
                    max(0.0, values[probe_idx] - pre_quiet_level),
                )

            has_primary = (
                post_best_car >= max(0.24, CAR_ACCEL_THRESHOLD * 0.40)
                or post_best_onset >= 0.56
                or post_best_yamnet >= max(AUDIO_EVENT_MIN_SCORE * 0.70, 0.24)
                or post_best_visual >= max(VISUAL_EVENT_MIN_SCORE * 0.70, 0.30)
            )
            has_secondary = (
                post_best_rise >= launch_rms_min_rise
                or post_best_onset >= 0.50
                or post_best_car >= max(0.30, CAR_ACCEL_THRESHOLD * 0.48)
            )
            if not (has_primary and has_secondary):
                continue

            score = (
                0.30
                + min(0.25, post_best_car * 0.34)
                + min(0.18, max(0.0, post_best_onset - 0.38) * 0.34)
                + min(0.14, post_best_rise * 0.74)
                + min(0.12, post_best_yamnet * 0.30)
                + min(0.09, post_best_visual * 0.22)
            )
            confidence = max(
                max(CAR_EVENT_MIN_SCORE * 0.84, 0.46),
                min(1.0, score),
            )
            if confidence < 0.46:
                continue

            quiet_start_idx = idx - 1
            while (
                quiet_start_idx > 1
                and (idx - quiet_start_idx) <= launch_rms_max_quiet_back
                and values[quiet_start_idx - 1] <= quiet_threshold
            ):
                quiet_start_idx -= 1

            silence_start_ts = max(0.0, quiet_start_idx * ANALYSIS_WINDOW_SECONDS)
            silence_end_ts = min(duration, idx * ANALYSIS_WINDOW_SECONDS)
            car_start_launch_by_idx[idx] = max(
                car_start_launch_by_idx.get(idx, 0.0),
                confidence,
            )
            car_start_launch_silence_start_by_idx[idx] = min(
                car_start_launch_silence_start_by_idx.get(idx, silence_start_ts),
                silence_start_ts,
            )
            car_start_launch_silence_end_by_idx[idx] = max(
                car_start_launch_silence_end_by_idx.get(idx, silence_end_ts),
                silence_end_ts,
            )
            car_start_by_idx[idx] = max(car_start_by_idx.get(idx, 0.0), confidence)
            rms_added += 1
            last_launch_idx = idx

        if rms_added > 0:
            LOGGER.info(
                "  - Car launch fallback (rms quiet→accel): %d starts",
                rms_added,
            )
    
    # === PHASE 2: COLLECTE UNIFIÉE DE TOUS LES SIGNAUX DE COUPE ===
    LOGGER.info("Phase 2: Collecte des signaux de coupe...")
    all_cut_signals = _collect_all_cut_signals(
        transcript_segments=transcript_segments,
        diarization=diarization,
        scenes=scenes,
        audio_rms_series=series,
        audio_vad_series=audio_vad_series,
        ffmpeg_silence_segments=ffmpeg_silence_segments,
        audio_path=audio_path,
        duration=duration,
    )
    LOGGER.info("  → %d signaux collectés", len(all_cut_signals))

    # === PHASE 3: DÉTECTION DUAL-SOURCE (Audio + Story) ===
    LOGGER.info("Phase 3: Détection des candidats...")
    
    # 3a. Candidats audio (pics RMS)
    audio_candidates: list[tuple[int, dict]] = []
    audio_candidate_features_by_idx: dict[int, dict[str, Any]] = {}
    candidate_indices = (
        set(peak_indices)
        | set(onset_strength_by_idx.keys())
        | set(opensmile_voice_by_idx.keys())
        | set(speaker_change_by_idx.keys())
        | set(visual_motion_by_idx.keys())
        | set(car_object_presence_by_idx.keys())
        | set(facial_emotion_by_idx.keys())
    )
    if car_profile_active:
        candidate_indices |= (
            set(car_strength_by_idx.keys())
            | set(car_start_by_idx.keys())
            | set(car_stop_by_idx.keys())
            | set(audio_event_start_by_idx.keys())
            | set(audio_event_stop_by_idx.keys())
            | set(visual_start_by_idx.keys())
            | set(visual_stop_by_idx.keys())
        )
    object_signal_available = bool(car_object_presence_by_idx)
    for idx in candidate_indices:
        features = _feature_bundle(values, idx, avg, deviation)
        onset_strength = onset_strength_by_idx.get(idx, 0.0)
        opensmile_voice_score = opensmile_voice_by_idx.get(idx, 0.0)
        car_accel_score = car_strength_by_idx.get(idx, 0.0) if car_profile_active else 0.0
        car_sustain_seconds = car_sustain_by_idx.get(idx, 0.0) if car_profile_active else 0.0
        audio_start_score = car_start_by_idx.get(idx, 0.0) if car_profile_active else 0.0
        audio_stop_score = car_stop_by_idx.get(idx, 0.0) if car_profile_active else 0.0
        event_start_score = audio_event_start_by_idx.get(idx, 0.0) if car_profile_active else 0.0
        event_stop_score = audio_event_stop_by_idx.get(idx, 0.0) if car_profile_active else 0.0
        inferred_start_score = car_start_inferred_by_idx.get(idx, 0.0) if car_profile_active else 0.0
        scene_cut_start_score = car_start_scene_cut_by_idx.get(idx, 0.0) if car_profile_active else 0.0
        launch_start_score = car_start_launch_by_idx.get(idx, 0.0) if car_profile_active else 0.0
        speech_context_ratio = speech_context_by_idx.get(idx, 0.0)
        music_context_ratio = music_context_by_idx.get(idx, 0.0)
        noise_context_ratio = noise_context_by_idx.get(idx, 0.0)
        speech_music_mix_score = speech_music_mix_by_idx.get(idx, 0.0)
        speaker_change_score = speaker_change_by_idx.get(idx, 0.0)
        visual_motion_score = visual_motion_by_idx.get(idx, 0.0)
        car_object_score = car_object_presence_by_idx.get(idx, 0.0)
        facial_emotion_score = facial_emotion_by_idx.get(idx, 0.0)
        visual_start_score = visual_start_by_idx.get(idx, 0.0) if car_profile_active else 0.0
        visual_stop_score = visual_stop_by_idx.get(idx, 0.0) if car_profile_active else 0.0
        car_start_score = max(
            audio_start_score,
            event_start_score,
            visual_start_score,
            inferred_start_score,
            scene_cut_start_score,
            launch_start_score,
        )
        car_stop_score = max(audio_stop_score, event_stop_score, visual_stop_score)
        car_is_sustained = car_sustain_seconds >= CAR_MIN_SUSTAIN_SECONDS
        car_start_event = (
            audio_start_score >= CAR_EVENT_MIN_SCORE
            or event_start_score >= AUDIO_EVENT_MIN_SCORE
            or visual_start_score >= VISUAL_EVENT_MIN_SCORE
            or inferred_start_score >= max(CAR_EVENT_MIN_SCORE * 0.90, 0.48)
            or scene_cut_start_score >= max(CAR_EVENT_MIN_SCORE * 0.82, 0.46)
            or launch_start_score >= max(CAR_EVENT_MIN_SCORE * 0.84, 0.46)
        )
        car_stop_event = (
            audio_stop_score >= CAR_EVENT_MIN_SCORE
            or event_stop_score >= AUDIO_EVENT_MIN_SCORE
            or visual_stop_score >= VISUAL_EVENT_MIN_SCORE
        )
        visual_motion_event = visual_motion_score >= VISUAL_EVENT_MIN_SCORE
        car_object_event = car_object_score >= OBJECT_CAR_MIN_SCORE
        facial_emotion_event = facial_emotion_score >= FACIAL_EMOTION_EVENT_MIN_SCORE
        opensmile_voice_event = opensmile_voice_score >= OPENSMILE_EVENT_MIN_SCORE
        speaker_change_event = speaker_change_score >= 0.5
        object_gate_ok = (not object_signal_available) or (
            car_object_score >= max(OBJECT_CAR_MIN_SCORE * 0.82, 0.28)
        )
        visual_walkaround_silent_event = bool(
            car_profile_active
            and speech_context_ratio <= AUDIO_CONTEXT_SPEECH_MIN_RATIO * 0.60
            and not opensmile_voice_event
            and not speaker_change_event
            and visual_motion_score >= max(0.26, VISUAL_EVENT_MIN_SCORE * 0.60)
            and visual_motion_score <= max(0.60, VISUAL_EVENT_MIN_SCORE * 1.22)
            and object_gate_ok
            and car_accel_score <= max(0.48, CAR_ACCEL_THRESHOLD * 0.76)
            and not car_start_event
            and not car_stop_event
        )
        car_stationary_showcase_event = bool(
            car_profile_active
            and object_signal_available
            and car_object_score >= max(OBJECT_CAR_MIN_SCORE * 1.12, 0.46)
            and visual_motion_score <= max(0.34, VISUAL_EVENT_MIN_SCORE * 0.78)
            and car_accel_score <= max(0.34, CAR_ACCEL_THRESHOLD * 0.52)
            and not car_start_event
            and not car_stop_event
        )
        features["onset_strength"] = round(onset_strength, 3)
        features["onset_peak"] = onset_strength > 0
        features["opensmile_voice_score"] = round(opensmile_voice_score, 3)
        features["opensmile_voice_event"] = opensmile_voice_event
        features["speech_context_ratio"] = round(speech_context_ratio, 3)
        features["music_context_ratio"] = round(music_context_ratio, 3)
        features["noise_context_ratio"] = round(noise_context_ratio, 3)
        features["speech_music_mix_score"] = round(speech_music_mix_score, 3)
        features["speaker_change_score"] = round(speaker_change_score, 3)
        features["speaker_change_event"] = speaker_change_event
        features["car_accel_score"] = round(car_accel_score, 3)
        features["car_peak"] = car_accel_score > 0
        features["car_sustain_seconds"] = round(car_sustain_seconds, 3)
        features["car_sustained"] = car_is_sustained
        features["car_start_score"] = round(car_start_score, 3)
        features["car_stop_score"] = round(car_stop_score, 3)
        features["car_start_event"] = car_start_event
        features["car_stop_event"] = car_stop_event
        features["car_start_from_audio"] = audio_start_score >= CAR_EVENT_MIN_SCORE
        features["car_stop_from_audio"] = audio_stop_score >= CAR_EVENT_MIN_SCORE
        features["car_start_from_yamnet"] = event_start_score >= AUDIO_EVENT_MIN_SCORE
        features["car_stop_from_yamnet"] = event_stop_score >= AUDIO_EVENT_MIN_SCORE
        features["car_start_from_visual"] = visual_start_score >= VISUAL_EVENT_MIN_SCORE
        features["car_stop_from_visual"] = visual_stop_score >= VISUAL_EVENT_MIN_SCORE
        features["car_start_from_inferred"] = inferred_start_score >= max(CAR_EVENT_MIN_SCORE * 0.90, 0.48)
        features["car_start_from_scene_cut"] = scene_cut_start_score >= max(CAR_EVENT_MIN_SCORE * 0.82, 0.46)
        features["car_start_from_launch"] = launch_start_score >= max(CAR_EVENT_MIN_SCORE * 0.84, 0.46)
        features["visual_motion_score"] = round(visual_motion_score, 3)
        features["visual_motion_event"] = visual_motion_event
        features["car_object_score"] = round(car_object_score, 3)
        features["car_object_event"] = bool(car_object_event)
        features["car_visual_walkaround_silent_event"] = visual_walkaround_silent_event
        features["car_stationary_showcase_event"] = car_stationary_showcase_event
        features["facial_emotion_score"] = round(facial_emotion_score, 3)
        features["facial_emotion_event"] = facial_emotion_event

        strong_car_signal = (
            car_profile_active
            and car_accel_score >= CAR_ACCEL_THRESHOLD
            and car_is_sustained
        )
        car_showcase_event = _is_car_showcase_event(
            car_profile_active=car_profile_active,
            visual_motion_score=visual_motion_score,
            visual_motion_event=visual_motion_event,
            speech_context_ratio=speech_context_ratio,
            speech_context_event=speech_context_ratio >= AUDIO_CONTEXT_SPEECH_MIN_RATIO,
            opensmile_voice_event=opensmile_voice_event,
            speaker_change_event=speaker_change_event,
            strong_car_signal=strong_car_signal,
            car_start_event=car_start_event,
            car_stop_event=car_stop_event,
            car_accel_score=car_accel_score,
            car_object_score=car_object_score,
        )
        if visual_walkaround_silent_event:
            car_showcase_event = True
        if car_stationary_showcase_event:
            car_showcase_event = True
        features["car_showcase_event"] = car_showcase_event

        # Candidate ranking score (used before full scoring/refinement).
        # Boost start/stop/showcase car moments so they survive merge pruning.
        merge_score = float(features.get("score", 0.0))
        if car_profile_active:
            if car_start_event:
                merge_score += 0.16
            if car_stop_event:
                merge_score += 0.12
            if features.get("car_start_from_inferred", False):
                merge_score += 0.06
            if features.get("car_start_from_scene_cut", False):
                merge_score += 0.08
            if features.get("car_start_from_launch", False):
                merge_score += 0.12
            if car_showcase_event:
                merge_score += 0.12
            if strong_car_signal:
                merge_score += 0.08
            if visual_motion_event:
                merge_score += 0.05
            if car_object_event:
                merge_score += 0.10
            if visual_walkaround_silent_event:
                merge_score += 0.10
            if car_stationary_showcase_event:
                merge_score += 0.12
            if (
                not has_transcript
                and not strong_car_signal
                and not car_start_event
                and not car_stop_event
                and visual_motion_score >= max(0.34, VISUAL_EVENT_MIN_SCORE * 0.78)
            ):
                # Keep low-dialogue visual car moments alive before merge pruning.
                merge_score += 0.10
            if (
                (features.get("car_start_from_visual", False) and car_start_event)
                or (features.get("car_stop_from_visual", False) and car_stop_event)
            ):
                merge_score += 0.05
        features["merge_score"] = round(min(1.0, max(0.0, merge_score)), 3)

        min_threshold = MIN_SCORE * 0.7  # Seuil légèrement plus bas
        if (
            onset_strength >= 0.6
            or opensmile_voice_event
            or (car_profile_active and (strong_car_signal or car_start_event or car_stop_event))
            or visual_motion_event
            or facial_emotion_event
            or speaker_change_event
            or car_showcase_event
            or car_object_event
            or visual_walkaround_silent_event
            or car_stationary_showcase_event
        ):
            min_threshold = MIN_SCORE * 0.5

        if (
            features["score"] >= min_threshold
            or onset_strength >= 0.6
            or opensmile_voice_event
            or (car_profile_active and (strong_car_signal or car_start_event or car_stop_event))
            or visual_motion_event
            or facial_emotion_event
            or speaker_change_event
            or car_showcase_event
            or car_object_event
            or visual_walkaround_silent_event
            or car_stationary_showcase_event
        ):
            audio_candidates.append((idx, features))
            audio_candidate_features_by_idx[idx] = features

    LOGGER.info("  - Pics audio: %d candidats", len(audio_candidates))
    
    # 3b. Candidats story (histoires dans le texte) ← NOUVEAU
    story_candidates = []
    if has_transcript:
        story_candidates = _find_story_windows(
            transcript_segments,
            min_duration=min_clip_length,
            max_duration=max_clip_length,
        )
        LOGGER.info("  - Story windows: %d candidats", len(story_candidates))
        if car_profile_active:
            car_exterior_story_candidates = _build_car_exterior_story_candidates(
                transcript_segments,
                duration=duration,
                min_clip_length=min_clip_length,
                max_clip_length=max_clip_length,
            )
            if car_exterior_story_candidates:
                story_candidates.extend(car_exterior_story_candidates)
                LOGGER.info(
                    "  - Story windows tour exterieur: %d candidats",
                    len(car_exterior_story_candidates),
                )
    
    # 3c. Fusion des deux sources
    if car_profile_active and not has_transcript:
        # Low-text driving videos benefit from denser candidate sampling.
        candidate_min_distance = max(14.0, min_clip_length * 0.40)
    else:
        candidate_min_distance = max(MIN_DISTANCE_SECONDS, min_clip_length * 0.55)
    merged_candidates = _merge_audio_and_story_candidates(
        audio_candidates=audio_candidates,
        story_candidates=story_candidates,
        series=series,
        min_distance=candidate_min_distance,
    )

    if car_profile_active and car_start_launch_by_idx:
        launch_injected = 0
        launch_representation_gap = max(7.0, candidate_min_distance * 0.52)
        launch_dedupe_gap = max(5.0, candidate_min_distance * 0.42)
        for launch_idx, launch_conf in sorted(
            car_start_launch_by_idx.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            if not (0 <= launch_idx < len(series)):
                continue
            center = float(series[launch_idx][0])
            if any(
                abs(center - float(existing.get("center", 0.0))) < launch_representation_gap
                and (
                    bool(existing.get("force_launch_candidate", False))
                    or bool((existing.get("audio_features") or {}).get("car_start_from_launch", False))
                )
                for existing in merged_candidates
            ):
                continue
            if any(
                abs(center - float(existing.get("center", 0.0))) < launch_dedupe_gap
                for existing in merged_candidates
            ):
                continue

            base_features = dict(
                audio_candidate_features_by_idx.get(
                    launch_idx,
                    _feature_bundle(values, launch_idx, avg, deviation),
                )
            )
            base_features["car_start_event"] = True
            base_features["car_transition_focus"] = True
            base_features["car_launch_focus"] = True
            base_features["car_start_from_launch"] = True
            base_features["car_start_score"] = round(
                max(
                    float(base_features.get("car_start_score", 0.0)),
                    float(launch_conf),
                    max(CAR_EVENT_MIN_SCORE * 0.84, 0.46),
                ),
                3,
            )
            merged_score = max(
                float(base_features.get("merge_score", base_features.get("score", 0.0))),
                float(base_features.get("score", 0.0)) + 0.20,
                0.64,
            )
            merged_score = min(1.0, merged_score)
            base_features["merge_score"] = round(merged_score, 3)

            merged_candidates.append(
                {
                    "center": center,
                    "audio_idx": launch_idx,
                    "audio_features": base_features,
                    "score": merged_score,
                    "source": "audio_peak",
                    "start": None,
                    "end": None,
                    "force_launch_candidate": True,
                }
            )
            launch_injected += 1
            if launch_injected >= 2:
                break

        if launch_injected > 0:
            merged_candidates.sort(key=lambda item: -float(item["score"]))
            LOGGER.info("  - Car launch candidates injected: %d", launch_injected)
    
    if not merged_candidates:
        LOGGER.warning("Aucun candidat trouvé (audio ou story)")
        return _fallback_segments(
            duration,
            seed,
            min_clip_length=min_clip_length,
            max_clip_length=max_clip_length,
        )
    
    LOGGER.info("  → %d candidats après fusion", len(merged_candidates))

    variant_rng: random.Random | random.SystemRandom | None = None
    if (
        ENABLE_CLIP_VARIATION
        and len(merged_candidates) > 1
        and CLIP_VARIATION_JITTER > 0
    ):
        variant_rng = random.SystemRandom()
        top_k = max(1, min(CLIP_VARIATION_TOP_K, len(merged_candidates)))
        head = list(merged_candidates[:top_k])
        for candidate in head:
            candidate["_variant_rank"] = candidate["score"] + variant_rng.uniform(
                -CLIP_VARIATION_JITTER, CLIP_VARIATION_JITTER
            )
        head.sort(key=lambda item: item.get("_variant_rank", item["score"]), reverse=True)
        merged_candidates = head + merged_candidates[top_k:]
        LOGGER.info(
            "  - Variation active: candidats ±%.2f sur top-%d, score ±%.3f",
            CLIP_VARIATION_JITTER,
            top_k,
            CLIP_VARIATION_SCORE_JITTER,
        )

    # === PHASE 4: TRAITEMENT DE CHAQUE CANDIDAT ===
    segments: list[tuple[float, float, float, str, str, dict]] = []
    
    # Vérifie si Ollama est disponible (texte + vision optionnelle)
    ollama_text_eligible = has_transcript and transcript_ok_for_ollama_text
    ollama_text_available = _ollama_check_available() if ollama_text_eligible else False
    if ollama_text_available:
        LOGGER.info(
            "Ollama texte active (segments=%d words=%d uniq=%d spoken=%.1fs cov=%.3f avg_w/seg=%.2f wps=%.3f)",
            int(transcript_stats["segments"]),
            int(transcript_stats["words"]),
            int(transcript_stats["unique_words"]),
            float(transcript_stats["spoken_seconds"]),
            float(transcript_stats["speech_coverage"]),
            float(transcript_stats["avg_words_per_segment"]),
            float(transcript_stats["wps"]),
        )
    elif transcript_dropped_for_quality:
        LOGGER.info(
            "Ollama texte ignore: transcript faible desactive avant scoring "
            "(segments=%d words=%d uniq=%d spoken=%.1fs cov=%.3f avg_w/seg=%.2f wps=%.3f | min seg=%d words=%d uniq=%d spoken=%.1fs cov=%.3f avg_w/seg=%.2f wps=%.3f)",
            int(transcript_stats["segments"]),
            int(transcript_stats["words"]),
            int(transcript_stats["unique_words"]),
            float(transcript_stats["spoken_seconds"]),
            float(transcript_stats["speech_coverage"]),
            float(transcript_stats["avg_words_per_segment"]),
            float(transcript_stats["wps"]),
            OLLAMA_TEXT_MIN_SEGMENTS,
            OLLAMA_TEXT_MIN_WORDS,
            OLLAMA_TEXT_MIN_UNIQUE_WORDS,
            OLLAMA_TEXT_MIN_SPOKEN_SECONDS,
            OLLAMA_TEXT_MIN_COVERAGE_RATIO,
            OLLAMA_TEXT_MIN_AVG_WORDS_PER_SEGMENT,
            OLLAMA_TEXT_MIN_WPS,
        )
    elif has_transcript and not ollama_text_eligible:
        LOGGER.info(
            "Ollama texte ignore: transcript faible (segments=%d words=%d uniq=%d spoken=%.1fs cov=%.3f avg_w/seg=%.2f wps=%.3f | min seg=%d words=%d uniq=%d spoken=%.1fs cov=%.3f avg_w/seg=%.2f wps=%.3f)",
            int(transcript_stats["segments"]),
            int(transcript_stats["words"]),
            int(transcript_stats["unique_words"]),
            float(transcript_stats["spoken_seconds"]),
            float(transcript_stats["speech_coverage"]),
            float(transcript_stats["avg_words_per_segment"]),
            float(transcript_stats["wps"]),
            OLLAMA_TEXT_MIN_SEGMENTS,
            OLLAMA_TEXT_MIN_WORDS,
            OLLAMA_TEXT_MIN_UNIQUE_WORDS,
            OLLAMA_TEXT_MIN_SPOKEN_SECONDS,
            OLLAMA_TEXT_MIN_COVERAGE_RATIO,
            OLLAMA_TEXT_MIN_AVG_WORDS_PER_SEGMENT,
            OLLAMA_TEXT_MIN_WPS,
        )
    elif has_transcript:
        LOGGER.info("Ollama texte indisponible ou modele non trouve: analyse LLM desactivee")
    else:
        LOGGER.info("Ollama texte ignore: transcript vide")

    if OLLAMA_VISION_ENABLED and OLLAMA_VISION_GPU_HANDOFF and video_path is not None:
        _prepare_cuda_for_ollama_vision(
            reason="selection_before_vision",
            release_whisper=False,
            release_diarization=True,
        )

    ollama_vision_available = _ollama_check_vision_available() if video_path else False
    if ollama_vision_available:
        LOGGER.info(
            "Ollama vision active (max_clips=%d, low_text_only=%s, title_only=%s/deprecated, timeout=%.1fs, require_gpu=%s)",
            OLLAMA_VISION_MAX_CLIPS,
            OLLAMA_VISION_ONLY_LOW_TEXT,
            OLLAMA_VISION_TITLE_ONLY,
            OLLAMA_VISION_TIMEOUT,
            OLLAMA_VISION_REQUIRE_GPU,
        )
    elif video_path:
        LOGGER.info("Ollama vision desactivee ou modele non trouve")

    if ollama_text_available or ollama_vision_available:
        LOGGER.info(
            "  - Ollama pacing: chunk=%d, pause=%.2fs",
            OLLAMA_CHUNK_SIZE,
            OLLAMA_CHUNK_PAUSE_SECONDS,
        )

    vision_clip_budget = OLLAMA_VISION_MAX_CLIPS
    if ollama_vision_available and OLLAMA_VISION_ALL_CLIPS:
        vision_clip_budget = len(merged_candidates)
        LOGGER.info(
            "Ollama vision all-clips: %d/%d candidats",
            vision_clip_budget,
            len(merged_candidates),
        )
    elif ollama_vision_available and car_profile_active and not has_transcript:
        vision_clip_budget = max(
            OLLAMA_VISION_MAX_CLIPS,
            min(len(merged_candidates), OLLAMA_VISION_MAX_CLIPS * 3),
        )
        LOGGER.info(
            "Ollama vision budget boost (car low-text): %d/%d candidats",
            vision_clip_budget,
            len(merged_candidates),
        )

    ollama_calls = 0
    ollama_vision_calls = 0
    vision_timeout_streak = 0
    best_showcase_fallback: tuple[float, float, float, str, str, dict] | None = None
    best_transition_fallback: tuple[float, float, float, str, str, dict] | None = None
    best_transition_fallback_rank = -1.0
    best_transition_focus_seed: tuple[float, float, float, str, str, dict] | None = None
    best_transition_focus_seed_rank = -1.0
    best_transition_late_candidate: tuple[float, float, float, str, str, dict] | None = None
    best_transition_late_rank = -1.0
    best_launch_early_candidate: tuple[float, float, float, str, str, dict] | None = None
    best_launch_early_rank = -1.0
    best_launch_late_candidate: tuple[float, float, float, str, str, dict] | None = None
    best_launch_late_rank = -1.0
    best_insertion_candidate: tuple[float, float, float, str, str, dict] | None = None
    best_insertion_rank = -1.0
    launch_early_max_start = min(max(12.0, duration * 0.34), max(42.0, min_clip_length + 16.0))
    late_transition_min_start = max(24.0, duration * 0.44)
    late_transition_max_start = max(
        late_transition_min_start + min_clip_length * 0.45,
        duration - min_clip_length * 0.55,
    )
    insertion_min_start = max(6.0, duration * 0.04)
    insertion_max_start = max(
        insertion_min_start + min_clip_length * 0.50,
        duration * 0.58,
    )
    insertion_focus_max_len = max(min_clip_length + 10.0, min(40.0, max_clip_length * 0.70))
    total_candidates = len(merged_candidates)
    for candidate_idx, candidate in enumerate(merged_candidates, start=1):
        source = candidate["source"]
        
        # --- ÉTAPE 4.1: Déterminer les boundaries initiales ---
        if source == "audio_peak":
            # Candidat audio: expand arc autour du pic
            idx = candidate["audio_idx"]
            raw_start, raw_end = _expand_arc(series, values, idx, avg, duration)
            raw_start = max(0.0, raw_start - PRE_ROLL_SECONDS)
            raw_end = min(duration, raw_end + POST_ROLL_SECONDS)
            audio_features = dict(candidate.get("audio_features") or {})

            launch_score_near = 0.0
            launch_focus = False
            if car_profile_active:
                launch_score_near = max(
                    float(car_start_launch_by_idx.get(idx, 0.0)),
                    float(car_start_launch_by_idx.get(idx - 1, 0.0)),
                    float(car_start_launch_by_idx.get(idx + 1, 0.0)),
                )
                launch_focus = bool(
                    candidate.get("force_launch_candidate", False)
                    or audio_features.get("car_start_from_launch", False)
                    or launch_score_near >= max(CAR_EVENT_MIN_SCORE * 0.84, 0.46)
                )

            if launch_focus:
                launch_silence_start: float | None = None
                launch_silence_end: float | None = None
                for delta in (0, -1, 1, -2, 2):
                    probe_idx = idx + delta
                    if probe_idx in car_start_launch_silence_start_by_idx:
                        ts_start = float(car_start_launch_silence_start_by_idx[probe_idx])
                        if launch_silence_start is None or ts_start < launch_silence_start:
                            launch_silence_start = ts_start
                    if probe_idx in car_start_launch_silence_end_by_idx:
                        ts_end = float(car_start_launch_silence_end_by_idx[probe_idx])
                        if launch_silence_end is None or ts_end > launch_silence_end:
                            launch_silence_end = ts_end

                if launch_silence_start is not None:
                    raw_start = min(raw_start, max(0.0, launch_silence_start - 0.8))
                else:
                    raw_start = max(0.0, raw_start - max(4.8, PRE_ROLL_SECONDS * 2.4))

                if launch_silence_end is not None:
                    launch_tail = max(11.0, min_clip_length * 0.85)
                    raw_end = max(raw_end, min(duration, launch_silence_end + launch_tail))

                launch_target_len = max(min_clip_length, min(34.0, max_clip_length * 0.60))
                if (raw_end - raw_start) > (launch_target_len + 4.0):
                    raw_end = min(duration, raw_start + launch_target_len)
                if (raw_end - raw_start) < min_clip_length:
                    raw_end = min(duration, raw_start + min_clip_length)
                    raw_start = max(0.0, raw_end - min_clip_length)

                audio_features["car_transition_focus"] = True
                audio_features["car_launch_focus"] = True
                audio_features["car_start_event"] = True
                audio_features["car_start_from_launch"] = True
                audio_features["car_start_score"] = round(
                    max(
                        float(audio_features.get("car_start_score", 0.0)),
                        launch_score_near,
                        max(CAR_EVENT_MIN_SCORE * 0.84, 0.46),
                    ),
                    3,
                )
        else:
            # Candidat story: utilise les boundaries pré-calculées
            raw_start = candidate["start"]
            raw_end = candidate["end"]
            # Crée des audio_features basiques pour les candidats story
            center_idx = int(candidate["center"] / ANALYSIS_WINDOW_SECONDS)
            center_idx = max(0, min(center_idx, len(values) - 1))
            audio_features = _feature_bundle(values, center_idx, avg, deviation)
            audio_features["source"] = "story_window"
            audio_features["story_reason"] = candidate.get("story_reason", "")
            car_center = (
                max(
                    car_strength_by_idx.get(center_idx, 0.0),
                    car_strength_by_idx.get(center_idx - 1, 0.0),
                    car_strength_by_idx.get(center_idx + 1, 0.0),
                )
                if car_profile_active
                else 0.0
            )
            car_center_sustain = (
                max(
                    car_sustain_by_idx.get(center_idx, 0.0),
                    car_sustain_by_idx.get(center_idx - 1, 0.0),
                    car_sustain_by_idx.get(center_idx + 1, 0.0),
                )
                if car_profile_active
                else 0.0
            )
            car_start_center_audio = (
                max(
                    car_start_by_idx.get(center_idx, 0.0),
                    car_start_by_idx.get(center_idx - 1, 0.0),
                    car_start_by_idx.get(center_idx + 1, 0.0),
                )
                if car_profile_active
                else 0.0
            )
            car_stop_center_audio = (
                max(
                    car_stop_by_idx.get(center_idx, 0.0),
                    car_stop_by_idx.get(center_idx - 1, 0.0),
                    car_stop_by_idx.get(center_idx + 1, 0.0),
                )
                if car_profile_active
                else 0.0
            )
            car_start_center_yamnet = (
                max(
                    audio_event_start_by_idx.get(center_idx, 0.0),
                    audio_event_start_by_idx.get(center_idx - 1, 0.0),
                    audio_event_start_by_idx.get(center_idx + 1, 0.0),
                )
                if car_profile_active
                else 0.0
            )
            car_stop_center_yamnet = (
                max(
                    audio_event_stop_by_idx.get(center_idx, 0.0),
                    audio_event_stop_by_idx.get(center_idx - 1, 0.0),
                    audio_event_stop_by_idx.get(center_idx + 1, 0.0),
                )
                if car_profile_active
                else 0.0
            )
            visual_motion_center = max(
                visual_motion_by_idx.get(center_idx, 0.0),
                visual_motion_by_idx.get(center_idx - 1, 0.0),
                visual_motion_by_idx.get(center_idx + 1, 0.0),
            )
            car_object_center = max(
                car_object_presence_by_idx.get(center_idx, 0.0),
                car_object_presence_by_idx.get(center_idx - 1, 0.0),
                car_object_presence_by_idx.get(center_idx + 1, 0.0),
            )
            opensmile_voice_center = max(
                opensmile_voice_by_idx.get(center_idx, 0.0),
                opensmile_voice_by_idx.get(center_idx - 1, 0.0),
                opensmile_voice_by_idx.get(center_idx + 1, 0.0),
            )
            speech_context_center = max(
                speech_context_by_idx.get(center_idx, 0.0),
                speech_context_by_idx.get(center_idx - 1, 0.0),
                speech_context_by_idx.get(center_idx + 1, 0.0),
            )
            music_context_center = max(
                music_context_by_idx.get(center_idx, 0.0),
                music_context_by_idx.get(center_idx - 1, 0.0),
                music_context_by_idx.get(center_idx + 1, 0.0),
            )
            noise_context_center = max(
                noise_context_by_idx.get(center_idx, 0.0),
                noise_context_by_idx.get(center_idx - 1, 0.0),
                noise_context_by_idx.get(center_idx + 1, 0.0),
            )
            speech_music_mix_center = max(
                speech_music_mix_by_idx.get(center_idx, 0.0),
                speech_music_mix_by_idx.get(center_idx - 1, 0.0),
                speech_music_mix_by_idx.get(center_idx + 1, 0.0),
            )
            speaker_change_center = max(
                speaker_change_by_idx.get(center_idx, 0.0),
                speaker_change_by_idx.get(center_idx - 1, 0.0),
                speaker_change_by_idx.get(center_idx + 1, 0.0),
            )
            facial_emotion_center = max(
                facial_emotion_by_idx.get(center_idx, 0.0),
                facial_emotion_by_idx.get(center_idx - 1, 0.0),
                facial_emotion_by_idx.get(center_idx + 1, 0.0),
            )
            visual_start_center = (
                max(
                    visual_start_by_idx.get(center_idx, 0.0),
                    visual_start_by_idx.get(center_idx - 1, 0.0),
                    visual_start_by_idx.get(center_idx + 1, 0.0),
                )
                if car_profile_active
                else 0.0
            )
            visual_stop_center = (
                max(
                    visual_stop_by_idx.get(center_idx, 0.0),
                    visual_stop_by_idx.get(center_idx - 1, 0.0),
                    visual_stop_by_idx.get(center_idx + 1, 0.0),
                )
                if car_profile_active
                else 0.0
            )
            inferred_start_center = (
                max(
                    car_start_inferred_by_idx.get(center_idx, 0.0),
                    car_start_inferred_by_idx.get(center_idx - 1, 0.0),
                    car_start_inferred_by_idx.get(center_idx + 1, 0.0),
                )
                if car_profile_active
                else 0.0
            )
            scene_cut_start_center = (
                max(
                    car_start_scene_cut_by_idx.get(center_idx, 0.0),
                    car_start_scene_cut_by_idx.get(center_idx - 1, 0.0),
                    car_start_scene_cut_by_idx.get(center_idx + 1, 0.0),
                )
                if car_profile_active
                else 0.0
            )
            launch_start_center = (
                max(
                    car_start_launch_by_idx.get(center_idx, 0.0),
                    car_start_launch_by_idx.get(center_idx - 1, 0.0),
                    car_start_launch_by_idx.get(center_idx + 1, 0.0),
                )
                if car_profile_active
                else 0.0
            )
            car_start_center = max(
                car_start_center_audio,
                car_start_center_yamnet,
                visual_start_center,
                inferred_start_center,
                scene_cut_start_center,
                launch_start_center,
            )
            car_stop_center = max(car_stop_center_audio, car_stop_center_yamnet, visual_stop_center)
            audio_features["car_accel_score"] = round(car_center, 3)
            audio_features["car_peak"] = car_center > 0
            audio_features["car_sustain_seconds"] = round(car_center_sustain, 3)
            audio_features["car_sustained"] = car_center_sustain >= CAR_MIN_SUSTAIN_SECONDS
            audio_features["car_start_score"] = round(car_start_center, 3)
            audio_features["car_stop_score"] = round(car_stop_center, 3)
            audio_features["car_start_event"] = (
                car_start_center_audio >= CAR_EVENT_MIN_SCORE
                or car_start_center_yamnet >= AUDIO_EVENT_MIN_SCORE
                or visual_start_center >= VISUAL_EVENT_MIN_SCORE
                or inferred_start_center >= max(CAR_EVENT_MIN_SCORE * 0.90, 0.48)
                or scene_cut_start_center >= max(CAR_EVENT_MIN_SCORE * 0.82, 0.46)
                or launch_start_center >= max(CAR_EVENT_MIN_SCORE * 0.84, 0.46)
            )
            audio_features["car_stop_event"] = (
                car_stop_center_audio >= CAR_EVENT_MIN_SCORE
                or car_stop_center_yamnet >= AUDIO_EVENT_MIN_SCORE
                or visual_stop_center >= VISUAL_EVENT_MIN_SCORE
            )
            audio_features["car_start_from_audio"] = car_start_center_audio >= CAR_EVENT_MIN_SCORE
            audio_features["car_stop_from_audio"] = car_stop_center_audio >= CAR_EVENT_MIN_SCORE
            audio_features["car_start_from_yamnet"] = car_start_center_yamnet >= AUDIO_EVENT_MIN_SCORE
            audio_features["car_stop_from_yamnet"] = car_stop_center_yamnet >= AUDIO_EVENT_MIN_SCORE
            audio_features["car_start_from_visual"] = visual_start_center >= VISUAL_EVENT_MIN_SCORE
            audio_features["car_stop_from_visual"] = visual_stop_center >= VISUAL_EVENT_MIN_SCORE
            audio_features["car_start_from_inferred"] = (
                inferred_start_center >= max(CAR_EVENT_MIN_SCORE * 0.90, 0.48)
            )
            audio_features["car_start_from_scene_cut"] = (
                scene_cut_start_center >= max(CAR_EVENT_MIN_SCORE * 0.82, 0.46)
            )
            audio_features["car_start_from_launch"] = (
                launch_start_center >= max(CAR_EVENT_MIN_SCORE * 0.84, 0.46)
            )
            audio_features["visual_motion_score"] = round(visual_motion_center, 3)
            audio_features["visual_motion_event"] = visual_motion_center >= VISUAL_EVENT_MIN_SCORE
            audio_features["car_object_score"] = round(car_object_center, 3)
            audio_features["car_object_event"] = car_object_center >= OBJECT_CAR_MIN_SCORE
            audio_features["opensmile_voice_score"] = round(opensmile_voice_center, 3)
            audio_features["opensmile_voice_event"] = (
                opensmile_voice_center >= OPENSMILE_EVENT_MIN_SCORE
            )
            audio_features["speech_context_ratio"] = round(speech_context_center, 3)
            audio_features["music_context_ratio"] = round(music_context_center, 3)
            audio_features["noise_context_ratio"] = round(noise_context_center, 3)
            audio_features["speech_music_mix_score"] = round(speech_music_mix_center, 3)
            audio_features["speaker_change_score"] = round(speaker_change_center, 3)
            audio_features["speaker_change_event"] = speaker_change_center >= 0.5
            audio_features["facial_emotion_score"] = round(facial_emotion_center, 3)
            audio_features["facial_emotion_event"] = (
                facial_emotion_center >= FACIAL_EMOTION_EVENT_MIN_SCORE
            )

        if "onset_strength" not in audio_features:
            audio_features["onset_strength"] = 0.0
            audio_features["onset_peak"] = False
        if "car_accel_score" not in audio_features:
            audio_features["car_accel_score"] = 0.0
            audio_features["car_peak"] = False
        if "car_sustain_seconds" not in audio_features:
            audio_features["car_sustain_seconds"] = 0.0
            audio_features["car_sustained"] = False
        if "car_start_score" not in audio_features:
            audio_features["car_start_score"] = 0.0
            audio_features["car_start_event"] = False
            audio_features["car_start_from_audio"] = False
            audio_features["car_start_from_yamnet"] = False
            audio_features["car_start_from_visual"] = False
            audio_features["car_start_from_inferred"] = False
            audio_features["car_start_from_scene_cut"] = False
            audio_features["car_start_from_launch"] = False
        if "car_stop_score" not in audio_features:
            audio_features["car_stop_score"] = 0.0
            audio_features["car_stop_event"] = False
            audio_features["car_stop_from_audio"] = False
            audio_features["car_stop_from_yamnet"] = False
            audio_features["car_stop_from_visual"] = False
        if "visual_motion_score" not in audio_features:
            audio_features["visual_motion_score"] = 0.0
            audio_features["visual_motion_event"] = False
        if "car_object_score" not in audio_features:
            audio_features["car_object_score"] = 0.0
            audio_features["car_object_event"] = False
        if "opensmile_voice_score" not in audio_features:
            audio_features["opensmile_voice_score"] = 0.0
            audio_features["opensmile_voice_event"] = False
        if "speech_context_ratio" not in audio_features:
            audio_features["speech_context_ratio"] = 0.0
        if "music_context_ratio" not in audio_features:
            audio_features["music_context_ratio"] = 0.0
        if "noise_context_ratio" not in audio_features:
            audio_features["noise_context_ratio"] = 0.0
        if "speech_music_mix_score" not in audio_features:
            audio_features["speech_music_mix_score"] = 0.0
        if "speaker_change_score" not in audio_features:
            audio_features["speaker_change_score"] = 0.0
            audio_features["speaker_change_event"] = False
        if "facial_emotion_score" not in audio_features:
            audio_features["facial_emotion_score"] = 0.0
            audio_features["facial_emotion_event"] = False
        if "car_showcase_event" not in audio_features:
            audio_features["car_showcase_event"] = False
        if "car_visual_walkaround_silent_event" not in audio_features:
            audio_features["car_visual_walkaround_silent_event"] = False
        if "car_stationary_showcase_event" not in audio_features:
            audio_features["car_stationary_showcase_event"] = False
        if "car_insertion_focus" not in audio_features:
            audio_features["car_insertion_focus"] = False
            audio_features["car_insertion_focus_score"] = 0.0
            audio_features["car_insertion_pre_motion"] = 0.0
            audio_features["car_insertion_rms_jump"] = 0.0


        
        # --- ÉTAPE 4.2: SINGLE-PASS BOUNDARY REFINEMENT ---
        start, end, boundary_metadata = _refine_boundaries_single_pass(
            start=raw_start,
            end=raw_end,
            signals=all_cut_signals,
            duration=duration,
            audio_path=audio_path,
            pitch_series=pitch_series,
            transcript_segments=transcript_segments,
            min_clip_length=min_clip_length,
            max_clip_length=max_clip_length,
        )
        
        # --- ÉTAPE 4.3: Analyse du contenu ---
        text_features = _text_features_for_range(start, end, transcript_segments)
        
        # Ajoute les métadonnées du boundary refinement
        audio_features["boundary_start_score"] = boundary_metadata.get("start_score", 0)
        audio_features["boundary_end_score"] = boundary_metadata.get("end_score", 0)
        audio_features["boundary_adjustments"] = boundary_metadata.get("adjustments", [])
        audio_features["candidate_source"] = source
        
        # --- ÉTAPE 4.4: Filtrage contenu commercial ---
        if text_features.get("is_commercial", False):
            commercial_penalty = text_features.get("commercial_penalty", 0.0)
            if REJECT_COMMERCIAL_CLIPS:
                LOGGER.info(
                    "Segment skipped (commercial hard-block penalty=%.2f): %.1f-%.1f",
                    commercial_penalty,
                    start,
                    end,
                )
                continue
            if commercial_penalty >= 0.3:
                if not ALLOW_LOW_SCORE_CLIPS:
                    LOGGER.info("Segment skipped (commercial penalty=%.2f): %.1f-%.1f", commercial_penalty, start, end)
                    continue
                LOGGER.info(
                    "Segment kept despite commercial penalty because ALLOW_LOW_SCORE_CLIPS=true (penalty=%.2f): %.1f-%.1f",
                    commercial_penalty,
                    start,
                    end,
                )
        
        # --- ÉTAPE 4.5: Analyse Ollama (optionnel) ---
        ollama_analysis = {
            "ollama_used": False,
            "cut_quality": 0.7,
            "viral_potential": 0.5,
            "is_complete": True,
            "suggested_action": "keep",
            "reason": "",
        }
        vision_analysis = {
            "vision_used": False,
            "scene_type": "unknown",
            "action_level": 0.5,
            "clip_quality": 0.5,
            "audio_visual_fit": 0.5,
            "is_car_showcase": False,
            "title_hint": "",
            "frame_count": 0,
            "reason": "",
        }
        clip_text = ""
        context_before = ""
        context_after = ""
        if has_transcript:
            clip_text = " ".join(
                seg["text"] for seg in transcript_segments
                if seg["end"] >= start and seg["start"] <= end
            )
            context_before = " ".join(
                seg["text"] for seg in transcript_segments
                if seg["end"] < start and seg["end"] >= start - 15.0
            )
            context_after = " ".join(
                seg["text"] for seg in transcript_segments
                if seg["start"] > end and seg["start"] <= end + 10.0
            )
        clip_text = clip_text.strip()
        context_before = context_before.strip()
        context_after = context_after.strip()
        clip_has_text = bool(clip_text)

        ollama_trim_applied = False
        if ollama_text_available and ollama_text_eligible:
            if clip_has_text:
                ollama_analysis = _ollama_analyze_clip_advanced(
                    clip_text, 
                    context_before=context_before,
                    context_after=context_after
                )
                ollama_calls += 1
                if (
                    OLLAMA_CHUNK_PAUSE_SECONDS > 0
                    and OLLAMA_CHUNK_SIZE > 0
                    and (ollama_calls % OLLAMA_CHUNK_SIZE) == 0
                    and candidate_idx < total_candidates
                ):
                    LOGGER.info(
                        "Ollama pacing: %d analyses traitées, pause %.2fs",
                        ollama_calls,
                        OLLAMA_CHUNK_PAUSE_SECONDS,
                    )
                    time.sleep(OLLAMA_CHUNK_PAUSE_SECONDS)
            else:
                LOGGER.debug(
                    "Ollama texte ignore pour %.1f-%.1f: pas de texte dans le clip",
                    start,
                    end,
                )

        run_vision = (
            ollama_vision_available
            and video_path is not None
            and ollama_vision_calls < vision_clip_budget
        )
        if run_vision and OLLAMA_VISION_ONLY_LOW_TEXT and (not OLLAMA_VISION_ALL_CLIPS):
            run_vision = (
                (not has_transcript)
                or car_profile_active
                or float(text_features.get("words_per_sec", 0.0)) < (CAR_LOW_DIALOGUE_WPS * 1.20)
                or float(text_features.get("text_score", 0.0)) < 0.56
            )

        if run_vision and video_path is not None:
            audio_hint = (
                f"profile={profile}; "
                f"base_audio={float(audio_features.get('score', 0.0)):.2f}; "
                f"onset={float(audio_features.get('onset_strength', 0.0)):.2f}; "
                f"car_accel={float(audio_features.get('car_accel_score', 0.0)):.2f}; "
                f"car_start={bool(audio_features.get('car_start_event', False))}; "
                f"car_stop={bool(audio_features.get('car_stop_event', False))}; "
                f"visual_motion={float(audio_features.get('visual_motion_score', 0.0)):.2f}; "
                f"speech_ratio={float(audio_features.get('speech_context_ratio', 0.0)):.2f}; "
                f"voice_dyn={float(audio_features.get('opensmile_voice_score', 0.0)):.2f}; "
                f"speaker_change={bool(audio_features.get('speaker_change_event', False))}; "
                f"transcript_present={has_transcript}"
            )
            vision_analysis = _ollama_vision_analyze_clip(
                video_path=video_path,
                start=start,
                end=end,
                clip_text=clip_text,
                audio_hint=audio_hint,
                profile_hint=profile,
                tag_hint=str(text_features.get("text_tag", "") or ""),
            )
            if vision_analysis.get("vision_used"):
                vision_timeout_streak = 0
                ollama_vision_calls += 1
                ollama_calls += 1
                LOGGER.info(
                    "Ollama vision clip %.1f-%.1f: scene=%s quality=%.2f action=%.2f av_fit=%.2f showcase=%s frames=%d",
                    start,
                    end,
                    str(vision_analysis.get("scene_type", "unknown")),
                    float(vision_analysis.get("clip_quality", 0.5)),
                    float(vision_analysis.get("action_level", 0.5)),
                    float(vision_analysis.get("audio_visual_fit", 0.5)),
                    bool(vision_analysis.get("is_car_showcase", False)),
                    int(vision_analysis.get("frame_count", 0) or 0),
                )
                if (
                    OLLAMA_CHUNK_PAUSE_SECONDS > 0
                    and OLLAMA_CHUNK_SIZE > 0
                    and (ollama_calls % OLLAMA_CHUNK_SIZE) == 0
                    and candidate_idx < total_candidates
                ):
                    LOGGER.info(
                        "Ollama pacing: %d analyses traitees, pause %.2fs",
                        ollama_calls,
                        OLLAMA_CHUNK_PAUSE_SECONDS,
                    )
                    time.sleep(OLLAMA_CHUNK_PAUSE_SECONDS)
            else:
                vision_reason = str(vision_analysis.get("reason", "")).strip().lower()
                if "timeout" in vision_reason:
                    vision_timeout_streak += 1
                    if vision_timeout_streak >= OLLAMA_VISION_TIMEOUT_STREAK_LIMIT:
                        ollama_vision_available = False
                        LOGGER.warning(
                            "Ollama vision desactivee pour ce job: %d timeouts consecutifs",
                            vision_timeout_streak,
                        )
                elif "gpu_unavailable" in vision_reason:
                    ollama_vision_available = False
                    LOGGER.warning(
                        "Ollama vision desactivee pour ce job: GPU indisponible (mode require_gpu actif)"
                    )
                elif vision_reason:
                    vision_timeout_streak = 0

        ollama_action = str(ollama_analysis.get("suggested_action", "keep")).strip().lower()
        if ollama_analysis.get("ollama_used"):
            if OLLAMA_HARD_REJECT and ollama_action == "drop":
                LOGGER.info(
                    "Segment skipped (Ollama hard reject): %.1f-%.1f reason=%s",
                    start,
                    end,
                    str(ollama_analysis.get("reason", ""))[:80],
                )
                continue
            if OLLAMA_APPLY_TRIM_HINTS and ollama_action in {"trim_start", "trim_end"}:
                t_start, t_end, trimmed, trim_label = _apply_ollama_trim_hint(
                    ollama_action,
                    start,
                    end,
                    transcript_segments,
                    min_clip_length,
                    OLLAMA_TRIM_MAX_SHIFT_SECONDS,
                )
                if trimmed:
                    ollama_trim_applied = True
                    LOGGER.info(
                        "Ollama %s applied: %.1f-%.1f -> %.1f-%.1f",
                        ollama_action,
                        start,
                        end,
                        t_start,
                        t_end,
                    )
                    start, end = t_start, t_end
                    boundary_adjustments = list(boundary_metadata.get("adjustments", []))
                    boundary_adjustments.append(trim_label)
                    boundary_metadata["adjustments"] = boundary_adjustments
                    if ollama_action == "trim_end":
                        boundary_metadata["end_score"] = max(
                            0.62, float(boundary_metadata.get("end_score", 0.5))
                        )
                    else:
                        boundary_metadata["start_score"] = max(
                            0.62, float(boundary_metadata.get("start_score", 0.5))
                        )
                    # Recompute text features on adjusted boundaries.
                    text_features = _text_features_for_range(start, end, transcript_segments)
                    if REJECT_COMMERCIAL_CLIPS and text_features.get("is_commercial", False):
                        LOGGER.info(
                            "Segment skipped after Ollama trim (commercial hard-block): %.1f-%.1f",
                            start,
                            end,
                        )
                        continue
                    # Refresh boundary metadata mirrored in audio features.
                    audio_features["boundary_start_score"] = boundary_metadata.get("start_score", 0)
                    audio_features["boundary_end_score"] = boundary_metadata.get("end_score", 0)
                    audio_features["boundary_adjustments"] = boundary_metadata.get("adjustments", [])
        
        clip_text_for_car_hint = clip_text
        if has_transcript:
            clip_text_for_car_hint = " ".join(
                seg["text"]
                for seg in transcript_segments
                if seg["end"] >= start and seg["start"] <= end
            ).strip()
        car_exterior_tour_text_hint = bool(
            car_profile_active
            and _has_car_exterior_tour_text_hint(clip_text_for_car_hint)
        )

        # --- ÉTAPE 4.6: Calcul du score final ---
        base_audio_score = audio_features["score"]
        audio_score = base_audio_score
        onset_strength = audio_features.get("onset_strength", 0.0)
        opensmile_voice_score = float(audio_features.get("opensmile_voice_score", 0.0))
        car_accel_score = audio_features.get("car_accel_score", 0.0)
        car_sustain_seconds = audio_features.get("car_sustain_seconds", 0.0)
        car_start_score = float(audio_features.get("car_start_score", 0.0))
        car_stop_score = float(audio_features.get("car_stop_score", 0.0))
        visual_motion_score = float(audio_features.get("visual_motion_score", 0.0))
        car_object_score = float(audio_features.get("car_object_score", 0.0))
        visual_motion_event = bool(
            audio_features.get("visual_motion_event", False)
            or visual_motion_score >= VISUAL_EVENT_MIN_SCORE
        )
        car_object_event = bool(
            audio_features.get("car_object_event", False)
            or car_object_score >= OBJECT_CAR_MIN_SCORE
        )
        facial_emotion_score = float(audio_features.get("facial_emotion_score", 0.0))
        facial_emotion_event = bool(
            audio_features.get("facial_emotion_event", False)
            or facial_emotion_score >= FACIAL_EMOTION_EVENT_MIN_SCORE
        )
        speech_context_ratio = float(audio_features.get("speech_context_ratio", 0.0))
        music_context_ratio = float(audio_features.get("music_context_ratio", 0.0))
        noise_context_ratio = float(audio_features.get("noise_context_ratio", 0.0))
        speech_music_mix_score = float(audio_features.get("speech_music_mix_score", 0.0))
        speaker_change_score = float(audio_features.get("speaker_change_score", 0.0))
        opensmile_voice_event = bool(
            audio_features.get("opensmile_voice_event", False)
            or opensmile_voice_score >= OPENSMILE_EVENT_MIN_SCORE
        )
        speaker_change_event = bool(
            audio_features.get("speaker_change_event", False)
            or speaker_change_score >= 0.5
        )
        car_showcase_event = bool(audio_features.get("car_showcase_event", False))
        car_stationary_showcase_event = bool(
            audio_features.get("car_stationary_showcase_event", False)
        )
        presentation_like = car_showcase_event or car_stationary_showcase_event
        speech_context_event = speech_context_ratio >= AUDIO_CONTEXT_SPEECH_MIN_RATIO
        music_context_event = music_context_ratio >= AUDIO_CONTEXT_MUSIC_MIN_RATIO
        noise_context_event = noise_context_ratio >= AUDIO_CONTEXT_NOISE_MIN_RATIO
        speech_music_mix_event = (
            speech_music_mix_score > 0
            or (speech_context_event and music_context_event)
        )
        music_only_context = (
            music_context_event
            and speech_context_ratio < AUDIO_CONTEXT_SPEECH_MIN_RATIO * 0.60
            and noise_context_ratio < AUDIO_CONTEXT_NOISE_MIN_RATIO * 0.70
        )
        noise_only_context = (
            noise_context_event
            and speech_context_ratio < AUDIO_CONTEXT_SPEECH_MIN_RATIO * 0.60
            and music_context_ratio < AUDIO_CONTEXT_MUSIC_MIN_RATIO * 0.70
        )
        car_start_from_audio = bool(audio_features.get("car_start_from_audio", False))
        car_stop_from_audio = bool(audio_features.get("car_stop_from_audio", False))
        car_start_from_yamnet = bool(audio_features.get("car_start_from_yamnet", False))
        car_stop_from_yamnet = bool(audio_features.get("car_stop_from_yamnet", False))
        car_start_from_visual = bool(audio_features.get("car_start_from_visual", False))
        car_stop_from_visual = bool(audio_features.get("car_stop_from_visual", False))
        car_start_from_inferred = bool(audio_features.get("car_start_from_inferred", False))
        car_start_from_scene_cut = bool(audio_features.get("car_start_from_scene_cut", False))
        car_start_from_launch = bool(audio_features.get("car_start_from_launch", False))

        start_idx = int(round(start / ANALYSIS_WINDOW_SECONDS))
        end_idx = int(round(end / ANALYSIS_WINDOW_SECONDS))
        start_left = max(2, int(round(3.0 / ANALYSIS_WINDOW_SECONDS)))
        start_right = max(1, int(round(2.0 / ANALYSIS_WINDOW_SECONDS)))
        stop_left = max(2, int(round(3.0 / ANALYSIS_WINDOW_SECONDS)))
        stop_right = max(1, int(round(1.5 / ANALYSIS_WINDOW_SECONDS)))

        def _max_event_window(source: dict[int, float], center_idx: int, left: int, right: int) -> float:
            best = 0.0
            for idx in range(center_idx - left, center_idx + right + 1):
                best = max(best, float(source.get(idx, 0.0)))
            return best

        def _max_event_range(source: dict[int, float], idx_from: int, idx_to: int) -> float:
            if idx_to < idx_from:
                return 0.0
            lo = max(0, idx_from)
            hi = min(len(values) - 1, idx_to)
            if hi < lo:
                return 0.0
            best = 0.0
            for idx in range(lo, hi + 1):
                best = max(best, float(source.get(idx, 0.0)))
            return best

        def _max_series_range(series_values: list[float], idx_from: int, idx_to: int) -> float:
            if idx_to < idx_from:
                return 0.0
            lo = max(0, idx_from)
            hi = min(len(series_values) - 1, idx_to)
            if hi < lo:
                return 0.0
            best = 0.0
            for idx in range(lo, hi + 1):
                best = max(best, float(series_values[idx]))
            return best

        start_audio_near = _max_event_window(car_start_by_idx, start_idx, start_left, start_right)
        start_yamnet_near = _max_event_window(audio_event_start_by_idx, start_idx, start_left, start_right)
        start_visual_near = _max_event_window(visual_start_by_idx, start_idx, start_left, start_right)
        start_inferred_near = _max_event_window(
            car_start_inferred_by_idx,
            start_idx,
            start_left,
            start_right,
        )
        start_scene_cut_near = _max_event_window(
            car_start_scene_cut_by_idx,
            start_idx,
            start_left,
            start_right,
        )
        start_launch_near = _max_event_window(
            car_start_launch_by_idx,
            start_idx,
            start_left,
            start_right,
        )
        stop_audio_near = _max_event_window(car_stop_by_idx, end_idx, stop_left, stop_right)
        stop_yamnet_near = _max_event_window(audio_event_stop_by_idx, end_idx, stop_left, stop_right)
        stop_visual_near = _max_event_window(visual_stop_by_idx, end_idx, stop_left, stop_right)
        object_near = _max_event_range(
            car_object_presence_by_idx,
            start_idx - start_left,
            end_idx + stop_right,
        )

        car_start_from_audio = car_start_from_audio or start_audio_near >= max(CAR_EVENT_MIN_SCORE * 0.90, 0.46)
        car_start_from_yamnet = car_start_from_yamnet or start_yamnet_near >= max(AUDIO_EVENT_MIN_SCORE * 0.72, 0.24)
        car_start_from_visual = car_start_from_visual or start_visual_near >= max(VISUAL_EVENT_MIN_SCORE * 0.72, 0.30)
        car_start_from_inferred = car_start_from_inferred or start_inferred_near >= max(CAR_EVENT_MIN_SCORE * 0.90, 0.48)
        car_start_from_scene_cut = car_start_from_scene_cut or start_scene_cut_near >= max(CAR_EVENT_MIN_SCORE * 0.82, 0.46)
        car_start_from_launch = car_start_from_launch or start_launch_near >= max(CAR_EVENT_MIN_SCORE * 0.84, 0.46)
        car_stop_from_audio = car_stop_from_audio or stop_audio_near >= max(CAR_EVENT_MIN_SCORE * 0.85, 0.44)
        car_stop_from_yamnet = car_stop_from_yamnet or stop_yamnet_near >= max(AUDIO_EVENT_MIN_SCORE * 0.70, 0.22)
        car_stop_from_visual = car_stop_from_visual or stop_visual_near >= max(VISUAL_EVENT_MIN_SCORE * 0.70, 0.30)

        car_start_score = max(
            car_start_score,
            start_audio_near,
            start_yamnet_near,
            start_visual_near,
            start_inferred_near,
            start_scene_cut_near,
            start_launch_near,
        )
        car_stop_score = max(
            car_stop_score,
            stop_audio_near,
            stop_yamnet_near,
            stop_visual_near,
        )
        car_object_score = max(car_object_score, object_near)
        car_object_event = car_object_score >= OBJECT_CAR_MIN_SCORE
        car_start_event = bool(
            audio_features.get("car_start_event", False)
            or car_start_from_audio
            or car_start_from_yamnet
            or car_start_from_visual
            or car_start_from_inferred
            or car_start_from_scene_cut
            or car_start_from_launch
        )
        car_stop_event = bool(
            audio_features.get("car_stop_event", False)
            or car_stop_from_audio
            or car_stop_from_yamnet
            or car_stop_from_visual
        )
        visual_walkaround_silent_event = bool(
            car_profile_active
            and speech_context_ratio <= AUDIO_CONTEXT_SPEECH_MIN_RATIO * 0.60
            and not opensmile_voice_event
            and not speaker_change_event
            and visual_motion_score >= max(0.26, VISUAL_EVENT_MIN_SCORE * 0.60)
            and visual_motion_score <= max(0.60, VISUAL_EVENT_MIN_SCORE * 1.22)
            and (
                (not object_signal_available)
                or car_object_score >= max(OBJECT_CAR_MIN_SCORE * 0.82, 0.28)
            )
            and car_accel_score <= max(0.50, CAR_ACCEL_THRESHOLD * 0.80)
            and not car_start_event
            and not car_stop_event
        )
        car_stationary_showcase_event = bool(
            car_profile_active
            and object_signal_available
            and car_object_score >= max(OBJECT_CAR_MIN_SCORE * 1.12, 0.46)
            and visual_motion_score <= max(0.34, VISUAL_EVENT_MIN_SCORE * 0.78)
            and car_accel_score <= max(0.34, CAR_ACCEL_THRESHOLD * 0.52)
            and not car_start_event
            and not car_stop_event
        )
        insertion_pre_left = max(3, int(round(5.0 / ANALYSIS_WINDOW_SECONDS)))
        insertion_pre_right = max(1, int(round(1.0 / ANALYSIS_WINDOW_SECONDS)))
        insertion_post_right = max(2, int(round(2.6 / ANALYSIS_WINDOW_SECONDS)))
        insertion_pre_motion = (
            _max_event_range(
                visual_motion_by_idx,
                start_idx - insertion_pre_left,
                start_idx - insertion_pre_right,
            )
            if car_profile_active
            else 0.0
        )
        insertion_pre_car = (
            _max_event_range(
                car_strength_by_idx,
                start_idx - insertion_pre_left,
                start_idx - insertion_pre_right,
            )
            if car_profile_active
            else 0.0
        )
        insertion_post_car = (
            _max_event_range(car_strength_by_idx, start_idx, start_idx + insertion_post_right)
            if car_profile_active
            else 0.0
        )
        insertion_post_onset = (
            _max_event_range(onset_strength_by_idx, start_idx, start_idx + insertion_post_right)
            if car_profile_active
            else 0.0
        )
        insertion_pre_rms = (
            _max_series_range(values, start_idx - insertion_pre_left, start_idx - insertion_pre_right)
            if car_profile_active
            else 0.0
        )
        insertion_post_rms = (
            _max_series_range(values, start_idx, start_idx + insertion_post_right)
            if car_profile_active
            else 0.0
        )
        insertion_rms_jump = max(0.0, insertion_post_rms - insertion_pre_rms)
        insertion_focus_score = 0.0
        if car_profile_active:
            if insertion_pre_motion >= max(0.34, VISUAL_EVENT_MIN_SCORE * 0.75):
                insertion_focus_score += 0.34
            if insertion_pre_car >= max(0.18, CAR_ACCEL_THRESHOLD * 0.30):
                insertion_focus_score += 0.14
            if insertion_post_car >= max(0.30, CAR_ACCEL_THRESHOLD * 0.52):
                insertion_focus_score += 0.22
            if insertion_post_onset >= 0.50:
                insertion_focus_score += 0.14
            if start_scene_cut_near >= max(CAR_EVENT_MIN_SCORE * 0.82, 0.46):
                insertion_focus_score += 0.12
            if start_inferred_near >= max(CAR_EVENT_MIN_SCORE * 0.90, 0.48):
                insertion_focus_score += 0.08
            if insertion_rms_jump >= max(0.06, CAR_EVENT_MIN_DELTA * 0.50):
                insertion_focus_score += 0.12
            if car_start_from_launch:
                insertion_focus_score -= 0.28
            if start <= max(6.0, duration * 0.04):
                insertion_focus_score -= 0.12
        insertion_focus_score = max(0.0, min(1.0, insertion_focus_score))
        car_insertion_focus = bool(
            car_profile_active
            and not car_start_from_launch
            and insertion_min_start <= start <= insertion_max_start
            and insertion_focus_score >= 0.54
        )
        car_is_sustained = (
            audio_features.get("car_sustained", False)
            or car_sustain_seconds >= CAR_MIN_SUSTAIN_SECONDS
        )
        strong_car_signal = car_accel_score >= CAR_ACCEL_THRESHOLD and car_is_sustained
        vision_used = bool(vision_analysis.get("vision_used", False))
        vision_scene_type = str(vision_analysis.get("scene_type", "unknown")).strip().lower()
        vision_action_level = max(0.0, min(1.0, float(vision_analysis.get("action_level", 0.5))))
        vision_clip_quality = max(0.0, min(1.0, float(vision_analysis.get("clip_quality", 0.5))))
        vision_audio_visual_fit = max(
            0.0,
            min(1.0, float(vision_analysis.get("audio_visual_fit", 0.5))),
        )
        vision_is_showcase = bool(vision_analysis.get("is_car_showcase", False))
        vision_title_hint = str(vision_analysis.get("title_hint", "")).strip()
        vision_scoring_enabled = bool(vision_used)
        if (
            vision_scoring_enabled
            and car_profile_active
            and not vision_is_showcase
            and vision_scene_type in {"showcase", "interior"}
            and vision_clip_quality >= 0.55
        ):
            vision_is_showcase = True
        car_showcase_event = car_showcase_event or _is_car_showcase_event(
            car_profile_active=car_profile_active,
            visual_motion_score=visual_motion_score,
            visual_motion_event=visual_motion_event,
            speech_context_ratio=speech_context_ratio,
            speech_context_event=speech_context_event,
            opensmile_voice_event=opensmile_voice_event,
            speaker_change_event=speaker_change_event,
            strong_car_signal=strong_car_signal,
            car_start_event=car_start_event,
            car_stop_event=car_stop_event,
            car_accel_score=car_accel_score,
            car_object_score=car_object_score,
            exterior_tour_text_hint=car_exterior_tour_text_hint,
        )
        if visual_walkaround_silent_event:
            car_showcase_event = True
        if car_stationary_showcase_event:
            car_showcase_event = True
        if vision_scoring_enabled and vision_is_showcase and car_profile_active:
            car_showcase_event = True
        if car_showcase_event and car_insertion_focus:
            insertion_focus_score = max(0.0, insertion_focus_score - 0.10)
            car_insertion_focus = insertion_focus_score >= 0.56
        if not car_profile_active:
            car_accel_score = 0.0
            car_sustain_seconds = 0.0
            car_start_score = 0.0
            car_stop_score = 0.0
            car_start_from_audio = False
            car_stop_from_audio = False
            car_start_from_yamnet = False
            car_stop_from_yamnet = False
            car_start_from_visual = False
            car_stop_from_visual = False
            car_start_event = False
            car_stop_event = False
            car_is_sustained = False
            strong_car_signal = False
            car_showcase_event = False
            car_object_score = 0.0
            car_object_event = False
            visual_walkaround_silent_event = False
            car_stationary_showcase_event = False
            insertion_pre_motion = 0.0
            insertion_pre_car = 0.0
            insertion_post_car = 0.0
            insertion_post_onset = 0.0
            insertion_pre_rms = 0.0
            insertion_post_rms = 0.0
            insertion_rms_jump = 0.0
            insertion_focus_score = 0.0
            car_insertion_focus = False
        if onset_strength >= 0.6:
            audio_score = min(1.0, audio_score + 0.05)
        if strong_car_signal:
            audio_score = min(1.0, audio_score + 0.07)
        if car_start_event:
            audio_score = min(1.0, audio_score + 0.05)
        if car_start_from_launch:
            audio_score = min(1.0, audio_score + 0.04)
        if car_insertion_focus:
            audio_score = min(1.0, audio_score + 0.05)
        if car_stop_event:
            audio_score = min(1.0, audio_score + 0.04)
        if visual_motion_event:
            audio_score = min(1.0, audio_score + 0.04)
        if car_object_event:
            audio_score = min(1.0, audio_score + 0.03)
        if visual_walkaround_silent_event:
            audio_score = min(1.0, audio_score + 0.03)
        if car_stationary_showcase_event:
            audio_score = min(1.0, audio_score + 0.04)
        if facial_emotion_event:
            audio_score = min(1.0, audio_score + 0.05)
        if opensmile_voice_event:
            audio_score = min(
                1.0,
                audio_score + (0.05 if speech_context_event else 0.03),
            )
        if speaker_change_event:
            audio_score = min(1.0, audio_score + 0.03)
        if speech_music_mix_event and (
            onset_strength >= 0.45
            or visual_motion_event
            or facial_emotion_event
        ):
            audio_score = min(1.0, audio_score + 0.03)
        if music_only_context and onset_strength < 0.35 and not visual_motion_event:
            audio_score = max(0.0, audio_score - 0.03)
        if noise_only_context and onset_strength < 0.35 and not visual_motion_event:
            audio_score = max(0.0, audio_score - 0.04)
        text_score = text_features["text_score"]
        story_score = text_features.get("story_score", 0.3)
        # Éléments de qualité (issus des features texte)
        has_hook = text_features.get("has_hook", False)
        has_punchline = text_features.get("has_punchline", False)
        has_intensifiers = text_features.get("intensifier_hits", 0)
        has_dialogue = text_features.get("dialogue_hits", 0)
        has_laughter = text_features.get("has_laughter", False)
        has_story_start = text_features.get("has_story_start", False)
        has_story_end = text_features.get("has_story_end", False)
        presentation_like = car_showcase_event or car_stationary_showcase_event or car_exterior_tour_text_hint or visual_walkaround_silent_event or (
            _is_car_showcase_event(
                car_profile_active=car_profile_active,
                visual_motion_score=visual_motion_score,
                visual_motion_event=visual_motion_event,
                speech_context_ratio=speech_context_ratio,
                speech_context_event=speech_context_event,
                opensmile_voice_event=opensmile_voice_event,
                speaker_change_event=speaker_change_event,
                strong_car_signal=strong_car_signal,
                car_start_event=car_start_event,
                car_stop_event=car_stop_event,
                car_accel_score=car_accel_score,
                car_object_score=car_object_score,
                exterior_tour_text_hint=car_exterior_tour_text_hint,
            )
            and (
                speech_context_event
                or opensmile_voice_event
                or has_dialogue >= 1
                or (
                    car_profile_active
                    and (
                        (not has_transcript)
                        or float(text_features.get("words_per_sec", 0.0))
                        < (CAR_LOW_DIALOGUE_WPS * 1.15)
                    )
                    and (
                        visual_motion_event
                        or car_object_event
                        or strong_car_signal
                        or car_start_event
                        or car_stop_event
                    )
                )
            )
        )
        car_showcase_event = presentation_like

        # Score de qualité des boundaries (nouveau!)
        boundary_score = (boundary_metadata.get("start_score", 0.5) + boundary_metadata.get("end_score", 0.5)) / 2
        clip_length = max(0.0, end - start)
        variation_delta = 0.0
        low_dialogue_content = False
        non_dialogue_legit = False
        dialogue_expected = False

        # Pondération adaptative selon la dispo des signaux
        components: dict[str, float] = {"audio": audio_score}
        if has_transcript:
            components["text"] = text_score
            components["story"] = story_score
        if all_cut_signals:
            components["boundary"] = boundary_score
        if opensmile_voice_event or opensmile_voice_score > 0:
            components["voice"] = opensmile_voice_score
        if speech_context_event or music_context_event or noise_context_event:
            context_quality = min(
                1.0,
                speech_context_ratio * 0.55
                + speech_music_mix_score * 0.30
                + (1.0 - noise_context_ratio) * 0.15,
            )
            components["context"] = context_quality
        if speaker_change_event:
            components["speaker"] = speaker_change_score
        if car_profile_active and (
            strong_car_signal
            or car_start_event
            or car_stop_event
            or car_object_event
            or presentation_like
        ):
            components["car"] = max(
                car_accel_score,
                car_start_score,
                car_stop_score,
                car_object_score * 0.92,
                visual_motion_score * 0.85 if presentation_like else 0.0,
            )
        if vision_scoring_enabled:
            components["vision"] = min(
                1.0,
                vision_clip_quality * 0.55
                + vision_action_level * 0.20
                + vision_audio_visual_fit * 0.25,
            )

        weights = {
            "story": 0.21,
            "text": 0.18,
            "audio": 0.20,
            "boundary": 0.20,
            "car": 0.12,
            "voice": 0.07,
            "context": 0.08,
            "speaker": 0.06,
            "vision": 0.10,
        }
        if (not has_transcript) and car_profile_active:
            # Rebalance for low-dialogue car videos: visual/car signals are more informative
            # than textual structure.
            weights["audio"] = 0.22
            weights["boundary"] = 0.16 if presentation_like else 0.18
            weights["car"] = 0.20 if presentation_like else 0.16
            if "vision" in components:
                weights["vision"] = 0.14
        total_weight = sum(weights[k] for k in components)
        final_score = (
            sum(components[k] * weights[k] for k in components) / total_weight
            if total_weight > 0
            else audio_score
        )

        if has_transcript and not ENABLE_ADAPTIVE_SCORE:
            final_score = (
                story_score * 0.30 +
                text_score * 0.25 +
                audio_score * 0.20 +
                boundary_score * 0.25
            )
        if (not has_transcript) and not ENABLE_ADAPTIVE_SCORE:
            final_score = audio_score

        presentation_score_boost = 0.0
        if car_profile_active and presentation_like:
            presentation_score_boost += 0.06
            if car_exterior_tour_text_hint:
                presentation_score_boost += 0.03
            if car_object_event:
                presentation_score_boost += 0.03
            if visual_walkaround_silent_event:
                presentation_score_boost += 0.03
            if car_stationary_showcase_event:
                presentation_score_boost += 0.04
            if visual_motion_event:
                presentation_score_boost += 0.03
            if vision_scoring_enabled and vision_is_showcase:
                presentation_score_boost += 0.02
            if has_transcript and float(text_features.get("text_score", 0.0)) < 0.55:
                presentation_score_boost += 0.02
            presentation_score_boost = min(0.12, presentation_score_boost)
            final_score += presentation_score_boost
            presentation_floor = 0.64
            if car_exterior_tour_text_hint:
                presentation_floor += 0.03
            if car_object_event:
                presentation_floor += 0.03
            if visual_walkaround_silent_event:
                presentation_floor += 0.03
            if car_stationary_showcase_event:
                presentation_floor += 0.05
            if visual_motion_event:
                presentation_floor += 0.04
            if strong_car_signal:
                presentation_floor += 0.03
            if vision_scoring_enabled and vision_is_showcase:
                presentation_floor += 0.05
            presentation_floor = min(0.82, presentation_floor)
            final_score = max(final_score, presentation_floor)

        if has_transcript:
            # Combos
            combo_bonus = 0.0
            combo_reasons = []
            
            if has_laughter and story_score >= 0.5 and has_story_end:
                combo_bonus += 0.20
                combo_reasons.append("🎰 histoire drôle")
            elif has_hook and has_punchline:
                combo_bonus += 0.15
                combo_reasons.append("🎣 hook+payoff")
            
            if has_story_start and has_story_end:
                combo_bonus += 0.12
                combo_reasons.append("📚 histoire complète")
            
            climax_detected = text_features.get("story_phase") == "climax"
            if climax_detected:
                combo_bonus += 0.08
                combo_reasons.append("💥 climax")
            
            if has_intensifiers >= 3:
                combo_bonus += 0.05
                combo_reasons.append("🔥 intense")
            
            if has_dialogue >= 2:
                combo_bonus += 0.05
                combo_reasons.append("🗣️ dialogue vif")

            if opensmile_voice_event:
                combo_bonus += 0.05
                combo_reasons.append("🎙️ prosodie vocale")

            if speech_context_event and has_dialogue >= 1:
                combo_bonus += 0.03
                combo_reasons.append("🧩 parole détectée")

            if speech_music_mix_event and (
                onset_strength >= 0.5
                or visual_motion_event
                or has_hook
                or has_punchline
            ):
                combo_bonus += 0.04
                combo_reasons.append("🎚️ mix speech+music dynamique")

            if speaker_change_event and has_dialogue >= 1:
                combo_bonus += 0.04
                combo_reasons.append("👥 changement speaker")
            
            if onset_strength >= 0.6:
                combo_bonus += 0.04
                combo_reasons.append("⚡ changement audio")

            if strong_car_signal:
                combo_bonus += 0.08
                combo_reasons.append("🏎️ accélération moteur")
            if car_start_event:
                combo_bonus += 0.07
                combo_reasons.append("🚦 départ voiture")
            if car_stop_event:
                combo_bonus += 0.05
                combo_reasons.append("🛑 arrêt/freinage")
            if visual_motion_event:
                combo_bonus += 0.04
                combo_reasons.append("👀 mouvement visuel fort")
            if facial_emotion_event:
                combo_bonus += 0.06
                combo_reasons.append("🎭 émotion visage")
            if car_start_event and car_stop_event:
                combo_bonus += 0.03
                combo_reasons.append("🔁 séquence départ-arrêt")
            if car_start_from_yamnet:
                combo_bonus += 0.03
                combo_reasons.append("🧠 départ détecté IA audio")
            if car_start_from_launch:
                combo_bonus += 0.05
                combo_reasons.append("🚀 départ après silence")
            if car_stop_from_yamnet:
                combo_bonus += 0.02
                combo_reasons.append("🧠 arrêt détecté IA audio")
            if car_start_from_audio and car_start_from_visual:
                combo_bonus += 0.03
                combo_reasons.append("✅ départ confirmé audio+image")
            if car_stop_from_audio and car_stop_from_visual:
                combo_bonus += 0.02
                combo_reasons.append("✅ arrêt confirmé audio+image")
            if presentation_like:
                combo_bonus += 0.07
                combo_reasons.append("🚘 présentation voiture")
            if facial_emotion_event and has_dialogue >= 1:
                combo_bonus += 0.03
                combo_reasons.append("🧩 visage + dialogue")
            
            if has_hook and not has_punchline:
                combo_bonus += 0.03
            
            # Bonus pour bonnes coupes (single-pass)
            if boundary_score >= 0.8:
                combo_bonus += 0.05
                combo_reasons.append("✂️ coupes nettes")
            
            # Bonus si candidat détecté via story window (priorité au contenu)
            if source == "story_window":
                combo_bonus += 0.08
                combo_reasons.append("📖 détecté via texte")

            # Bonus de convergence multi-signaux: le clip devient robuste
            # quand plusieurs familles de signaux pointent le même moment.
            convergence_hits = 0
            if (
                onset_strength >= 0.6
                or opensmile_voice_event
                or strong_car_signal
                or car_start_event
                or car_stop_event
            ):
                convergence_hits += 1
            if visual_motion_event or facial_emotion_event:
                convergence_hits += 1
            if has_hook or has_punchline or story_score >= 0.55 or text_score >= 0.58:
                convergence_hits += 1
            if boundary_score >= 0.65:
                convergence_hits += 1
            if speech_music_mix_event or speaker_change_event:
                convergence_hits += 1

            if convergence_hits >= 4:
                combo_bonus += 0.08
                combo_reasons.append("🧠 convergence 4+ signaux")
            elif convergence_hits == 3:
                combo_bonus += 0.05
                combo_reasons.append("🧠 convergence 3 signaux")
            elif convergence_hits == 2:
                combo_bonus += 0.02
                combo_reasons.append("🧠 convergence 2 signaux")
            
            # Pénalités
            penalty = 0.0
            penalty_reasons = []
            
            # Pénalité réduite car le single-pass gère mieux les coupes
            is_mid_thought = text_features.get("is_mid_thought", False)
            if is_mid_thought and boundary_score < 0.5:
                penalty += 0.10
                penalty_reasons.append("⚠️ coupe milieu")
            
            words_per_sec = float(text_features.get("words_per_sec", 0.0))
            low_dialogue_content = words_per_sec < CAR_LOW_DIALOGUE_WPS
            non_dialogue_signal = (
                strong_car_signal
                or car_start_event
                or car_stop_event
                or visual_motion_event
                or facial_emotion_event
                or car_stationary_showcase_event
                or onset_strength >= 0.55
                or music_only_context
                or noise_only_context
            )
            non_dialogue_legit = non_dialogue_signal and (
                profile == "car"
                or strong_car_signal
                or car_start_event
                or car_stop_event
                or visual_motion_event
                or facial_emotion_event
                or onset_strength >= 0.60
            )
            dialogue_expected = (
                has_dialogue >= 1
                or speech_context_event
                or words_per_sec >= CAR_LOW_DIALOGUE_WPS * 1.15
                or profile == "talking"
                or has_story_start
                or has_story_end
            )

            if not has_story_start and not has_story_end and not climax_detected:
                if low_dialogue_content and non_dialogue_legit and not dialogue_expected:
                    combo_reasons.append("✅ structure non requise (low-dialogue)")
                elif presentation_like:
                    combo_reasons.append("✅ structure présentation voiture")
                else:
                    penalty += 0.12
                    penalty_reasons.append("⚠️ pas de structure")
            
            if words_per_sec < CAR_LOW_DIALOGUE_WPS:
                if non_dialogue_legit or (low_dialogue_content and not dialogue_expected):
                    combo_reasons.append("✅ low-dialogue compatible")
                else:
                    penalty += 0.08
                    penalty_reasons.append("⚠️ peu de dialogue")

            if (
                music_only_context
                and onset_strength < 0.45
                and not visual_motion_event
                and not strong_car_signal
                and text_score < 0.45
            ):
                penalty += 0.08
                penalty_reasons.append("⚠️ fond musical sans signal fort")

            if (
                noise_only_context
                and onset_strength < 0.40
                and not visual_motion_event
                and text_score < 0.45
                and not non_dialogue_legit
                and not strong_car_signal
                and not car_start_event
                and not car_stop_event
            ):
                penalty += 0.09
                penalty_reasons.append("⚠️ bruit dominant")

            # Pénalité pour mauvaises coupes
            if boundary_score < 0.3:
                car_boundary_tolerance = (
                    car_profile_active
                    and (
                        strong_car_signal
                        or car_start_event
                        or car_stop_event
                        or visual_motion_event
                        or presentation_like
                    )
                    and (low_dialogue_content or non_dialogue_legit or presentation_like)
                    and boundary_score >= 0.12
                )
                if car_boundary_tolerance:
                    penalty += 0.11
                    penalty_reasons.append("⚠️ coupes moyennes (tolérance car)")
                else:
                    penalty += 0.20
                    penalty_reasons.append("⚠️ coupes floues")

            # Pénalité longueur: au-delà de ~1min20, exige forte cohérence.
            if clip_length > 80.0:
                overflow = clip_length - 80.0
                length_penalty = min(0.18, overflow * 0.008)
                penalty += length_penalty
                penalty_reasons.append("⚠️ clip trop long")
            elif clip_length > 65.0 and not has_story_end:
                car_longform_legit = (
                    profile == "car"
                    or strong_car_signal
                    or car_start_event
                    or car_stop_event
                    or (
                        low_dialogue_content
                        and non_dialogue_legit
                        and not dialogue_expected
                    )
                )
                if car_longform_legit:
                    combo_reasons.append("✅ fin ouverte acceptable (car/low-dialogue)")
                else:
                    penalty += 0.07
                    penalty_reasons.append("⚠️ fin longue sans conclusion")

            # Ollama bonus/penalties
            if ollama_analysis.get("ollama_used"):
                ollama_quality = ollama_analysis.get("cut_quality", 0.7)
                viral_potential = ollama_analysis.get("viral_potential", 0.5)
                ollama_complete = bool(ollama_analysis.get("is_complete", True))
                
                if ollama_quality >= 0.8:
                    combo_bonus += 0.08
                    combo_reasons.append("🤖 LLM approuve")
                elif ollama_quality <= 0.35:
                    penalty += 0.14
                    penalty_reasons.append("🤖 LLM désapprouve")
                
                if viral_potential >= 0.8:
                    combo_bonus += 0.06
                    combo_reasons.append("🚀 potentiel viral")
                
                if not ollama_complete:
                    penalty += 0.08
                    penalty_reasons.append("🤖 incomplet")

                if ollama_action == "drop":
                    penalty += 0.25
                    penalty_reasons.append("🤖 LLM drop")
                elif ollama_action in {"trim_end", "trim_start"} and not ollama_trim_applied:
                    penalty += 0.08
                    penalty_reasons.append("🤖 recoupe suggérée")
            
            combo_bonus = min(SCORE_COMBO_BONUS_CAP, combo_bonus)
            final_score += combo_bonus - penalty
            
            # Log
            if combo_reasons or penalty_reasons:
                LOGGER.info(
                    "Clip %.1f-%.1f: boundary=%.2f combos=%s(+%.2f) penalties=%s(-%.2f) -> final=%.2f",
                    start, end, boundary_score,
                    ",".join(combo_reasons) if combo_reasons else "none",
                    combo_bonus,
                    ",".join(penalty_reasons) if penalty_reasons else "none",
                    penalty,
                    final_score
                )
            
            audio_features["combo_bonus"] = round(combo_bonus, 3)
            audio_features["combo_reasons"] = combo_reasons
            audio_features["penalty"] = round(penalty, 3)
            audio_features["penalty_reasons"] = penalty_reasons
            audio_features["has_hook"] = has_hook
            audio_features["has_punchline"] = has_punchline
            audio_features["has_laughter"] = has_laughter

        non_text_bonus = 0.0
        non_text_penalty = 0.0
        non_text_reasons: list[str] = []
        if not has_transcript:
            if car_profile_active:
                if presentation_like:
                    non_text_bonus += 0.06
                    non_text_reasons.append("car presentation low-dialogue")
                if car_stationary_showcase_event:
                    non_text_bonus += 0.03
                    non_text_reasons.append("car presentation stationnaire")

                if visual_motion_event and visual_motion_score >= max(0.80, VISUAL_EVENT_MIN_SCORE * 1.45):
                    non_text_bonus += 0.02
                    non_text_reasons.append("car visual dynamique")

                if strong_car_signal:
                    non_text_bonus += 0.03
                    non_text_reasons.append("car signal fort")

                if car_start_event or car_stop_event:
                    non_text_bonus += 0.03
                    non_text_reasons.append("car transition start/stop")
                if car_insertion_focus:
                    non_text_bonus += 0.03
                    non_text_reasons.append("car insertion autoroute")

                if (
                    presentation_like
                    and not vision_used
                    and visual_motion_score >= max(0.78, VISUAL_EVENT_MIN_SCORE * 1.35)
                ):
                    # Keep showcase clips from being under-scored when vision inference fails.
                    non_text_bonus += 0.015
                    non_text_reasons.append("fallback sans vision")

            if boundary_score < 0.22 and not presentation_like:
                non_text_penalty += 0.05
                non_text_reasons.append("boundary faible sans contexte texte")

            if clip_length > 80.0 and not (car_profile_active and (presentation_like or strong_car_signal)):
                non_text_penalty += min(0.10, (clip_length - 80.0) * 0.006)
                non_text_reasons.append("longueur excessive sans narration")

            non_text_bonus = min(0.14, non_text_bonus)
            final_score += non_text_bonus - non_text_penalty
            LOGGER.info(
                "Clip %.1f-%.1f: low-dialogue delta=+%.2f-%.2f (%s)",
                start,
                end,
                non_text_bonus,
                non_text_penalty,
                ",".join(non_text_reasons) if non_text_reasons else "none",
            )

        vision_bonus = 0.0
        vision_penalty = 0.0
        vision_reasons: list[str] = []
        if vision_scoring_enabled:
            if vision_clip_quality >= 0.78:
                vision_bonus += 0.06
                vision_reasons.append("vision qualite elevee")
            elif vision_clip_quality <= 0.30:
                vision_penalty += 0.10
                vision_reasons.append("vision qualite faible")

            if vision_audio_visual_fit >= 0.78:
                vision_bonus += 0.03
                vision_reasons.append("vision audio+image coherents")
            elif vision_audio_visual_fit <= 0.30:
                vision_penalty += 0.06
                vision_reasons.append("vision audio+image incoherents")

            if car_profile_active and vision_is_showcase:
                vision_bonus += 0.05
                vision_reasons.append("vision presentation voiture")

            if (
                vision_action_level >= 0.80
                and (strong_car_signal or visual_motion_event or car_start_event)
            ):
                vision_bonus += 0.03
                vision_reasons.append("vision action forte")

            final_score += vision_bonus - vision_penalty
            LOGGER.info(
                "Clip %.1f-%.1f: vision scene=%s quality=%.2f action=%.2f av_fit=%.2f showcase=%s delta=+%.2f-%.2f (%s)",
                start,
                end,
                vision_scene_type or "unknown",
                vision_clip_quality,
                vision_action_level,
                vision_audio_visual_fit,
                vision_is_showcase,
                vision_bonus,
                vision_penalty,
                ",".join(vision_reasons) if vision_reasons else "none",
            )

        # Règle de garde: ignore les faux positifs "car" sans base audio suffisante.
        if car_profile_active and strong_car_signal and base_audio_score < CAR_GUARD_MIN_AUDIO:
            if not ALLOW_LOW_SCORE_CLIPS:
                LOGGER.info(
                    "Clip rejected (car guard: car=%.2f sustain=%.1fs base_audio=%.2f < %.2f): %.1f-%.1f",
                    car_accel_score,
                    car_sustain_seconds,
                    base_audio_score,
                    CAR_GUARD_MIN_AUDIO,
                    start,
                    end,
                )
                continue
            LOGGER.info(
                "Clip kept despite car guard because ALLOW_LOW_SCORE_CLIPS=true (car=%.2f sustain=%.1fs base_audio=%.2f < %.2f): %.1f-%.1f",
                car_accel_score,
                car_sustain_seconds,
                base_audio_score,
                CAR_GUARD_MIN_AUDIO,
                start,
                end,
            )

        # Petite variation stochastique pour éviter la même shortlist à chaque run.
        if (
            ENABLE_CLIP_VARIATION
            and variant_rng is not None
            and CLIP_VARIATION_SCORE_JITTER > 0
        ):
            variation_delta = variant_rng.uniform(
                -CLIP_VARIATION_SCORE_JITTER,
                CLIP_VARIATION_SCORE_JITTER,
            )
            final_score += variation_delta

        final_score = max(0.0, min(1.0, final_score))

        effective_min_score = MIN_SCORE
        if car_profile_active and presentation_like:
            # Keep at least one usable car showcase clip on sparse-transcript videos.
            effective_min_score = max(0.38, MIN_SCORE - 0.14)
        elif car_profile_active and (strong_car_signal or car_start_event or car_stop_event):
            # Car clips are often low-dialogue and can have weaker textual boundaries.
            effective_min_score = max(0.40, MIN_SCORE - 0.10)
        elif presentation_like:
            # Walkaround/presentation clips are useful even with softer audio peaks.
            effective_min_score = max(0.42, MIN_SCORE - 0.08)
        elif profile == "car" and (non_dialogue_legit or low_dialogue_content):
            effective_min_score = max(0.40, MIN_SCORE - 0.10)

        showcase_like_candidate = bool(
            car_profile_active
            and (
                car_exterior_tour_text_hint
                or visual_walkaround_silent_event
                or car_stationary_showcase_event
                or car_object_event
                or vision_is_showcase
                or car_showcase_event
                or (
                    vision_used
                    and vision_scene_type in {"showcase", "interior"}
                    and vision_clip_quality >= 0.55
                )
            )
        )
        transition_like_candidate = bool(
            car_profile_active
            and (
                car_start_event
                or car_stop_event
                or car_start_from_scene_cut
                or car_start_from_inferred
                or car_start_from_launch
                or car_insertion_focus
            )
            and (
                start >= 6.0
                or car_start_from_scene_cut
                or car_start_from_inferred
                or car_start_from_launch
                or car_insertion_focus
            )
        )
        insertion_moving_context = bool(
            insertion_pre_motion >= max(0.34, VISUAL_EVENT_MIN_SCORE * 0.75)
            or insertion_pre_car >= max(0.18, CAR_ACCEL_THRESHOLD * 0.30)
        )
        insertion_accel_context = bool(
            insertion_post_car >= max(0.30, CAR_ACCEL_THRESHOLD * 0.52)
            or insertion_post_onset >= 0.50
            or insertion_rms_jump >= max(0.06, CAR_EVENT_MIN_DELTA * 0.50)
            or car_start_from_scene_cut
        )
        insertion_scene_transition = bool(
            car_start_from_scene_cut
            and (car_start_from_inferred or car_start_from_visual or car_start_from_yamnet)
        )
        insertion_signal_bundle = bool(
            insertion_scene_transition
            or (car_start_from_inferred and car_start_from_visual)
            or car_insertion_focus
        )
        insertion_like_candidate = bool(
            car_profile_active
            and transition_like_candidate
            and not car_start_from_launch
            and insertion_min_start <= start <= insertion_max_start
            and (
                (insertion_moving_context and insertion_accel_context and insertion_signal_bundle)
                or insertion_scene_transition
                or (car_start_from_inferred and insertion_accel_context)
                or (car_start_from_visual and insertion_accel_context)
            )
        )

        if transition_like_candidate:
            transition_start = float(start)
            transition_end = float(end)
            transition_target_len = max(min_clip_length, min(34.0, max_clip_length * 0.62))
            if (transition_end - transition_start) > (transition_target_len + 2.0):
                transition_end = min(transition_end, transition_start + transition_target_len)
            if (transition_end - transition_start) < min_clip_length:
                transition_end = min(duration, transition_start + min_clip_length)
            if (transition_end - transition_start) >= min_clip_length:
                seed_features = dict(audio_features)
                seed_features["car_transition_focus"] = True
                seed_features["car_transition_fallback"] = True
                seed_features["car_start_event"] = bool(car_start_event)
                seed_features["car_stop_event"] = bool(car_stop_event)
                seed_features["car_start_from_scene_cut"] = bool(car_start_from_scene_cut)
                seed_features["car_start_from_inferred"] = bool(car_start_from_inferred)
                seed_features["car_start_from_launch"] = bool(car_start_from_launch)
                seed_score = max(
                    final_score,
                    min(
                        effective_min_score - 0.01,
                        max(0.42, MIN_SCORE - 0.10),
                    ),
                )
                seed_features["score"] = round(seed_score, 3)
                seed_tag, seed_reason, seed_signals = _tag_and_reason(seed_features, None)
                seed_features["signals"] = seed_signals
                seed_features["tiktok_title"] = _build_tiktok_title(
                    seed_tag,
                    transition_start,
                    transition_end,
                    transcript_segments,
                    text_features,
                    audio_features=seed_features,
                )
                seed_tuple = (
                    transition_start,
                    transition_end - transition_start,
                    round(seed_score, 3),
                    seed_tag,
                    seed_reason,
                    seed_features,
                )
                seed_rank = (
                    float(seed_score)
                    + (0.10 if car_start_from_scene_cut else 0.0)
                    + (0.08 if car_start_from_inferred else 0.0)
                    + (0.08 if car_start_from_launch else 0.0)
                    + (0.06 if car_start_event else 0.0)
                    + (0.03 if car_stop_event else 0.0)
                )
                if seed_rank > best_transition_focus_seed_rank:
                    best_transition_focus_seed_rank = seed_rank
                    best_transition_focus_seed = seed_tuple

                if insertion_like_candidate:
                    insertion_start = transition_start
                    insertion_end = transition_end
                    insertion_target_len = max(min_clip_length, min(32.0, max_clip_length * 0.58))
                    insertion_start = max(0.0, insertion_start - 4.5)
                    if insertion_end <= insertion_start + min_clip_length:
                        insertion_end = min(duration, insertion_start + min_clip_length)
                    if (insertion_end - insertion_start) > (insertion_target_len + 2.0):
                        insertion_end = min(insertion_end, insertion_start + insertion_target_len)
                    if (insertion_end - insertion_start) < min_clip_length:
                        insertion_end = min(duration, insertion_start + min_clip_length)
                        if (insertion_end - insertion_start) < min_clip_length:
                            insertion_start = max(0.0, insertion_end - min_clip_length)

                    insertion_features = dict(seed_features)
                    insertion_features["car_insertion_focus"] = True
                    insertion_features["car_insertion_focus_score"] = round(insertion_focus_score, 3)
                    insertion_features["car_insertion_pre_motion"] = round(insertion_pre_motion, 3)
                    insertion_features["car_insertion_rms_jump"] = round(insertion_rms_jump, 3)
                    insertion_features["car_transition_focus"] = True
                    insertion_features["car_transition_fallback"] = True
                    insertion_features["car_start_from_launch"] = False
                    insertion_score = max(
                        seed_score,
                        min(
                            effective_min_score - 0.01,
                            max(0.43, MIN_SCORE - 0.09),
                        ),
                    )
                    insertion_features["score"] = round(insertion_score, 3)
                    insertion_tag, insertion_reason, insertion_signals = _tag_and_reason(
                        insertion_features,
                        None,
                    )
                    insertion_features["signals"] = insertion_signals
                    insertion_features["tiktok_title"] = _build_tiktok_title(
                        insertion_tag,
                        insertion_start,
                        insertion_end,
                        transcript_segments,
                        text_features,
                        audio_features=insertion_features,
                    )
                    insertion_tuple = (
                        insertion_start,
                        insertion_end - insertion_start,
                        round(insertion_score, 3),
                        insertion_tag,
                        insertion_reason,
                        insertion_features,
                    )
                    insertion_rank = (
                        float(insertion_score)
                        + (0.12 if car_start_from_scene_cut else 0.0)
                        + (0.08 if car_start_from_inferred else 0.0)
                        + (0.07 if car_start_from_visual else 0.0)
                        + (0.05 if car_start_from_yamnet else 0.0)
                        + (0.03 if visual_motion_event else 0.0)
                    )
                    insertion_progress = insertion_start / max(duration, 1.0)
                    insertion_rank += max(
                        0.0,
                        1.0 - abs(insertion_progress - 0.30) / 0.35,
                    ) * 0.06
                    if insertion_rank > best_insertion_rank:
                        best_insertion_rank = insertion_rank
                        best_insertion_candidate = insertion_tuple

                transition_progress = transition_start / max(duration, 1.0)
                mid_focus_bonus = max(0.0, 1.0 - abs(transition_progress - 0.58) / 0.26) * 0.06
                tail_penalty = max(0.0, transition_progress - 0.78) * 0.12
                late_seed_rank = seed_rank + mid_focus_bonus - tail_penalty
                if (
                    late_transition_min_start <= transition_start <= late_transition_max_start
                    and late_seed_rank > best_transition_late_rank
                ):
                    best_transition_late_rank = late_seed_rank
                    best_transition_late_candidate = seed_tuple

                if car_start_from_launch:
                    launch_seed_rank = late_seed_rank + 0.08
                    if (
                        transition_start <= launch_early_max_start
                        and launch_seed_rank > best_launch_early_rank
                    ):
                        best_launch_early_rank = launch_seed_rank
                        best_launch_early_candidate = seed_tuple
                    if (
                        late_transition_min_start <= transition_start <= late_transition_max_start
                        and launch_seed_rank > best_launch_late_rank
                    ):
                        best_launch_late_rank = launch_seed_rank
                        best_launch_late_candidate = seed_tuple

        if final_score < effective_min_score:
            if not ALLOW_LOW_SCORE_CLIPS:
                if showcase_like_candidate:
                    fallback_features = dict(audio_features)
                    fallback_features["car_showcase_event"] = True
                    fallback_features["car_presentation_like"] = True
                    fallback_features["ollama_vision_used"] = bool(vision_used)
                    fallback_features["ollama_vision_scene"] = vision_scene_type
                    fallback_features["ollama_vision_quality"] = round(vision_clip_quality, 3)
                    fallback_features["ollama_vision_showcase"] = bool(vision_is_showcase)
                    fallback_features["score"] = round(final_score, 3)
                    fallback_tag, fallback_reason, fallback_signals = _tag_and_reason(
                        fallback_features,
                        None,
                    )
                    fallback_features["signals"] = fallback_signals
                    fallback_features["tiktok_title"] = _build_tiktok_title(
                        fallback_tag,
                        start,
                        end,
                        transcript_segments,
                        text_features,
                        audio_features=fallback_features,
                    )
                    candidate_tuple = (
                        start,
                        end - start,
                        round(final_score, 3),
                        fallback_tag,
                        fallback_reason,
                        fallback_features,
                    )
                    if (
                        best_showcase_fallback is None
                        or candidate_tuple[2] > best_showcase_fallback[2]
                    ):
                        best_showcase_fallback = candidate_tuple
                if transition_like_candidate:
                    fallback_features = dict(audio_features)
                    fallback_features["car_transition_fallback"] = True
                    fallback_features["car_start_event"] = bool(car_start_event)
                    fallback_features["car_stop_event"] = bool(car_stop_event)
                    fallback_features["car_start_from_scene_cut"] = bool(car_start_from_scene_cut)
                    fallback_features["car_start_from_inferred"] = bool(car_start_from_inferred)
                    fallback_features["car_start_from_launch"] = bool(car_start_from_launch)
                    fallback_features["car_insertion_focus"] = bool(car_insertion_focus)
                    fallback_features["car_insertion_focus_score"] = round(insertion_focus_score, 3)

                    transition_start = float(start)
                    transition_end = float(end)
                    if (
                        car_start_event
                        or car_start_from_scene_cut
                        or car_start_from_inferred
                        or car_start_from_launch
                    ):
                        target_len = max(min_clip_length, min(36.0, max_clip_length * 0.65))
                        if (transition_end - transition_start) > (target_len + 2.0):
                            transition_end = min(transition_end, transition_start + target_len)
                    if (transition_end - transition_start) < min_clip_length:
                        transition_end = min(duration, transition_start + min_clip_length)
                        if (transition_end - transition_start) < min_clip_length:
                            transition_start = max(0.0, transition_end - min_clip_length)

                    fallback_score = max(
                        final_score,
                        min(
                            effective_min_score - 0.01,
                            max(0.42, MIN_SCORE - 0.10),
                        ),
                    )
                    fallback_features["score"] = round(fallback_score, 3)
                    fallback_tag, fallback_reason, fallback_signals = _tag_and_reason(
                        fallback_features,
                        None,
                    )
                    fallback_features["signals"] = fallback_signals
                    fallback_features["tiktok_title"] = _build_tiktok_title(
                        fallback_tag,
                        transition_start,
                        transition_end,
                        transcript_segments,
                        text_features,
                        audio_features=fallback_features,
                    )
                    candidate_tuple = (
                        transition_start,
                        transition_end - transition_start,
                        round(fallback_score, 3),
                        fallback_tag,
                        fallback_reason,
                        fallback_features,
                    )
                    transition_rank = (
                        float(fallback_score)
                        + (0.09 if car_start_from_scene_cut else 0.0)
                        + (0.06 if car_start_from_inferred else 0.0)
                        + (0.10 if car_start_from_launch else 0.0)
                        + (0.12 if car_insertion_focus else 0.0)
                        + (0.05 if car_start_event else 0.0)
                        + (0.02 if car_stop_event else 0.0)
                    )
                    if transition_rank > best_transition_fallback_rank:
                        best_transition_fallback_rank = transition_rank
                        best_transition_fallback = candidate_tuple

                    transition_progress = transition_start / max(duration, 1.0)
                    mid_focus_bonus = max(0.0, 1.0 - abs(transition_progress - 0.58) / 0.26) * 0.07
                    tail_penalty = max(0.0, transition_progress - 0.78) * 0.14
                    late_transition_rank = transition_rank + mid_focus_bonus - tail_penalty
                    if (
                        late_transition_min_start <= transition_start <= late_transition_max_start
                        and late_transition_rank > best_transition_late_rank
                    ):
                        best_transition_late_rank = late_transition_rank
                        best_transition_late_candidate = candidate_tuple

                    if car_start_from_launch:
                        launch_fallback_rank = late_transition_rank + 0.09
                        if (
                            transition_start <= launch_early_max_start
                            and launch_fallback_rank > best_launch_early_rank
                        ):
                            best_launch_early_rank = launch_fallback_rank
                            best_launch_early_candidate = candidate_tuple
                        if (
                            late_transition_min_start <= transition_start <= late_transition_max_start
                            and launch_fallback_rank > best_launch_late_rank
                        ):
                            best_launch_late_rank = launch_fallback_rank
                            best_launch_late_candidate = candidate_tuple
                LOGGER.info(
                    "Clip rejected (score=%.2f < %.2f): %.1f-%.1f",
                    final_score,
                    effective_min_score,
                    start,
                    end,
                )
                continue
            LOGGER.info(
                "Clip kept below min score because ALLOW_LOW_SCORE_CLIPS=true (score=%.2f < %.2f): %.1f-%.1f",
                final_score,
                effective_min_score,
                start,
                end,
            )

        # Stocke toutes les features
        audio_features["base_audio_score"] = base_audio_score
        audio_features["audio_score"] = audio_score
        audio_features["variation_enabled"] = bool(ENABLE_CLIP_VARIATION and variant_rng is not None)
        audio_features["variation_delta"] = round(variation_delta, 4)
        audio_features["car_accel_score"] = round(car_accel_score, 3)
        audio_features["car_sustain_seconds"] = round(car_sustain_seconds, 3)
        audio_features["car_sustained"] = bool(car_is_sustained)
        audio_features["car_strong_signal"] = bool(strong_car_signal)
        audio_features["car_showcase_event"] = bool(car_showcase_event)
        audio_features["car_presentation_like"] = bool(presentation_like)
        audio_features["car_exterior_tour_text_hint"] = bool(car_exterior_tour_text_hint)
        audio_features["car_visual_walkaround_silent_event"] = bool(visual_walkaround_silent_event)
        audio_features["car_stationary_showcase_event"] = bool(car_stationary_showcase_event)
        audio_features["car_object_score"] = round(car_object_score, 3)
        audio_features["car_object_event"] = bool(car_object_event)
        audio_features["car_start_score"] = round(car_start_score, 3)
        audio_features["car_stop_score"] = round(car_stop_score, 3)
        audio_features["car_start_event"] = bool(car_start_event)
        audio_features["car_stop_event"] = bool(car_stop_event)
        audio_features["car_start_from_audio"] = bool(car_start_from_audio)
        audio_features["car_stop_from_audio"] = bool(car_stop_from_audio)
        audio_features["car_start_from_yamnet"] = bool(car_start_from_yamnet)
        audio_features["car_stop_from_yamnet"] = bool(car_stop_from_yamnet)
        audio_features["car_start_from_visual"] = bool(car_start_from_visual)
        audio_features["car_stop_from_visual"] = bool(car_stop_from_visual)
        audio_features["car_start_from_inferred"] = bool(car_start_from_inferred)
        audio_features["car_start_from_scene_cut"] = bool(car_start_from_scene_cut)
        audio_features["car_start_from_launch"] = bool(car_start_from_launch)
        audio_features["car_insertion_focus"] = bool(car_insertion_focus)
        audio_features["car_insertion_focus_score"] = round(insertion_focus_score, 3)
        audio_features["car_insertion_pre_motion"] = round(insertion_pre_motion, 3)
        audio_features["car_insertion_rms_jump"] = round(insertion_rms_jump, 3)
        audio_features["visual_motion_score"] = round(visual_motion_score, 3)
        audio_features["visual_motion_event"] = bool(visual_motion_event)
        audio_features["opensmile_voice_score"] = round(opensmile_voice_score, 3)
        audio_features["opensmile_voice_event"] = bool(opensmile_voice_event)
        audio_features["opensmile_event_min_score"] = float(OPENSMILE_EVENT_MIN_SCORE)
        audio_features["speech_context_ratio"] = round(speech_context_ratio, 3)
        audio_features["music_context_ratio"] = round(music_context_ratio, 3)
        audio_features["noise_context_ratio"] = round(noise_context_ratio, 3)
        audio_features["speech_music_mix_score"] = round(speech_music_mix_score, 3)
        audio_features["music_only_context"] = bool(music_only_context)
        audio_features["noise_only_context"] = bool(noise_only_context)
        audio_features["speaker_change_score"] = round(speaker_change_score, 3)
        audio_features["speaker_change_event"] = bool(speaker_change_event)
        audio_features["audio_context_provider"] = AUDIO_CONTEXT_PROVIDER
        audio_features["facial_emotion_score"] = round(facial_emotion_score, 3)
        audio_features["facial_emotion_event"] = bool(facial_emotion_event)
        audio_features["car_event_min_score"] = float(CAR_EVENT_MIN_SCORE)
        audio_features["audio_event_min_score"] = float(AUDIO_EVENT_MIN_SCORE)
        audio_features["audio_event_provider"] = AUDIO_EVENT_PROVIDER
        audio_features["visual_event_min_score"] = float(VISUAL_EVENT_MIN_SCORE)
        audio_features["object_car_min_score"] = float(OBJECT_CAR_MIN_SCORE)
        audio_features["object_car_detection_available"] = bool(OBJECT_CAR_DETECTION_AVAILABLE)
        audio_features["facial_emotion_event_min_score"] = float(FACIAL_EMOTION_EVENT_MIN_SCORE)
        audio_features["car_profile_active"] = bool(car_profile_active)
        audio_features["clip_profile"] = profile
        audio_features["target_min_clip_length"] = round(min_clip_length, 3)
        audio_features["target_max_clip_length"] = round(max_clip_length, 3)
        audio_features["profile_reason"] = str(profile_meta.get("reason", ""))
        audio_features["profile_words_per_sec"] = float(profile_meta.get("words_per_sec", 0.0))
        audio_features["profile_car_peaks_per_min"] = float(profile_meta.get("car_peaks_per_min", 0.0))
        audio_features["profile_car_audio_peaks_per_min"] = float(
            profile_meta.get("car_audio_peaks_per_min", 0.0)
        )
        audio_features["profile_car_object_peaks_per_min"] = float(
            profile_meta.get("car_object_peaks_per_min", 0.0)
        )
        audio_features["text_score"] = text_score
        audio_features["story_score"] = story_score
        audio_features["boundary_score"] = round(boundary_score, 3)
        audio_features["words_per_sec"] = text_features["words_per_sec"]
        audio_features["keyword_hits"] = text_features["keyword_hits"]
        audio_features["exclamations"] = text_features["exclamations"]
        audio_features["questions"] = text_features["questions"]
        audio_features["text_tag"] = text_features["text_tag"]
        audio_features["text_reason"] = text_features["text_reason"]
        audio_features["keybert_score"] = text_features.get("keybert_score", 0.0)
        audio_features["keybert_keywords"] = text_features.get("keybert_keywords", [])
        audio_features["is_commercial"] = text_features.get("is_commercial", False)
        audio_features["has_story_start"] = text_features.get("has_story_start", False)
        audio_features["has_story_end"] = text_features.get("has_story_end", False)
        audio_features["is_mid_thought"] = text_features.get("is_mid_thought", False)
        audio_features["ollama_used"] = ollama_analysis.get("ollama_used", False)
        audio_features["ollama_quality"] = ollama_analysis.get("cut_quality", 0.7)
        audio_features["ollama_reason"] = ollama_analysis.get("reason", "")
        audio_features["ollama_vision_used"] = bool(vision_used)
        audio_features["ollama_vision_scene"] = vision_scene_type
        audio_features["ollama_vision_action"] = round(vision_action_level, 3)
        audio_features["ollama_vision_quality"] = round(vision_clip_quality, 3)
        audio_features["ollama_vision_audio_visual_fit"] = round(vision_audio_visual_fit, 3)
        audio_features["ollama_vision_showcase"] = bool(vision_is_showcase)
        audio_features["ollama_vision_frames"] = int(vision_analysis.get("frame_count", 0) or 0)
        audio_features["ollama_vision_title"] = vision_title_hint
        audio_features["ollama_vision_reason"] = str(vision_analysis.get("reason", ""))
        audio_features["ollama_vision_title_only"] = False
        audio_features["low_dialogue_bonus"] = round(non_text_bonus, 3)
        audio_features["low_dialogue_penalty"] = round(non_text_penalty, 3)
        audio_features["low_dialogue_reasons"] = non_text_reasons
        audio_features["presentation_score_boost"] = round(presentation_score_boost, 3)
        audio_features["vision_bonus"] = round(vision_bonus, 3)
        audio_features["vision_penalty"] = round(vision_penalty, 3)

        text_features_for_tag: dict[str, Any] | None = text_features
        weak_text_for_car = (
            car_profile_active
            and (
                strong_car_signal
                or car_start_event
                or car_stop_event
                or visual_motion_event
                or car_object_event
                or visual_walkaround_silent_event
                or car_stationary_showcase_event
            )
            and float(text_features.get("words_per_sec", 0.0)) < CAR_LOW_DIALOGUE_WPS * 1.10
            and float(text_features.get("text_score", 0.0)) < 0.58
            and int(text_features.get("dialogue_hits", 0)) < 1
            and not bool(text_features.get("has_story_end", False))
        )
        if weak_text_for_car:
            text_features_for_tag = None
            audio_features["text_override_disabled"] = "car_low_dialogue"

        tag, reason, signals = _tag_and_reason(audio_features, text_features_for_tag)
        audio_features["signals"] = signals
        audio_features["score"] = round(final_score, 3)
        audio_features["effective_min_score"] = round(effective_min_score, 3)
        audio_features["below_min_score"] = bool(final_score < effective_min_score)
        audio_features["below_min_score_allowed"] = bool(
            final_score < effective_min_score and ALLOW_LOW_SCORE_CLIPS
        )
        tiktok_title = _build_tiktok_title(
            tag,
            start,
            end,
            transcript_segments,
            text_features,
            audio_features=audio_features,
        )
        audio_features["tiktok_title"] = tiktok_title
        segments.append((start, end - start, audio_features["score"], tag, reason, audio_features))

    if car_profile_active and best_showcase_fallback is not None:
        has_showcase_selected = any(
            bool(
                seg_features.get("car_showcase_event", False)
                or seg_features.get("car_presentation_like", False)
                or seg_features.get("ollama_vision_showcase", False)
            )
            for _, _, _, _, _, seg_features in segments
        )
        if not has_showcase_selected:
            LOGGER.info(
                "Ajout fallback showcase voiture: %.1f-%.1f score=%.2f",
                best_showcase_fallback[0],
                best_showcase_fallback[0] + best_showcase_fallback[1],
                best_showcase_fallback[2],
            )
            segments.append(best_showcase_fallback)

    if ENABLE_NMS:
        segments = _nms_segments(segments, iou_threshold=0.6)
    segments.sort(key=lambda item: item[0])

    merged: list[tuple[float, float, float, str, str, dict]] = []
    for segment in segments:
        if not merged:
            merged.append(segment)
            continue
        prev_start, prev_length, prev_score, prev_tag, prev_reason, prev_features = merged[-1]
        prev_end = prev_start + prev_length
        start, length, score, tag, reason, features = segment
        if start <= prev_end + MERGE_GAP_SECONDS:
            overlap_start = max(prev_start, start)
            overlap_end = min(prev_end, start + length)
            overlap_seconds = max(0.0, overlap_end - overlap_start)
            overlap_ratio_prev = overlap_seconds / max(prev_length, 1e-6)
            overlap_ratio_cur = overlap_seconds / max(length, 1e-6)
            prev_transition_like = bool(
                prev_features.get("car_start_event", False)
                or prev_features.get("car_stop_event", False)
                or prev_features.get("car_start_from_scene_cut", False)
                or prev_features.get("car_start_from_inferred", False)
                or prev_features.get("car_start_from_launch", False)
                or prev_features.get("car_transition_focus", False)
            )
            cur_transition_like = bool(
                features.get("car_start_event", False)
                or features.get("car_stop_event", False)
                or features.get("car_start_from_scene_cut", False)
                or features.get("car_start_from_inferred", False)
                or features.get("car_start_from_launch", False)
                or features.get("car_transition_focus", False)
            )
            prev_presentation_like = bool(
                prev_features.get("car_presentation_like", False)
                or prev_features.get("car_showcase_event", False)
                or prev_features.get("ollama_vision_showcase", False)
            )
            cur_presentation_like = bool(
                features.get("car_presentation_like", False)
                or features.get("car_showcase_event", False)
                or features.get("ollama_vision_showcase", False)
            )
            prev_launch_focus = bool(
                prev_features.get("car_start_from_launch", False)
                or prev_features.get("car_launch_focus", False)
            )
            cur_launch_focus = bool(
                features.get("car_start_from_launch", False)
                or features.get("car_launch_focus", False)
            )
            prev_insertion_focus = bool(prev_features.get("car_insertion_focus", False))
            cur_insertion_focus = bool(features.get("car_insertion_focus", False))
            preserve_transition_split = bool(
                car_profile_active
                and start >= prev_end
                and (
                    (cur_transition_like and prev_presentation_like and not cur_presentation_like)
                    or (prev_transition_like and cur_presentation_like and not prev_presentation_like)
                )
            )
            preserve_low_overlap_split = bool(
                car_profile_active
                and overlap_seconds > 0.0
                and overlap_seconds <= min(prev_length, length) * 0.35
                and (
                    (prev_presentation_like != cur_presentation_like)
                    or (prev_launch_focus != cur_launch_focus)
                    or (prev_insertion_focus != cur_insertion_focus)
                )
            )
            if preserve_transition_split or preserve_low_overlap_split:
                merged.append(segment)
                continue
            if MERGE_KEEP_BEST_ONLY:
                if car_profile_active:
                    high_overlap_launch = max(overlap_ratio_prev, overlap_ratio_cur) >= 0.45
                    if prev_launch_focus and cur_launch_focus and high_overlap_launch:
                        # Keep the earliest launch to preserve the stopped-before-accel context.
                        launch_gap = abs(float(start) - float(prev_start))
                        if launch_gap >= max(1.8, ANALYSIS_WINDOW_SECONDS * 4):
                            continue
                    if prev_launch_focus != cur_launch_focus and high_overlap_launch:
                        if cur_launch_focus:
                            merged[-1] = segment
                        continue
                    high_overlap_insertion = max(overlap_ratio_prev, overlap_ratio_cur) >= 0.45
                    if prev_insertion_focus != cur_insertion_focus and high_overlap_insertion:
                        if cur_insertion_focus:
                            merged[-1] = segment
                        continue
                if score > prev_score:
                    merged[-1] = segment
                continue
            best = (prev_start, prev_length, prev_score, prev_tag, prev_reason, prev_features)
            if score > prev_score:
                best = (start, length, score, tag, reason, features)
            new_start = min(prev_start, start)
            new_end = max(prev_end, start + length)
            new_length = new_end - new_start
            if new_length < min_clip_length:
                center = best[0] + best[1] * 0.5
                new_length = min_clip_length
                new_start = max(0.0, min(center - new_length * 0.45, duration - new_length))
                new_end = new_start + new_length
            if new_length > max_clip_length:
                center = best[0] + best[1] * 0.5
                new_length = max_clip_length
                new_start = max(0.0, min(center - new_length * 0.45, duration - new_length))
                new_end = new_start + new_length
            merged[-1] = (
                new_start,
                new_end - new_start,
                best[2],
                best[3],
                f"{best[4]} · séquence continue",
                best[5],
            )
        else:
            merged.append(segment)

    transition_fallback_candidate = best_transition_fallback or best_transition_focus_seed
    if car_profile_active and transition_fallback_candidate is not None:
        transition_focus_max_len = max(min_clip_length + 14.0, min(42.0, max_clip_length * 0.72))
        has_transition_selected = any(
            bool(
                seg_features.get("car_start_event", False)
                or seg_features.get("car_stop_event", False)
                or seg_features.get("car_start_from_scene_cut", False)
                or seg_features.get("car_start_from_inferred", False)
                or seg_features.get("car_start_from_launch", False)
                or seg_features.get("car_insertion_focus", False)
            )
            and (
                float(seg_start) >= 6.0
                or bool(seg_features.get("car_start_from_launch", False))
                or bool(seg_features.get("car_insertion_focus", False))
            )
            and float(seg_length) <= transition_focus_max_len
            for seg_start, seg_length, _, _, _, seg_features in merged
        )
        if not has_transition_selected:
            fb_start, fb_length, _, _, _, _ = transition_fallback_candidate
            fb_end = fb_start + fb_length
            too_close_duplicate = any(
                _temporal_iou(fb_start, fb_end, m_start, m_start + m_length) >= 0.88
                for m_start, m_length, _, _, _, _ in merged
            )
            if not too_close_duplicate:
                LOGGER.info(
                    "Ajout fallback transition voiture: %.1f-%.1f score=%.2f",
                    fb_start,
                    fb_end,
                    transition_fallback_candidate[2],
                )
                merged.append(transition_fallback_candidate)
                merged.sort(key=lambda item: item[0])

    if car_profile_active and best_transition_late_candidate is not None:
        transition_focus_max_len = max(min_clip_length + 14.0, min(42.0, max_clip_length * 0.72))
        has_late_transition_selected = any(
            bool(
                seg_features.get("car_start_event", False)
                or seg_features.get("car_stop_event", False)
                or seg_features.get("car_start_from_scene_cut", False)
                or seg_features.get("car_start_from_inferred", False)
                or seg_features.get("car_start_from_launch", False)
                or seg_features.get("car_insertion_focus", False)
            )
            and late_transition_min_start <= float(seg_start) <= late_transition_max_start
            and float(seg_length) <= transition_focus_max_len + 8.0
            for seg_start, seg_length, _, _, _, seg_features in merged
        )
        if not has_late_transition_selected:
            fb_start, fb_length, _, _, _, _ = best_transition_late_candidate
            fb_end = fb_start + fb_length
            too_close_duplicate = any(
                _temporal_iou(fb_start, fb_end, m_start, m_start + m_length) >= 0.86
                for m_start, m_length, _, _, _, _ in merged
            )
            if not too_close_duplicate:
                LOGGER.info(
                    "Ajout fallback transition voiture (late): %.1f-%.1f score=%.2f",
                    fb_start,
                    fb_end,
                    best_transition_late_candidate[2],
                )
                merged.append(best_transition_late_candidate)
                merged.sort(key=lambda item: item[0])

    if car_profile_active and best_launch_early_candidate is not None:
        has_launch_early_selected = any(
            bool(seg_features.get("car_start_from_launch", False))
            and float(seg_start) <= (launch_early_max_start + 3.0)
            for seg_start, _, _, _, _, seg_features in merged
        )
        if not has_launch_early_selected:
            fb_start, fb_length, _, _, _, _ = best_launch_early_candidate
            fb_end = fb_start + fb_length
            too_close_duplicate = any(
                _temporal_iou(fb_start, fb_end, m_start, m_start + m_length) >= 0.84
                for m_start, m_length, _, _, _, _ in merged
            )
            if not too_close_duplicate:
                LOGGER.info(
                    "Ajout fallback départ lancé (early): %.1f-%.1f score=%.2f",
                    fb_start,
                    fb_end,
                    best_launch_early_candidate[2],
                )
                merged.append(best_launch_early_candidate)
                merged.sort(key=lambda item: item[0])

    if car_profile_active and best_launch_late_candidate is not None:
        has_launch_late_selected = any(
            bool(seg_features.get("car_start_from_launch", False))
            and late_transition_min_start <= float(seg_start) <= late_transition_max_start
            for seg_start, _, _, _, _, seg_features in merged
        )
        if not has_launch_late_selected:
            fb_start, fb_length, _, _, _, _ = best_launch_late_candidate
            fb_end = fb_start + fb_length
            too_close_duplicate = any(
                _temporal_iou(fb_start, fb_end, m_start, m_start + m_length) >= 0.84
                for m_start, m_length, _, _, _, _ in merged
            )
            if not too_close_duplicate:
                LOGGER.info(
                    "Ajout fallback départ lancé (late): %.1f-%.1f score=%.2f",
                    fb_start,
                    fb_end,
                    best_launch_late_candidate[2],
                )
                merged.append(best_launch_late_candidate)
                merged.sort(key=lambda item: item[0])

    if car_profile_active and best_insertion_candidate is not None:
        has_insertion_selected = any(
            (
                bool(seg_features.get("car_insertion_focus", False))
                or (
                    bool(seg_features.get("car_transition_focus", False))
                    and not bool(seg_features.get("car_start_from_launch", False))
                    and (
                        bool(seg_features.get("car_start_from_scene_cut", False))
                        or bool(seg_features.get("car_start_from_inferred", False))
                        or bool(seg_features.get("car_start_from_visual", False))
                        or bool(seg_features.get("car_start_from_yamnet", False))
                    )
                )
            )
            and insertion_min_start <= float(seg_start) <= insertion_max_start
            and float(seg_length) <= insertion_focus_max_len
            for seg_start, seg_length, _, _, _, seg_features in merged
        )
        if not has_insertion_selected:
            fb_start, fb_length, _, _, _, _ = best_insertion_candidate
            fb_end = fb_start + fb_length
            too_close_duplicate = any(
                _temporal_iou(fb_start, fb_end, m_start, m_start + m_length) >= 0.84
                for m_start, m_length, _, _, _, _ in merged
            )
            if not too_close_duplicate:
                LOGGER.info(
                    "Ajout fallback insertion voiture: %.1f-%.1f score=%.2f",
                    fb_start,
                    fb_end,
                    best_insertion_candidate[2],
                )
                merged.append(best_insertion_candidate)
                merged.sort(key=lambda item: item[0])

    if car_profile_active and len(merged) > 1:
        chain_gap_threshold = max(0.4, ANALYSIS_WINDOW_SECONDS * 2.2)
        short_chain_limit = max(
            min_clip_length + 2.0,
            min(32.0, max_clip_length * 0.45),
        )

        def _segment_role(seg_features: dict[str, Any]) -> str:
            if seg_features.get("car_start_from_launch", False):
                return "launch"
            if seg_features.get("car_insertion_focus", False):
                return "insertion"
            if (
                seg_features.get("car_presentation_like", False)
                or seg_features.get("car_showcase_event", False)
                or seg_features.get("ollama_vision_showcase", False)
            ):
                return "presentation"
            if (
                seg_features.get("car_transition_focus", False)
                or seg_features.get("car_start_event", False)
                or seg_features.get("car_stop_event", False)
            ):
                return "transition"
            return "other"

        consolidated: list[tuple[float, float, float, str, str, dict]] = []
        for segment in merged:
            if not consolidated:
                consolidated.append(segment)
                continue

            prev_start, prev_length, prev_score, prev_tag, prev_reason, prev_features = consolidated[-1]
            prev_end = prev_start + prev_length
            start, length, score, tag, reason, features = segment
            gap = max(0.0, start - prev_end)

            prev_role = _segment_role(prev_features)
            cur_role = _segment_role(features)
            both_short = prev_length <= short_chain_limit and length <= short_chain_limit
            compatible_roles = bool(
                prev_role == cur_role
                or (
                    both_short
                    and prev_role in {"transition", "insertion", "other"}
                    and cur_role in {"transition", "insertion", "other"}
                )
            )
            protected_pair = bool(
                {"launch", "presentation"} == {prev_role, cur_role}
                or {"launch", "insertion"} == {prev_role, cur_role}
                or {"insertion", "presentation"} == {prev_role, cur_role}
            )

            if (
                gap <= chain_gap_threshold
                and compatible_roles
                and not protected_pair
            ):
                new_start = min(prev_start, start)
                new_end = max(prev_end, start + length)
                new_length = new_end - new_start
                if new_length <= max_clip_length:
                    best = (prev_score, prev_tag, prev_reason, prev_features)
                    if score > prev_score:
                        best = (score, tag, reason, features)
                    merged_features = dict(best[3])
                    bool_union_keys = (
                        "car_start_event",
                        "car_stop_event",
                        "car_start_from_launch",
                        "car_insertion_focus",
                        "car_transition_focus",
                        "car_transition_fallback",
                        "car_presentation_like",
                        "car_showcase_event",
                        "car_stationary_showcase_event",
                        "ollama_vision_showcase",
                    )
                    for key in bool_union_keys:
                        merged_features[key] = bool(
                            prev_features.get(key, False) or features.get(key, False)
                        )
                    merged_features["car_start_score"] = max(
                        float(prev_features.get("car_start_score", 0.0)),
                        float(features.get("car_start_score", 0.0)),
                    )
                    merged_features["car_stop_score"] = max(
                        float(prev_features.get("car_stop_score", 0.0)),
                        float(features.get("car_stop_score", 0.0)),
                    )
                    merged_features["car_insertion_focus_score"] = max(
                        float(prev_features.get("car_insertion_focus_score", 0.0)),
                        float(features.get("car_insertion_focus_score", 0.0)),
                    )
                    merged_score = max(prev_score, score)
                    merged_features["score"] = round(merged_score, 3)
                    merged_reason = f"{best[2]} · fusion segments consecutifs"
                    merged_text_features = {
                        "text_tag": merged_features.get("text_tag", ""),
                        "text_score": float(merged_features.get("text_score", 0.0)),
                        "words_per_sec": float(merged_features.get("words_per_sec", 0.0)),
                        "dialogue_hits": int(merged_features.get("dialogue_hits", 0)),
                        "has_story_end": bool(merged_features.get("has_story_end", False)),
                        "has_hook": bool(merged_features.get("has_hook", False)),
                        "has_punchline": bool(merged_features.get("has_punchline", False)),
                    }
                    merged_features["tiktok_title"] = _build_tiktok_title(
                        best[1],
                        new_start,
                        new_end,
                        transcript_segments,
                        merged_text_features,
                        audio_features=merged_features,
                    )
                    consolidated[-1] = (
                        new_start,
                        new_length,
                        round(merged_score, 3),
                        best[1],
                        merged_reason,
                        merged_features,
                    )
                    continue

            consolidated.append(segment)

        if len(consolidated) != len(merged):
            LOGGER.info(
                "Fusion clips consecutifs: %d -> %d",
                len(merged),
                len(consolidated),
            )
        merged = consolidated

    if car_profile_active and len(merged) > 1:
        # Secondary compaction: avoid side-by-side duplicates by merging close clips
        # with similar intent (or keeping the best one if merge would be too long).
        timeline_gap_threshold = max(2.0, ANALYSIS_WINDOW_SECONDS * 4.0)
        timeline_iou_threshold = 0.32

        def _timeline_role(seg_features: dict[str, Any]) -> str:
            if seg_features.get("car_start_from_launch", False):
                return "launch"
            if seg_features.get("car_insertion_focus", False):
                return "insertion"
            if (
                seg_features.get("car_presentation_like", False)
                or seg_features.get("car_showcase_event", False)
                or seg_features.get("ollama_vision_showcase", False)
            ):
                return "presentation"
            if (
                seg_features.get("car_transition_focus", False)
                or seg_features.get("car_start_event", False)
                or seg_features.get("car_stop_event", False)
            ):
                return "transition"
            return "other"

        def _timeline_priority(
            role: str,
            score_value: float,
            length_value: float,
            insertion_score: float,
        ) -> float:
            role_bonus = {
                "launch": 0.19,
                "insertion": 0.22,
                "presentation": 0.12,
                "transition": 0.07,
                "other": 0.0,
            }.get(role, 0.0)
            length_bonus = min(max(float(length_value), 0.0), 80.0) / 600.0
            insertion_bonus = min(max(float(insertion_score), 0.0), 1.0) * 0.06
            return float(score_value) + role_bonus + length_bonus + insertion_bonus

        compacted: list[tuple[float, float, float, str, str, dict]] = []
        for segment in sorted(merged, key=lambda item: item[0]):
            if not compacted:
                compacted.append(segment)
                continue

            prev_start, prev_length, prev_score, prev_tag, prev_reason, prev_features = compacted[-1]
            prev_end = prev_start + prev_length
            start, length, score, tag, reason, features = segment
            end = start + length

            iou = _temporal_iou(prev_start, prev_end, start, end)
            gap = max(0.0, start - prev_end)
            close_in_timeline = bool(iou >= timeline_iou_threshold or gap <= timeline_gap_threshold)

            prev_role = _timeline_role(prev_features)
            cur_role = _timeline_role(features)
            similar_role = bool(
                prev_role == cur_role
                or ({prev_role, cur_role} <= {"transition", "other"})
                or ({prev_role, cur_role} <= {"presentation", "other"})
                or ({prev_role, cur_role} <= {"presentation", "transition"})
                or ({prev_role, cur_role} <= {"launch", "insertion", "transition"})
            )
            protected_pair = bool(
                {"launch", "presentation"} == {prev_role, cur_role}
                or {"insertion", "presentation"} == {prev_role, cur_role}
            )

            if not close_in_timeline or not similar_role or protected_pair:
                compacted.append(segment)
                continue

            new_start = min(prev_start, start)
            new_end = max(prev_end, end)
            new_length = new_end - new_start

            if new_length <= max_clip_length:
                best = (prev_start, prev_length, prev_score, prev_tag, prev_reason, prev_features)
                if _timeline_priority(
                    cur_role,
                    score,
                    length,
                    float(features.get("car_insertion_focus_score", 0.0)),
                ) > _timeline_priority(
                    prev_role,
                    prev_score,
                    prev_length,
                    float(prev_features.get("car_insertion_focus_score", 0.0)),
                ):
                    best = (start, length, score, tag, reason, features)

                merged_features = dict(best[5])
                bool_union_keys = (
                    "car_start_event",
                    "car_stop_event",
                    "car_start_from_launch",
                    "car_start_from_audio",
                    "car_start_from_visual",
                    "car_start_from_scene_cut",
                    "car_start_from_inferred",
                    "car_start_from_yamnet",
                    "car_insertion_focus",
                    "car_transition_focus",
                    "car_transition_fallback",
                    "car_presentation_like",
                    "car_showcase_event",
                    "car_stationary_showcase_event",
                    "ollama_vision_showcase",
                )
                for key in bool_union_keys:
                    merged_features[key] = bool(
                        prev_features.get(key, False) or features.get(key, False)
                    )
                merged_features["car_start_score"] = max(
                    float(prev_features.get("car_start_score", 0.0)),
                    float(features.get("car_start_score", 0.0)),
                )
                merged_features["car_stop_score"] = max(
                    float(prev_features.get("car_stop_score", 0.0)),
                    float(features.get("car_stop_score", 0.0)),
                )
                merged_features["car_insertion_focus_score"] = max(
                    float(prev_features.get("car_insertion_focus_score", 0.0)),
                    float(features.get("car_insertion_focus_score", 0.0)),
                )
                merged_score = max(prev_score, score)
                merged_features["score"] = round(merged_score, 3)
                merged_reason = f"{best[4]} · regroupement timeline"
                merged_text_features = {
                    "text_tag": merged_features.get("text_tag", ""),
                    "text_score": float(merged_features.get("text_score", 0.0)),
                    "words_per_sec": float(merged_features.get("words_per_sec", 0.0)),
                    "dialogue_hits": int(merged_features.get("dialogue_hits", 0)),
                    "has_story_end": bool(merged_features.get("has_story_end", False)),
                    "has_hook": bool(merged_features.get("has_hook", False)),
                    "has_punchline": bool(merged_features.get("has_punchline", False)),
                }
                merged_features["tiktok_title"] = _build_tiktok_title(
                    best[3],
                    new_start,
                    new_end,
                    transcript_segments,
                    merged_text_features,
                    audio_features=merged_features,
                )
                compacted[-1] = (
                    new_start,
                    new_length,
                    round(merged_score, 3),
                    best[3],
                    merged_reason,
                    merged_features,
                )
                continue

            prev_priority = _timeline_priority(
                prev_role,
                prev_score,
                prev_length,
                float(prev_features.get("car_insertion_focus_score", 0.0)),
            )
            cur_priority = _timeline_priority(
                cur_role,
                score,
                length,
                float(features.get("car_insertion_focus_score", 0.0)),
            )
            if cur_priority > prev_priority:
                compacted[-1] = segment

        if len(compacted) != len(merged):
            LOGGER.info(
                "Consolidation anti-enchainement clips: %d -> %d",
                len(merged),
                len(compacted),
            )
        merged = compacted

    return merged

def _fallback_segments(
    duration: float,
    seed: str,
    min_clip_length: float | None = None,
    max_clip_length: float | None = None,
) -> list[tuple[float, float, float, str, str, dict]]:
    min_len = CLIP_MIN_SECONDS if min_clip_length is None else float(min_clip_length)
    max_len = CLIP_MAX_SECONDS if max_clip_length is None else float(max_clip_length)
    if max_len <= min_len:
        max_len = min_len + 5.0

    rng = random.Random(seed)
    if duration <= 12:
        return [(0.0, duration, 0.3, "moment", "segment court", {"score": 0.3})]
    if duration <= min_len:
        return [(0.0, duration, 0.3, "moment", "vidéo plus courte que la cible", {"score": 0.3})]

    target = max(1, min(4, int(duration / max(min_len, 60.0)) + 1))
    step = duration / (target + 1)
    segments: list[tuple[float, float, float, str, str, dict]] = []
    for idx in range(target):
        center = step * (idx + 1) + rng.uniform(-2.0, 2.0)
        base_length = min_len + (max_len - min_len) * 0.45
        length = max(min_len, min(max_len, base_length + rng.uniform(-6.0, 8.0)))
        length = min(length, duration)
        start = max(0.0, min(center - length * 0.4, duration - length))
        segments.append((start, length, 0.3, "moment", "segment régulier", {"score": 0.3}))
    return segments










