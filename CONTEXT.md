# CONTEXT - CLIP VIDEO

Ce fichier sert de memo rapide pour relancer une session de travail.

## But produit

Generer des clips courts (20-55s) depuis une video longue, en local.

## Architecture

- Frontend (port 3000): interface Next.js
- Backend (port 8000): API FastAPI
- Worker: boucle de jobs SQLite
- Stockage: `data/storage/*`
- Base: `data/app.db`

## Flux principal

1. Upload video (`POST /api/videos`)
2. Analyse (`POST /api/videos/{video_id}/analyze`)
3. Generation clips (`POST /api/videos/{video_id}/generate`)
4. Export clip (`POST /api/clips/{clip_id}/export`)

## Endpoints utilises souvent

- `GET /api/videos`
- `GET /api/videos/{video_id}`
- `GET /api/clips/{clip_id}`
- `PATCH /api/clips/{clip_id}` (titre utilisateur)
- `POST /api/jobs/retry-stuck`
- `POST /api/reset`
- `GET /api/exports/{export_id}/download`

## Etats importants

Video:
- `uploaded`
- `analyzing`
- `analyzed`
- `generating`
- `ready`
- `error`

Job:
- `queued`
- `running`
- `done`
- `error`

Export:
- `queued`
- `done`
- `error`

## Presets export

- `9x16-crop`
- `9x16-fit`
- `1x1-crop`
- `1x1-fit`
- `16x9-fit`
- `4x5-crop`

Compat legacy:
- `talking` -> `9x16-crop`
- `gaming` -> `9x16-fit`

## Fichiers a modifier selon besoin

- API: `backend/main.py`
- Jobs worker: `worker/worker_jobs.py`
- Selection clips: `worker/worker_selection.py`
- Transcription: `worker/worker_transcript.py`
- Config worker: `worker/worker_config.py`
- Schema DB: `clipvideo/db.py`
- Wrappers FFmpeg: `clipvideo/ffmpeg.py`
- UI shell: `frontend/components/app/app-shell.tsx`
- Pages frontend: `frontend/app/**/page.tsx`

## Commandes utiles

```powershell
# Backend
uvicorn backend.main:app --reload --port 8000

# Worker
python -m worker.worker

# Frontend
cd frontend
npm run dev

# Relancer jobs bloques
curl -X POST http://localhost:8000/api/jobs/retry-stuck

# Reset complet
curl -X POST http://localhost:8000/api/reset
```

## Risques frequents

- Worker non lance -> jobs restent `queued`
- FFmpeg absent -> echec encode
- CUDA indisponible -> transcription/encode plus lents
- Job plante -> etat `running` ou `error`, utiliser `retry-stuck`
