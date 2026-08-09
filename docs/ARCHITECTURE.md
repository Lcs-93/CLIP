# Architecture - CLIP VIDEO

## Vue globale

```text
Frontend (Next.js) -> Backend API (FastAPI) -> Queue SQLite (jobs)
                                             -> Worker Python
                                             -> data/storage/*
```

## Arborescence utile

```text
CLIP_VIDEO/
|- backend/main.py
|- clipvideo/
|  |- config.py
|  |- db.py
|  |- ffmpeg.py
|  `- utils.py
|- worker/
|  |- worker.py
|  |- worker_jobs.py
|  |- worker_selection.py
|  |- worker_transcript.py
|  |- worker_audio.py
|  |- ...
|- frontend/
|  |- app/
|  |- components/
|  `- lib/
|- data/
|  |- app.db
|  `- storage/
`- docs/
```

## Backend (`backend/main.py`)

Role:
- creer/supprimer videos, clips, exports
- creer les jobs (`analyze`, `generate`, `export`)
- servir les fichiers via `/files/...`
- exposer les endpoints admin (`retry-stuck`, `reset`)

## Worker (`worker/`)

Le worker est maintenant modulaire (pas un seul gros fichier).

Flux worker:
1. prend un job `queued`
2. passe le job en `running`
3. execute selon `type`
4. termine en `done` ou `error`

Modules centraux:
- `worker_jobs.py`: handlers `handle_analyze`, `handle_generate`, `handle_export`
- `worker_transcript.py`: transcription faster-whisper
- `worker_selection.py`: selection/scoring des segments
- `worker_audio.py`: RMS, VAD, pitch, onset
- `worker_scene.py`: scene detection (optionnel)
- `worker_diarization.py`: speaker diarization (optionnel)
- `worker_ollama.py`: enrichissement LLM (optionnel)

## DB et communication

L API et le worker communiquent via SQLite (`jobs`).
Pas de broker externe.

Etats jobs utilises:
- `queued`
- `running`
- `done`
- `error`

## Frontend (`frontend/`)

Routes principales:
- `/dashboard`
- `/videos/[videoId]/processing`
- `/videos/[videoId]/clips`
- `/clips/[clipId]`
- `/exports`
- `/settings`

Redirection racine:
- `/` -> `/dashboard`

API base frontend:
- `NEXT_PUBLIC_API_BASE` (default `http://localhost:8000`)

## Donnees runtime

- Base: `data/app.db`
- Fichiers:
  - `data/storage/videos`
  - `data/storage/transcripts`
  - `data/storage/previews`
  - `data/storage/exports`
  - `data/storage/tmp`
