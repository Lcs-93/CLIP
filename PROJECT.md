# CLIP VIDEO

Mise a jour: 2026-02-07
Statut: developpement actif

CLIP VIDEO est un outil local pour transformer une video longue en clips courts.
Le pipeline est: upload -> analyse -> generation -> export.

## Stack

- Frontend: Next.js 14 + TypeScript + Tailwind
- Backend: FastAPI
- Worker: Python (jobs asynchrones)
- DB: SQLite (`data/app.db`)
- Video: FFmpeg (NVENC avec fallback CPU)
- Transcription: faster-whisper

## Documentation

- `CONTEXT.md`: resume rapide pour reprendre le projet
- `docs/SETUP.md`: installation et lancement
- `docs/ARCHITECTURE.md`: architecture et flux
- `docs/API.md`: endpoints backend
- `docs/DATABASE.md`: schema SQLite
- `docs/WORKER.md`: logique worker et detection
- `docs/CONVENTIONS.md`: conventions de code
- `docs/ROADMAP.md`: priorites produit
- `docs/WORKER_IMPROVEMENTS.md`: backlog technique worker

## Lancement rapide

```powershell
# Terminal 1
uvicorn backend.main:app --reload --port 8000

# Terminal 2
python -m worker.worker

# Terminal 3
cd frontend
npm run dev
```

URLs:
- Frontend: http://localhost:3000
- API: http://localhost:8000
- Docs API: http://localhost:8000/docs
