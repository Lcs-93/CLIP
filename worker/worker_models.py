from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SignalType(Enum):
    """Types de signaux pour la détection des points de coupe."""

    PAUSE_SHORT = "pause_short"       # Pause courte entre mots
    PAUSE_LONG = "pause_long"         # Pause longue (fin de phrase)
    PAUSE_PARAGRAPH = "pause_para"    # Pause très longue (fin de paragraphe)
    SENTENCE_END = "sentence_end"     # Fin de phrase (ponctuation)
    STORY_START = "story_start"       # Début d'histoire détecté
    STORY_END = "story_end"           # Fin d'histoire détectée
    SPEAKER_CHANGE = "speaker_change" # Changement de locuteur
    SCENE_CUT = "scene_cut"           # Changement de scène vidéo
    PITCH_FALLING = "pitch_fall"      # Intonation descendante (fin naturelle)
    PITCH_RISING = "pitch_rise"       # Intonation montante (question/incomplet)
    GRAMMAR_COMPLETE = "grammar_ok"   # Phrase grammaticalement complète
    GRAMMAR_INCOMPLETE = "grammar_bad" # Phrase incomplète
    SILENCE_AUDIO = "silence"         # Silence dans l'audio (RMS bas)
    VAD_SILENCE = "vad_silence"       # Silence détecté par VAD (voix absente)


@dataclass
class CutSignal:
    """Un signal de point de coupe potentiel."""

    time: float                    # Timestamp en secondes
    signal_type: SignalType        # Type de signal
    score: float                   # Score de qualité (0.0 - 1.0)
    is_good_for_start: bool        # Bon pour début de clip ?
    is_good_for_end: bool          # Bon pour fin de clip ?
    source: str = ""               # Source du signal (debug)

    def __repr__(self) -> str:
        return (
            f"CutSignal({self.time:.2f}s, {self.signal_type.value}, "
            f"score={self.score:.2f})"
        )
