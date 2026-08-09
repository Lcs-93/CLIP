# Setup - CLIP VIDEO

## Prerequis

- Windows 10/11
- Python 3.11+ (3.13 teste)
- Node.js 18+
- npm 9+
- FFmpeg (ffmpeg + ffprobe dans le PATH)

Verification rapide:

```powershell
python --version
node --version
npm --version
ffmpeg -version
ffprobe -version
```

## Installation

```powershell
git clone <repo_url> CLIP_VIDEO
cd CLIP_VIDEO
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Frontend:

```powershell
cd frontend
npm install
cd ..
```

## Variables d environnement

Fichier `.env` a la racine (optionnel selon besoins):

```env
# Ollama (optionnel)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=mistral:7b
OLLAMA_ENABLED=true

# Whisper (optionnel)
WHISPER_MODEL=large-v3
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
WHISPER_LANGUAGE=auto

# Detection
DETECTION_CLASSIC=false
ENABLE_CAR_DETECTION=true
CAR_ACCEL_THRESHOLD=0.62
CAR_MIN_SUSTAIN_SECONDS=1.0
CAR_GUARD_MIN_AUDIO=0.42
CAR_LOW_DIALOGUE_WPS=0.90
ENABLE_CAR_START_STOP_DETECTION=true
CAR_START_EVENT_THRESHOLD=0.58
CAR_STOP_EVENT_THRESHOLD=0.46
CAR_EVENT_MIN_DELTA=0.12
CAR_EVENT_SMOOTH_SECONDS=1.5
CAR_EVENT_COOLDOWN_SECONDS=2.5
CAR_EVENT_MIN_SCORE=0.50
ENABLE_VISUAL_CAR_DETECTION=true
VISUAL_MOTION_SAMPLE_FPS=6.0
VISUAL_MOTION_RESIZE_WIDTH=320
VISUAL_MOTION_ROI_BOTTOM_RATIO=0.60
VISUAL_START_EVENT_THRESHOLD=0.52
VISUAL_STOP_EVENT_THRESHOLD=0.42
VISUAL_EVENT_MIN_DELTA=0.08
VISUAL_EVENT_SMOOTH_SECONDS=1.2
VISUAL_EVENT_COOLDOWN_SECONDS=2.0
VISUAL_EVENT_MIN_SCORE=0.45
ENABLE_AUDIO_EVENT_DETECTION=true
AUDIO_EVENT_PROVIDER=yamnet
AUDIO_EVENT_START_THRESHOLD=0.35
AUDIO_EVENT_STOP_THRESHOLD=0.30
AUDIO_EVENT_MIN_DELTA=0.08
AUDIO_EVENT_SMOOTH_SECONDS=1.0
AUDIO_EVENT_COOLDOWN_SECONDS=2.0
AUDIO_EVENT_MIN_SCORE=0.30
ALLOW_LOW_SCORE_CLIPS=false
ENABLE_CLIP_VARIATION=true
CLIP_VARIATION_JITTER=0.04
CLIP_VARIATION_TOP_K=18
CLIP_VARIATION_SCORE_JITTER=0.025
ENABLE_BOUNDARY_SNAP=true
BOUNDARY_LOW_SCORE_THRESHOLD=0.55
BOUNDARY_SNAP_MAX_SHIFT_SECONDS=1.6

# Profil clips (durée dynamique)
CLIP_PROFILE=auto
CLIP_MIN_SECONDS=20
CLIP_MAX_SECONDS=55
PROFILE_CAR_MIN_SECONDS=24
PROFILE_CAR_MAX_SECONDS=62
PROFILE_TALKING_MIN_SECONDS=28
PROFILE_TALKING_MAX_SECONDS=70
PROFILE_GENERAL_MIN_SECONDS=55
PROFILE_GENERAL_MAX_SECONDS=60
PROFILE_AUTO_CAR_PEAKS_PER_MIN=8.0
PROFILE_AUTO_TALKING_WPS=1.35
```

Option pyannote:

```env
HF_TOKEN=hf_xxx
```

Option YAMNet (IA audio start/stop moteur):

```powershell
pip install tensorflow tensorflow-hub
```

## Lancement

```powershell
# Terminal 1: API
uvicorn backend.main:app --reload --port 8000

# Terminal 2: Worker
python -m worker.worker

# Terminal 3: Frontend
cd frontend
npm run dev
```

Lancement en une commande (depuis la racine du projet):

```powershell
.\start-dev.ps1
```

Ou en double-clic:

```powershell
.\start-dev.bat
```

## Verification

```powershell
curl http://localhost:8000/api/health
```

Reponse attendue:

```json
{ "status": "ok" }
```

## Depannage rapide

- Jobs bloquent:

```powershell
curl -X POST http://localhost:8000/api/jobs/retry-stuck
```

- Reset complet:

```powershell
curl -X POST http://localhost:8000/api/reset
```

- Port occupe (8000):

```powershell
netstat -ano | findstr :8000
taskkill /PID <pid> /F
```
