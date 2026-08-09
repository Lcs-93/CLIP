from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from worker.worker_config import (
    ENABLE_KEYBERT,
    KEYBERT_LOCAL_ONLY,
    KEYBERT_MODEL_NAME,
    MAX_CLIP_LENGTH,
    MIN_CLIP_LENGTH,
    MIN_DISTANCE_SECONDS,
    SENTENCE_END_PATTERNS,
    WORD_RE,
)
from worker.worker_keywords import (
    COMMERCIAL_KEYWORDS,
    COMMERCIAL_PHRASES,
    DIALOGUE_MARKERS,
    EMOTION_INTENSIFIERS,
    FORBIDDEN_END_WORDS,
    HOOK_MARKERS,
    LAUGHTER_TOKENS,
    MID_THOUGHT_MARKERS,
    PHRASE_KEYWORDS,
    PUNCHLINE_MARKERS,
    STORY_CLIMAX_MARKERS,
    STORY_CONTINUATION_MARKERS,
    STORY_END_MARKERS,
    STORY_START_MARKERS,
    TAG_KEYWORDS,
)
from worker.worker_logging import LOGGER

# KeyBERT pour extraction de mots-cles saillants (optionnel)
try:
    from keybert import KeyBERT

    KEYBERT_AVAILABLE = True
except Exception:
    KeyBERT = None
    KEYBERT_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except Exception:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False

_KEYBERT_MODEL: Any | None = None
_KEYBERT_DISABLED = False

# spaCy pour analyse grammaticale fran?aise
try:
    import spacy
    SPACY_NLP = spacy.load("fr_core_news_md")
    SPACY_AVAILABLE = True
    LOGGER.info("spaCy charg? avec mod?le fr_core_news_md")
except Exception:
    SPACY_NLP = None
    SPACY_AVAILABLE = False


@lru_cache(maxsize=2048)
def _lemmatize_cached(text: str) -> tuple[str, ...]:
    if not SPACY_AVAILABLE or SPACY_NLP is None:
        return ()
    try:
        doc = SPACY_NLP(text)
        return tuple(
            token.lemma_.lower()
            for token in doc
            if not token.is_punct and not token.is_space
        )
    except Exception as e:
        LOGGER.debug("spaCy lemmatization failed: %s", e)
        return ()


def _get_keybert_model() -> Any | None:
    if not KEYBERT_AVAILABLE or KeyBERT is None:
        return None
    global _KEYBERT_MODEL, _KEYBERT_DISABLED
    if _KEYBERT_DISABLED:
        return None
    if _KEYBERT_MODEL is None:
        model_name = KEYBERT_MODEL_NAME.strip() or "all-MiniLM-L6-v2"
        try:
            if KEYBERT_LOCAL_ONLY:
                if not SENTENCE_TRANSFORMERS_AVAILABLE or SentenceTransformer is None:
                    LOGGER.warning(
                        "KeyBERT local-only requested but sentence-transformers is unavailable"
                    )
                    _KEYBERT_DISABLED = True
                    return None
                sentence_model = SentenceTransformer(model_name, local_files_only=True)
                _KEYBERT_MODEL = KeyBERT(model=sentence_model)
            else:
                _KEYBERT_MODEL = KeyBERT(model=model_name)
            LOGGER.info(
                "KeyBERT loaded (model=%s, local_only=%s)",
                model_name,
                KEYBERT_LOCAL_ONLY,
            )
        except Exception as e:
            LOGGER.warning(
                "KeyBERT init failed (model=%s, local_only=%s): %s",
                model_name,
                KEYBERT_LOCAL_ONLY,
                e,
            )
            _KEYBERT_DISABLED = True
            return None
    return _KEYBERT_MODEL


