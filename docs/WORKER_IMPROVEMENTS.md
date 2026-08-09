# Worker Improvements Backlog

Mise a jour: 2026-02-07

Objectif: garder une liste courte, actionnable, alignee sur le code actuel.

## P0 - Fiabilite

1. Couvrir `worker_jobs.py` par tests
- cas succes/erreur sur `analyze`, `generate`, `export`
- validation des transitions de status DB

2. Renforcer gestion erreurs encode
- conserver message d erreur utile dans `jobs.message`
- verifier coherence `exports.status` en echec

3. Detecter jobs orphelins plus tot
- monitoring simple des jobs `running` trop longs
- alerte log explicite

## P1 - Qualite detection

1. Affiner scoring segment
- recalibrer seuils `MIN_SCORE`, bonus/punition
- separer davantage contenu utile vs promo

2. Mieux exploiter transcript mots
- coupes plus propres en fin de phrase
- moins de coupes sur mots de liaison

3. Evaluer options audio
- VAD/onset/pitch selon cout reel
- profils de config par type de contenu

## P2 - Performance

1. Mesure fine des timings
- temps transcription
- temps selection
- temps encodage previews

2. Parallelisme configurable
- ajuster workers preview selon machine
- fallback clair si GPU indisponible

3. Cache analyses optionnelles
- eviter recalculs inutiles sur regenerate

## P3 - UX technique

1. Qualite metadata clips
- coherence `tag`, `reason`, `tiktok_title`
- fallback propre si Ollama indisponible

2. Export experience
- presets favoris
- historique export par clip plus lisible

## Critere de priorisation

- Impact utilisateur
- Risque de regression
- Cout implementation
- Facilité de test

## Definition of done (par item)

- code merge
- test minimum ajoute
- doc mise a jour (`WORKER.md` ou `API.md` si impact API)
