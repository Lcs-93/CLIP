from __future__ import annotations

from typing import Any

from worker.worker_config import (
    ANALYSIS_WINDOW_SECONDS,
    CAR_ACCEL_THRESHOLD,
    CAR_EVENT_MIN_SCORE,
    CAR_MIN_SUSTAIN_SECONDS,
)
from worker.worker_keywords import (
    DIALOGUE_MARKERS,
    EMOTION_INTENSIFIERS,
    HOOK_MARKERS,
    LAUGHTER_TOKENS,
    PUNCHLINE_MARKERS,
    TAG_KEYWORDS,
)
from worker.worker_utils import _window_slice


def _feature_bundle(values: list[float], index: int, avg: float, deviation: float) -> dict:
    energy = values[index]
    delta = max(0.0, energy - values[index - 1] if index > 0 else energy)
    silence_start, silence_end = _window_slice(values, index, 3.0, ANALYSIS_WINDOW_SECONDS)
    silence_threshold = max(0.06, avg * 0.6)
    silence_vals = values[silence_start:index]
    silence_before = (
        sum(1 for value in silence_vals if value <= silence_threshold) / len(silence_vals)
        if silence_vals
        else 0.0
    )
    density_start, density_end = _window_slice(values, index, 5.0, ANALYSIS_WINDOW_SECONDS)
    density_threshold = avg + deviation * 0.4
    density_vals = values[density_start : density_end + 1]
    density = (
        sum(1 for value in density_vals if value >= density_threshold) / len(density_vals)
        if density_vals
        else 0.0
    )
    score = energy * 0.45 + delta * 0.2 + silence_before * 0.2 + density * 0.15
    return {
        "energy": round(energy, 3),
        "delta": round(delta, 3),
        "silence_before": round(silence_before, 3),
        "density": round(density, 3),
        "score": round(score, 3),
    }