@lru_cache(maxsize=512)
def _keybert_extract_cached(text: str) -> tuple[tuple[str, float], ...]:
    model = _get_keybert_model()
    if model is None:
        return ()
    try:
        keywords = model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 2),
            stop_words="french",
            top_n=5,
        )
        return tuple((kw, float(score)) for kw, score in keywords)
    except Exception as e:
        LOGGER.debug("KeyBERT failed: %s", e)
        return ()


def _marker_positions(text: str, markers: set[str]) -> list[int]:
    positions: list[int] = []
    if not text:
        return positions
    for marker in markers:
        start = 0
        while True:
            idx = text.find(marker, start)
            if idx == -1:
                break
            positions.append(idx)
            start = idx + 1
    return positions


def _analyze_grammar_ending(text: str) -> dict[str, Any]:
    """
    Utilise spaCy pour analyser si la fin du texte est grammaticalement complète.
    
    Retourne:
    - is_complete: bool - La phrase est grammaticalement complète
    - last_word_pos: str - Part-of-speech du dernier mot
    - forbidden_end: bool - Le texte se termine sur un mot interdit
    - grammar_score: float - Score de qualité grammaticale (0-1)
    """
    default = {
        "is_complete": True,
        "last_word_pos": "unknown",
        "forbidden_end": False,
        "grammar_score": 0.5,
    }
    
    if not text or not text.strip():
        return default
    
    text = text.strip()
    words = text.split()
    
    if not words:
        return default
    
    last_word = words[-1].lower().rstrip(".,!?;:")
    
    # Check FORBIDDEN_END_WORDS
    forbidden_end = last_word in FORBIDDEN_END_WORDS
    
    # Analyse avec spaCy si disponible
    if SPACY_AVAILABLE and SPACY_NLP is not None:
        try:
            doc = SPACY_NLP(text)
            
            # Trouve le dernier token significatif (pas ponctuation)
            last_token = None
            for token in reversed(doc):
                if not token.is_punct and not token.is_space:
                    last_token = token
                    break
            
            if last_token:
                pos = last_token.pos_
                dep = last_token.dep_
                
                # POS tags problématiques en fin de phrase
                incomplete_pos = {"ADP", "DET", "CCONJ", "SCONJ", "AUX", "PRON"}
                # Dépendances problématiques (attendent un complément)
                incomplete_dep = {"aux", "det", "prep", "mark", "cc", "case"}
                
                is_complete = pos not in incomplete_pos and dep not in incomplete_dep
                grammar_score = 0.9 if is_complete else 0.2
                
                return {
                    "is_complete": is_complete and not forbidden_end,
                    "last_word_pos": pos,
                    "forbidden_end": forbidden_end,
                    "grammar_score": 0.1 if forbidden_end else grammar_score,
                }
                
        except Exception as e:
            LOGGER.debug("spaCy analysis failed: %s", e)
    
    # Fallback: utilise juste FORBIDDEN_END_WORDS
    return {
        "is_complete": not forbidden_end,
        "last_word_pos": "unknown",
        "forbidden_end": forbidden_end,
        "grammar_score": 0.1 if forbidden_end else 0.5,
    }

def _is_commercial_content(text: str) -> tuple[bool, float]:
    """
    Détecte si le texte contient du contenu commercial/promotionnel.
    Retourne (is_commercial, penalty_score) où penalty_score est entre 0 et 1.
    """
    if not text:
        return False, 0.0
    
    lower = text.lower()
    penalty = 0.0

    # Signaux forts explicites (pub/sponsor/code/lien) -> pénalité immédiate.
    strong_markers = (
        "sponsor",
        "sponsorisé",
        "sponsorisée",
        "en partenariat",
        "partenariat",
        "code promo",
        "use code",
        "lien en description",
        "lien dans la description",
        "lien en bio",
        "affiliate",
        "affilié",
    )
    if any(marker in lower for marker in strong_markers):
        penalty += 0.45

    # Check phrases commerciales (plus fort poids)
    for phrase in COMMERCIAL_PHRASES:
        if phrase in lower:
            penalty += 0.4
    
    # Check mots-clés commerciaux
    words = set(WORD_RE.findall(lower))
    commercial_hits = sum(1 for kw in COMMERCIAL_KEYWORDS if kw in lower or kw in words)
    penalty += commercial_hits * 0.15

    # Combos typiques "code + promo/réduc" ou "lien + bio/description".
    if "code" in words and any(token in words for token in {"promo", "reduction", "réduction"}):
        penalty += 0.20
    if "lien" in words and any(token in words for token in {"bio", "description"}):
        penalty += 0.18

    # Plafonne à 1.0
    penalty = min(1.0, penalty)
    
    # Seuil volontairement strict: toute probabilité pub notable doit être filtrée.
    is_commercial = penalty >= 0.2
    return is_commercial, penalty


