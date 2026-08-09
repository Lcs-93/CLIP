# Roadmap - CLIP VIDEO

Mise a jour: 2026-02-07

## En place

- Upload video
- Jobs async (`analyze`, `generate`, `export`)
- Transcription faster-whisper
- Selection clips + scoring
- Previews auto
- Exports multi-presets
- Retry jobs bloques
- Reset session

## Priorites court terme

1. Stabilite worker
- mieux tracer les erreurs
- renforcer les tests unitaires modules worker

2. Qualite detection
- affiner les poids de scoring
- reduire faux positifs commerciaux
- mieux gerer debuts/fins de phrase

3. UX workflow
- clarifier suivi d avancement par job
- edition plus simple des titres clips
- tri/filtre exports plus rapides

## Moyen terme

1. Performance
- cache plus agressif des analyses
- options de parallellisation reglables

2. Formats
- consolider presets sociaux (9:16, 1:1, 4:5, 16:9)
- automatiser recommandations de preset par type de clip

3. Qualite semantique
- titres plus consistants
- tags plus stables

## Long terme

- monitoring avance (metriques et timings par etape)
- strategie de tests de regression scoring
- packaging plus simple pour execution locale