def _tag_and_reason(
    audio_features: dict, text_features: dict | None = None
) -> tuple[str, str, list[str]]:
    """Compute default tag/reason/signals, then enrich with text signals when available."""
    energy = audio_features["energy"]
    delta = audio_features["delta"]
    silence_before = audio_features["silence_before"]
    density = audio_features["density"]

    car_accel_score = float(audio_features.get("car_accel_score", 0.0))
    car_sustain_seconds = float(audio_features.get("car_sustain_seconds", 0.0))
    car_start_score = float(audio_features.get("car_start_score", 0.0))
    car_stop_score = float(audio_features.get("car_stop_score", 0.0))
    car_object_score = float(audio_features.get("car_object_score", 0.0))
    has_car_start_yamnet = bool(audio_features.get("car_start_from_yamnet", False))
    has_car_stop_yamnet = bool(audio_features.get("car_stop_from_yamnet", False))
    visual_motion_score = float(audio_features.get("visual_motion_score", 0.0))
    has_visual_motion = bool(
        audio_features.get("visual_motion_event", False)
        or visual_motion_score >= float(audio_features.get("visual_event_min_score", 0.45))
    )
    facial_emotion_score = float(audio_features.get("facial_emotion_score", 0.0))
    has_facial_emotion = bool(
        audio_features.get("facial_emotion_event", False)
        or facial_emotion_score >= float(audio_features.get("facial_emotion_event_min_score", 0.52))
    )
    opensmile_voice_score = float(audio_features.get("opensmile_voice_score", 0.0))
    has_opensmile_voice = bool(
        audio_features.get("opensmile_voice_event", False)
        or opensmile_voice_score >= float(audio_features.get("opensmile_event_min_score", 0.55))
    )
    speech_context_ratio = float(audio_features.get("speech_context_ratio", 0.0))
    music_context_ratio = float(audio_features.get("music_context_ratio", 0.0))
    noise_context_ratio = float(audio_features.get("noise_context_ratio", 0.0))
    speaker_change_score = float(audio_features.get("speaker_change_score", 0.0))
    has_speaker_change = bool(
        audio_features.get("speaker_change_event", False)
        or speaker_change_score >= 0.5
    )
    car_event_min_score = float(audio_features.get("car_event_min_score", CAR_EVENT_MIN_SCORE))
    has_car_start_audio = bool(audio_features.get("car_start_from_audio", False))
    has_car_start_visual = bool(audio_features.get("car_start_from_visual", False))
    has_car_start_inferred = bool(audio_features.get("car_start_from_inferred", False))
    has_car_start_scene_cut = bool(audio_features.get("car_start_from_scene_cut", False))
    has_car_start = bool(
        audio_features.get("car_start_event", False)
        or car_start_score >= car_event_min_score
    )
    has_car_stop = bool(
        audio_features.get("car_stop_event", False)
        or car_stop_score >= car_event_min_score
    )
    has_car_showcase = bool(
        audio_features.get("car_showcase_event", False)
        or audio_features.get("car_presentation_like", False)
        or audio_features.get("car_stationary_showcase_event", False)
    )
    has_car_stationary_showcase = bool(
        audio_features.get("car_stationary_showcase_event", False)
    )
    has_car_object = bool(
        audio_features.get("car_object_event", False)
        or car_object_score >= float(audio_features.get("object_car_min_score", 0.34))
    )
    has_car_insertion = bool(audio_features.get("car_insertion_focus", False))
    has_car_launch = bool(audio_features.get("car_start_from_launch", False))
    start_confirmation_count = sum(
        1
        for flag in (
            has_car_launch,
            has_car_start_audio,
            has_car_start_visual,
            has_car_start_inferred,
            has_car_start_scene_cut,
            has_car_start_yamnet,
        )
        if flag
    )
    has_car_start_confident = bool(
        has_car_start
        and (
            has_car_launch
            or start_confirmation_count >= 2
            or car_start_score >= max(car_event_min_score + 0.08, 0.62)
        )
    )
    car_sustained = bool(
        audio_features.get("car_sustained", False)
        or car_sustain_seconds >= CAR_MIN_SUSTAIN_SECONDS
    )
    strong_car_signal = car_accel_score >= CAR_ACCEL_THRESHOLD and car_sustained
    car_exterior_hint = bool(audio_features.get("car_exterior_tour_text_hint", False))
    vision_showcase = bool(audio_features.get("ollama_vision_showcase", False))
    vision_scene = str(audio_features.get("ollama_vision_scene", "")).strip().lower()
    visual_event_min_score = float(audio_features.get("visual_event_min_score", 0.45))
    driving_like_car_clip = bool(
        not has_car_stationary_showcase
        and not car_exterior_hint
        and not vision_showcase
        and (
            has_car_insertion
            or has_car_start_confident
            or strong_car_signal
            or vision_scene == "driving"
            or visual_motion_score >= max(0.62, visual_event_min_score * 1.35)
        )
    )
    showcase_for_tag = bool(
        has_car_showcase
        and (has_car_stationary_showcase or not driving_like_car_clip)
    )

    audio_signals: list[str] = []
    if energy >= 0.6:
        audio_signals.append("hausse energie audio")
    if delta >= 0.15:
        audio_signals.append("rupture de rythme")
    if silence_before >= 0.3:
        audio_signals.append("silence puis reprise")
    if density >= 0.35:
        audio_signals.append("densite audio elevee")
    if strong_car_signal:
        audio_signals.append("acceleration moteur")
    if has_car_start_confident:
        audio_signals.append("depart voiture")
    elif has_car_start and strong_car_signal:
        audio_signals.append("reprise dynamique voiture")
    if has_car_stop:
        audio_signals.append("arret/freinage voiture")
    if showcase_for_tag:
        audio_signals.append("presentation voiture")
    if has_car_stationary_showcase:
        audio_signals.append("presentation voiture a l'arret")
    elif has_car_showcase and driving_like_car_clip:
        audio_signals.append("conduite autoroute")
    if has_car_object:
        audio_signals.append("voiture visible (objet ia)")
    if has_car_insertion:
        audio_signals.append("insertion autoroute")
    if has_visual_motion:
        audio_signals.append("mouvement visuel fort")
    if has_facial_emotion:
        audio_signals.append("emotion faciale detectee")
    if has_opensmile_voice:
        audio_signals.append("prosodie vocale forte")
    if speech_context_ratio >= 0.45:
        audio_signals.append("parole dominante")
    if music_context_ratio >= 0.40 and speech_context_ratio >= 0.45:
        audio_signals.append("mix parole + musique")
    if noise_context_ratio >= 0.50:
        audio_signals.append("bruit dominant")
    if has_speaker_change:
        audio_signals.append("changement de locuteur")
    if has_car_start_yamnet:
        audio_signals.append("ia audio confirme depart")
    if has_car_stop_yamnet:
        audio_signals.append("ia audio confirme arret")

    if (
        has_car_stationary_showcase
        and not has_car_insertion
        and not has_car_launch
        and not has_car_start_confident
    ):
        tag = "presentation"
        reason = "presentation voiture a l'arret"
    elif (
        showcase_for_tag
        and not has_car_insertion
        and not has_car_launch
        and not has_car_start_confident
    ):
        tag = "presentation"
        reason = "presentation detaillee de la voiture"
    elif has_car_insertion and (has_car_start_confident or strong_car_signal):
        tag = "action"
        reason = "insertion autoroute et reprise franche"
    elif has_car_start_confident and strong_car_signal:
        tag = "action"
        reason = "depart voiture + acceleration"
    elif has_car_stop and strong_car_signal:
        tag = "tension"
        reason = "freinage / arret marque"
    elif has_car_start and strong_car_signal:
        tag = "action"
        reason = "reprise dynamique voiture"
    elif strong_car_signal and energy >= 0.55:
        tag = "action"
        reason = "acceleration moteur marquee"
    elif has_car_start_confident:
        tag = "action"
        reason = "depart de voiture detecte"
    elif has_car_stop:
        tag = "surprise"
        reason = "arret/freinage de voiture detecte"
    elif showcase_for_tag:
        tag = "presentation"
        reason = "presentation detaillee de la voiture"
    elif energy >= 0.8 and density >= 0.45:
        tag = "action"
        reason = "energie elevee et rythme soutenu"
    elif delta >= 0.22 and silence_before >= 0.25:
        tag = "surprise"
        reason = "silence puis hausse brusque"
    elif density >= 0.45 and energy >= 0.55:
        tag = "tension"
        reason = "rythme dense et soutenu"
    elif energy >= 0.65:
        tag = "moment fort"
        reason = "montee d'energie perceptible"
    elif has_speaker_change and speech_context_ratio >= 0.45:
        tag = "dialogue"
        reason = "changement de locuteur et parole active"
    elif has_facial_emotion:
        tag = "emotion"
        reason = "reaction faciale marquee"
    else:
        tag = "moment"
        reason = "variation audio moderee"

    signals = audio_signals[:]

    if text_features:
        text_tag = text_features.get("text_tag")
        text_reason = text_features.get("text_reason")
        text_signals = text_features.get("signals", [])

        if text_tag and text_tag != "promo":
            tag = text_tag
        if text_reason:
            reason = text_reason

        signals = text_signals + signals

        story_score = text_features.get("story_score", 0)
        if story_score >= 0.6 and "bonne narration" not in signals:
            signals.insert(0, "bonne narration")

        if text_features.get("is_mid_thought") and "coupe en milieu" not in signals:
            signals.append("coupe en milieu")

    return tag, reason, signals[:4]