# ============================================================================
# DÉTECTION ACTIVE DES HISTOIRES (Story Windows)
# ============================================================================

def _find_story_windows(
    transcript_segments: list[dict[str, Any]],
    min_duration: float = MIN_CLIP_LENGTH,
    max_duration: float = MAX_CLIP_LENGTH,
) -> list[dict[str, Any]]:
    """
    Scanne le transcript pour trouver des "story windows" - des fenêtres
    qui contiennent une histoire complète ou un moment intéressant.
    
    Cette fonction permet de trouver des clips qu'on raterait en se basant
    uniquement sur les pics audio (ex: moments calmes mais narrativement forts).
    
    Retourne une liste de candidats avec:
    - start, end: timestamps
    - score: score de qualité narrative
    - reason: pourquoi c'est intéressant
    - text: le texte du segment
    """
    if not transcript_segments:
        return []
    
    candidates = []
    n_segments = len(transcript_segments)
    
    # Sliding window sur le transcript
    for i in range(n_segments):
        start_seg = transcript_segments[i]
        accumulated_text = ""
        
        for j in range(i, n_segments):
            end_seg = transcript_segments[j]
            accumulated_text += " " + end_seg["text"]
            
            duration = end_seg["end"] - start_seg["start"]
            
            # Trop court, continue d'accumuler
            if duration < min_duration:
                continue
            
            # Trop long, passe au prochain point de départ
            if duration > max_duration:
                break
            
            # === QUICK SCORE pour filtrer rapidement ===
            score, reason = _quick_story_score(accumulated_text, start_seg, end_seg, transcript_segments)
            
            # Garde seulement les candidats intéressants
            if score >= 0.35:
                candidates.append({
                    "start": start_seg["start"],
                    "end": end_seg["end"],
                    "score": score,
                    "reason": reason,
                    "text": accumulated_text.strip(),
                    "source": "story_window",
                })
    
    # Déduplique les candidats très proches (garde le meilleur)
    candidates = _dedupe_story_candidates(candidates)
    
    LOGGER.info("Story windows: %d candidats trouvés", len(candidates))
    return candidates

def _quick_story_score(
    text: str,
    start_seg: dict[str, Any],
    end_seg: dict[str, Any],
    transcript_segments: list[dict[str, Any]],
) -> tuple[float, str]:
    """
    Score rapide d'un segment textuel pour déterminer s'il contient
    une histoire intéressante. Pas d'appel Ollama, juste des heuristiques.
    
    Retourne (score, reason).
    """
    lower = text.lower()
    score = 0.0
    reasons = []
    
    # === REJET RAPIDE ===
    
    # Contenu commercial ?
    is_commercial, commercial_penalty = _is_commercial_content(text)
    if commercial_penalty >= 0.4:
        return 0.0, "commercial"
    
    # Pas assez de mots ?
    words = text.split()
    if len(words) < 25:
        return 0.0, "too_short"
    
    # === SCORING POSITIF ===
    
    # 1. Structure narrative (début + fin)
    first_text = start_seg["text"].lower()
    last_text = end_seg["text"].lower()
    
    has_story_start = any(m in first_text for m in STORY_START_MARKERS)
    has_story_end = any(m in last_text for m in STORY_END_MARKERS) or \
                    bool(SENTENCE_END_PATTERNS.search(last_text))
    
    if has_story_start:
        score += 0.25
        reasons.append("story_start")
    
    if has_story_end:
        score += 0.20
        reasons.append("story_end")
    
    # Bonus combo histoire complète
    if has_story_start and has_story_end:
        score += 0.15
        reasons.append("complete_story")
    
    # 2. Hooks (accroche au début) - positionnel
    text_len = max(1, len(lower))
    hook_positions = _marker_positions(lower, HOOK_MARKERS)
    has_hook = any(pos <= text_len * 0.2 for pos in hook_positions)
    if has_hook:
        score += 0.20
        reasons.append("hook")
    
    # 3. Punchlines (à la fin) - positionnel
    punch_positions = _marker_positions(lower, PUNCHLINE_MARKERS)
    has_punchline = any(pos >= text_len * 0.8 for pos in punch_positions)
    if has_punchline:
        score += 0.15
        reasons.append("punchline")
    
    # 4. Climax / Émotion forte
    climax_count = sum(1 for m in STORY_CLIMAX_MARKERS if m in lower)
    if climax_count >= 2:
        score += 0.15
        reasons.append("climax")
    
    # 5. Rires / Humour
    has_laughter = any(token in lower for token in LAUGHTER_TOKENS)
    if has_laughter:
        score += 0.20
        reasons.append("laughter")
    
    # 6. Intensité émotionnelle
    intensifier_count = sum(1 for i in EMOTION_INTENSIFIERS if i in lower)
    if intensifier_count >= 3:
        score += 0.10
        reasons.append("intense")
    
    # 7. Ponctuation expressive
    exclamations = lower.count("!")
    questions = lower.count("?")
    if exclamations + questions >= 3:
        score += 0.10
        reasons.append("expressive")
    
    # 8. Dialogue vif
    dialogue_count = sum(1 for d in DIALOGUE_MARKERS if d in lower)
    if dialogue_count >= 2:
        score += 0.10
        reasons.append("dialogue")
    
    # 9. Densité de parole (mots/seconde)
    duration = end_seg["end"] - start_seg["start"]
    words_per_sec = len(words) / duration if duration > 0 else 0
    if words_per_sec >= 2.0:
        score += 0.10
        reasons.append("dense")
    
    # === PÉNALITÉS ===
    
    # Coupe en milieu de pensée ?
    last_words = last_text.split()[-3:] if last_text else []
    for marker in MID_THOUGHT_MARKERS:
        if any(w in last_words for w in marker.split()):
            score -= 0.15
            reasons.append("mid_thought_penalty")
            break
    
    # Fin sur mot interdit ?
    if last_words:
        final_word = last_words[-1].rstrip(".,!?;:")
        if final_word in FORBIDDEN_END_WORDS:
            score -= 0.20
            reasons.append("forbidden_end_penalty")
    
    # Pénalité commerciale légère
    score -= commercial_penalty * 0.3
    
    # Clamp
    score = max(0.0, min(1.0, score))
    
    reason = "+".join(reasons) if reasons else "none"
    return round(score, 3), reason

def _dedupe_story_candidates(
    candidates: list[dict[str, Any]],
    overlap_threshold: float = 0.6,
) -> list[dict[str, Any]]:
    """
    Déduplique les candidats qui se chevauchent trop.
    Garde le meilleur score pour chaque groupe de chevauchement.
    """
    if not candidates:
        return []
    
    # Trie par score décroissant
    sorted_candidates = sorted(candidates, key=lambda x: -x["score"])
    
    kept = []
    for candidate in sorted_candidates:
        c_start, c_end = candidate["start"], candidate["end"]
        c_duration = c_end - c_start
        
        # Vérifie le chevauchement avec les candidats déjà gardés
        dominated = False
        for kept_candidate in kept:
            k_start, k_end = kept_candidate["start"], kept_candidate["end"]
            
            # Calcul du chevauchement
            overlap_start = max(c_start, k_start)
            overlap_end = min(c_end, k_end)
            overlap_duration = max(0, overlap_end - overlap_start)
            
            overlap_ratio = overlap_duration / c_duration if c_duration > 0 else 0
            
            if overlap_ratio >= overlap_threshold:
                dominated = True
                break
        
        if not dominated:
            kept.append(candidate)
    
    return kept

def _merge_audio_and_story_candidates(
    audio_candidates: list[tuple[int, dict]],
    story_candidates: list[dict[str, Any]],
    series: list[tuple[float, float]],
    min_distance: float = MIN_DISTANCE_SECONDS,
) -> list[dict[str, Any]]:
    """
    Fusionne les candidats audio (pics RMS) et les candidats textuels (story windows).
    Évite les doublons en gardant le meilleur de chaque zone.
    
    Retourne une liste unifiée de candidats avec leur source.
    """
    merged = []
    
    # Convertit les candidats audio en format unifié
    for idx, features in audio_candidates:
        timestamp = series[idx][0]
        candidate_score = float(features.get("merge_score", features["score"]))
        merged.append({
            "center": timestamp,
            "audio_idx": idx,
            "audio_features": features,
            "score": candidate_score,
            "source": "audio_peak",
            "start": None,  # Sera calculé par _expand_arc
            "end": None,
        })
    
    # Ajoute les candidats story
    for story in story_candidates:
        center = (story["start"] + story["end"]) / 2
        
        # Vérifie si ce candidat est trop proche d'un audio existant
        too_close = False
        for existing in merged:
            if abs(center - existing["center"]) < min_distance:
                # Il y a déjà un candidat proche
                if story["score"] > existing["score"]:
                    # Le story est meilleur, on le garde en plus
                    # (sera dédupé plus tard si nécessaire)
                    pass
                else:
                    too_close = True
                    break
        
        if not too_close:
            merged.append({
                "center": center,
                "audio_idx": None,
                "audio_features": None,
                "score": story["score"],
                "source": "story_window",
                "start": story["start"],
                "end": story["end"],
                "story_reason": story["reason"],
                "story_text": story.get("text", "")[:200],  # Tronqué pour mémoire
            })
    
    # Trie par score décroissant
    merged.sort(key=lambda x: -x["score"])
    
    # Garde les meilleurs en respectant la distance minimum
    final = []
    for candidate in merged:
        center = candidate["center"]
        if all(abs(center - f["center"]) >= min_distance for f in final):
            final.append(candidate)
    
    LOGGER.info("Candidats fusionnés: %d audio + %d story → %d total",
                sum(1 for c in final if c["source"] == "audio_peak"),
                sum(1 for c in final if c["source"] == "story_window"),
                len(final))
    
    return final

def _detect_story_structure(
    start: float, end: float, transcript_segments: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Analyse la structure narrative du segment.
    Retourne un dict avec:
    - has_story_start: bool - Segment commence par une intro d'histoire
    - has_story_end: bool - Segment se termine proprement
    - story_score: float - Score de qualité narrative (0-1)
    - story_phase: str - Phase dominante (intro/development/climax/conclusion)
    - is_mid_thought: bool - Coupe en plein milieu d'une pensée
    """
    if not transcript_segments:
        return {
            "has_story_start": False,
            "has_story_end": False,
            "story_score": 0.3,
            "story_phase": "unknown",
            "is_mid_thought": False,
        }
    
    overlaps = [
        seg for seg in transcript_segments 
        if seg["end"] >= start and seg["start"] <= end
    ]
    
    if not overlaps:
        return {
            "has_story_start": False,
            "has_story_end": False,
            "story_score": 0.2,
            "story_phase": "unknown",
            "is_mid_thought": False,
        }
    
    # Texte complet du segment
    full_text = " ".join(seg["text"] for seg in overlaps)
    lower = full_text.lower()
    
    # Premier segment (début du clip)
    first_text = overlaps[0]["text"].lower() if overlaps else ""
    # Dernier segment (fin du clip)
    last_text = overlaps[-1]["text"].lower() if overlaps else ""
    
    # Détection des marqueurs
    has_story_start = any(marker in first_text for marker in STORY_START_MARKERS)
    has_story_end = bool(SENTENCE_END_PATTERNS.search(last_text)) or \
                    any(marker in last_text for marker in STORY_END_MARKERS)
    
    # Vérifie si on coupe en plein milieu d'une pensée
    is_mid_thought = False
    last_words = last_text.split()[-3:] if last_text else []
    for marker in MID_THOUGHT_MARKERS:
        marker_words = marker.split()
        if any(w in last_words for w in marker_words):
            is_mid_thought = True
            break
    
    # Compte les marqueurs de chaque phase
    start_count = sum(1 for m in STORY_START_MARKERS if m in lower)
    continuation_count = sum(1 for m in STORY_CONTINUATION_MARKERS if m in lower)
    climax_count = sum(1 for m in STORY_CLIMAX_MARKERS if m in lower)
    end_count = sum(1 for m in STORY_END_MARKERS if m in lower)
    
    # Détermine la phase dominante
    counts = {
        "intro": start_count,
        "development": continuation_count,
        "climax": climax_count,
        "conclusion": end_count,
    }
    story_phase = max(counts, key=counts.get) if any(counts.values()) else "development"
    
    # Calcul du score narratif
    story_score = 0.3  # Base
    
    # Bonus pour bonne structure
    if has_story_start:
        story_score += 0.2
    if has_story_end:
        story_score += 0.2
    if climax_count > 0:
        story_score += 0.15
    if continuation_count >= 2:
        story_score += 0.1
    
    # Pénalité pour coupe en milieu de pensée
    if is_mid_thought:
        story_score -= 0.25
    
    # Pénalité si pas de structure claire
    if not has_story_start and not has_story_end and climax_count == 0:
        story_score -= 0.1
    
    story_score = max(0.0, min(1.0, story_score))
    
    return {
        "has_story_start": has_story_start,
        "has_story_end": has_story_end,
        "story_score": round(story_score, 3),
        "story_phase": story_phase,
        "is_mid_thought": is_mid_thought,
    }


def _align_to_transcript(
    start: float, end: float, transcript_segments: list[dict[str, Any]]
) -> tuple[float, float, float]:
    if not transcript_segments:
        return start, end, 0.2
    overlaps = [
        seg for seg in transcript_segments if seg["end"] >= start and seg["start"] <= end
    ]
    if not overlaps:
        return start, end, 0.2
    new_start = min(seg["start"] for seg in overlaps)
    new_end = max(seg["end"] for seg in overlaps)
    return new_start, new_end, 0.85

def _text_features_for_range(
    start: float, end: float, transcript_segments: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Analyse enrichie du texte incluant:
    - Détection des mots-clés émotionnels
    - Détection du contenu commercial (pénalité)
    - Analyse de la structure narrative (storytelling)
    """
    empty_result = {
        "text_score": 0.0,
        "words_per_sec": 0.0,
        "keyword_hits": 0,
        "exclamations": 0,
        "questions": 0,
        "text_tag": None,
        "text_reason": None,
        "signals": [],
        "has_hook": False,
        "has_punchline": False,
        "intensifier_hits": 0,
        "dialogue_hits": 0,
        "has_laughter": False,
        "keybert_score": 0.0,
        "keybert_keywords": [],
        "is_commercial": False,
        "commercial_penalty": 0.0,
        "story_score": 0.3,
        "has_story_start": False,
        "has_story_end": False,
        "is_mid_thought": False,
    }
    
    if not transcript_segments:
        return empty_result
    
    overlaps = [
        seg for seg in transcript_segments if seg["end"] >= start and seg["start"] <= end
    ]
    if not overlaps:
        return empty_result
    
    text = " ".join(seg["text"] for seg in overlaps)
    lower = text.lower()
    words = WORD_RE.findall(lower)
    word_count = len(words)
    duration = max(0.1, end - start)
    words_per_sec = word_count / duration

    lemmas: tuple[str, ...] = ()
    if SPACY_AVAILABLE and len(text) <= 2000:
        lemmas = _lemmatize_cached(text)
    token_list = list(lemmas) if lemmas else words
    token_set = set(token_list)

    # ========== DÉTECTION COMMERCIALE ==========
    is_commercial, commercial_penalty = _is_commercial_content(text)
    
    # ========== ANALYSE STORYTELLING ==========
    story_info = _detect_story_structure(start, end, transcript_segments)

    # ========== KEYBERT (mots-clés saillants) ==========
    keybert_keywords: tuple[tuple[str, float], ...] = ()
    keybert_score = 0.0
    if ENABLE_KEYBERT and KEYBERT_AVAILABLE:
        keybert_keywords = _keybert_extract_cached(text)
        if keybert_keywords:
            keybert_score = max(score for _, score in keybert_keywords)

    # ========== ANALYSE ÉMOTIONNELLE CLASSIQUE ==========
    keyword_hits = 0
    tag_hits: dict[str, int] = {}
    for tag, keywords in TAG_KEYWORDS.items():
        hits = sum(1 for word in token_list if word in keywords)
        tag_hits[tag] = hits
        keyword_hits += hits

    phrase_hits: dict[str, int] = {}
    for tag, phrases in PHRASE_KEYWORDS.items():
        count = sum(1 for phrase in phrases if phrase in lower)
        phrase_hits[tag] = count
        keyword_hits += count

    exclamations = lower.count("!")
    questions = lower.count("?")

    laughter = any(token in token_set for token in LAUGHTER_TOKENS)

    # ========== DÉTERMINATION DU TAG INTELLIGENT ==========
    text_tag = None
    
    # Détecte les hooks et punchlines pour les combos (positionnel)
    text_len = max(1, len(lower))
    hook_positions = _marker_positions(lower, HOOK_MARKERS)
    punch_positions = _marker_positions(lower, PUNCHLINE_MARKERS)
    has_hook = any(pos <= text_len * 0.2 for pos in hook_positions)
    has_punchline = any(pos >= text_len * 0.8 for pos in punch_positions)
    has_intensifiers = sum(1 for intens in EMOTION_INTENSIFIERS if intens in lower)
    dialogue_hits = sum(1 for d in DIALOGUE_MARKERS if d in lower)
    
    if is_commercial:
        text_tag = "promo"  # Tag spécial pour le contenu commercial
    elif laughter and story_info["story_score"] >= 0.5:
        text_tag = "histoire drôle"  # COMBO JACKPOT
    elif laughter:
        text_tag = "drôle"
    elif has_hook and has_punchline:
        text_tag = "viral"  # Hook + Payoff = viral potential
    else:
        for tag in ["drôle", "surprise", "révélation", "tension", "action", "émotion"]:
            if tag_hits.get(tag, 0) + phrase_hits.get(tag, 0) > 0:
                text_tag = tag
                break
        # Si pas de tag émotionnel mais bonne structure narrative
        if not text_tag and story_info["story_score"] >= 0.5:
            text_tag = "histoire"
        # Hook seul
        elif not text_tag and has_hook:
            text_tag = "accroche"

    # ========== CALCUL DU SCORE AMÉLIORÉ ==========
    keyword_score = min(1.0, keyword_hits / 3.0)
    punctuation_score = min(1.0, (exclamations + questions) / 4.0)
    density_score = min(1.0, words_per_sec / 2.8)
    
    # Score de base
    base_text_score = keyword_score * 0.4 + punctuation_score * 0.2 + density_score * 0.15
    
    # Ajout du score narratif (nouveau!)
    narrative_bonus = story_info["story_score"] * 0.25
    
    # Calcul final
    keybert_bonus = min(0.08, keybert_score * 0.15)
    text_score = base_text_score + narrative_bonus + keybert_bonus
    
    # Pénalités
    if is_commercial:
        text_score -= commercial_penalty * 0.5  # Forte pénalité pour contenu commercial
    if story_info["is_mid_thought"]:
        text_score -= 0.15  # Pénalité pour coupe en milieu de pensée
    
    text_score = max(0.0, min(1.0, text_score))

    # ========== SIGNAUX ENRICHIS ==========
    signals: list[str] = []
    
    # Signaux prioritaires (combos)
    if laughter and story_info["story_score"] >= 0.5:
        signals.append("🎰 histoire drôle")
    elif has_hook and has_punchline:
        signals.append("🎯 hook+payoff")
    
    # Signaux de qualité
    if is_commercial:
        signals.append("⚠️ contenu commercial")
    if story_info["has_story_start"]:
        signals.append("📖 début d'histoire")
    if story_info["has_story_end"]:
        signals.append("✓ fin propre")
    if story_info["is_mid_thought"]:
        signals.append("⚠️ coupe en milieu")
    if has_hook and not has_punchline:
        signals.append("🎣 hook")
    if has_intensifiers >= 2:
        signals.append("🔥 intense")
    if dialogue_hits >= 2 and "🗣️ dialogue vif" not in signals:
        signals.append("🗣️ dialogue vif")
    if keyword_hits > 0:
        signals.append("💬 émotionnel")
    if punctuation_score >= 0.4:
        signals.append("❗ expressif")
    if density_score >= 0.5 and "🗣️ dialogue vif" not in signals:
        signals.append("🗣️ dialogue vif")
    if keybert_score >= 0.6:
        signals.append("🔑 mots-clés saillants")

    # ========== RAISON INTELLIGENTE ==========
    text_reason = None
    if is_commercial:
        text_reason = "⚠️ Contenu promotionnel détecté"
    elif laughter and story_info["story_score"] >= 0.5:
        text_reason = "🎰 COMBO: histoire drôle complète"
    elif has_hook and has_punchline:
        text_reason = "🎯 COMBO: accroche + conclusion forte"
    elif laughter:
        text_reason = "😂 rires détectés"
    elif story_info["story_score"] >= 0.6:
        text_reason = f"📖 bonne narration ({story_info['story_phase']})"
    elif has_hook:
        text_reason = "🎣 accroche détectée"
    elif keyword_hits > 0:
        text_reason = "💬 mots-clés émotionnels"
    elif punctuation_score >= 0.4:
        text_reason = "❗ forte expressivité"

    return {
        "text_score": round(text_score, 3),
        "words_per_sec": round(words_per_sec, 3),
        "keyword_hits": keyword_hits,
        "exclamations": exclamations,
        "questions": questions,
        "text_tag": text_tag,
        "text_reason": text_reason,
        "signals": signals,
        "has_hook": has_hook,
        "has_punchline": has_punchline,
        "intensifier_hits": has_intensifiers,
        "dialogue_hits": dialogue_hits,
        "has_laughter": laughter,
        "keybert_score": round(keybert_score, 3),
        "keybert_keywords": [kw for kw, _ in keybert_keywords[:3]] if keybert_keywords else [],
        # Nouvelles données
        "is_commercial": is_commercial,
        "commercial_penalty": round(commercial_penalty, 3),
        "story_score": story_info["story_score"],
        "has_story_start": story_info["has_story_start"],
        "has_story_end": story_info["has_story_end"],
        "is_mid_thought": story_info["is_mid_thought"],
        "story_phase": story_info["story_phase"],
    }




