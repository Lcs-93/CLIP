# Worker - CLIP VIDEO

Le worker lit la table `jobs` et execute le traitement lourd.

## Boucle principale

- prend le prochain job `queued`
- passe en `running`
- execute selon `type`
- termine en `done` ou `error`

Fichier d entree: `worker/worker.py`

## Types de jobs

- `analyze`
  - lit la video
  - calcule duree
  - lance transcription Whisper
  - met a jour `videos.status = analyzed`

- `generate`
  - charge transcript
  - analyse audio (RMS + options VAD/pitch/onset)
  - selectionne les segments
  - encode previews en parallele
  - cree les lignes `clips`
  - met a jour `videos.status = ready`

- `export`
  - lit preset
  - encode en format cible
  - met `exports.status = done`

## Modules principaux

- `worker/worker_jobs.py`: orchestration des handlers
- `worker/worker_transcript.py`: faster-whisper + cache modele
- `worker/worker_selection.py`: logique de scoring/selection
- `worker/worker_audio.py`: RMS, VAD, pitch, onset
- `worker/worker_audio_events.py`: IA audio (YAMNet/AudioSet) pour start/stop moteur
- `worker/worker_video_motion.py`: mouvement visuel (optical flow) pour start/stop voiture
- `worker/worker_text.py`: heuristiques texte
- `worker/worker_titles.py`: generation/clean de titres
- `worker/worker_scene.py`: scene detection (optionnel)
- `worker/worker_diarization.py`: diarization (optionnel)
- `worker/worker_ollama.py`: enrichissement LLM (optionnel)

## Parametres cle (`worker/worker_config.py`)

- `MIN_CLIP_LENGTH = 20.0`
- `MAX_CLIP_LENGTH = 55.0`
- `MIN_SCORE = 0.50`
- `ALLOW_LOW_SCORE_CLIPS` (si `true`, conserve aussi les clips avec score `< MIN_SCORE`)
- `ENABLE_CLIP_VARIATION`
- `CLIP_VARIATION_JITTER`
- `CLIP_VARIATION_TOP_K`
- `CLIP_VARIATION_SCORE_JITTER`
- `ENABLE_BOUNDARY_SNAP`
- `BOUNDARY_LOW_SCORE_THRESHOLD`
- `BOUNDARY_SNAP_MAX_SHIFT_SECONDS`
- `MIN_DISTANCE_SECONDS = 25.0`
- `MERGE_GAP_SECONDS = 7.0`
- `PRE_ROLL_SECONDS = 4.0`
- `POST_ROLL_SECONDS = 6.0`

Flags detection:
- `DETECTION_CLASSIC`
- `ENABLE_KEYBERT`
- `ENABLE_VAD`
- `ENABLE_ONSET`
- `ENABLE_LOCAL_PEAKS`
- `ENABLE_ADAPTIVE_SCORE`
- `ENABLE_NMS`
- `ENABLE_CAR_DETECTION`
- `ENABLE_CAR_START_STOP_DETECTION`
- `ENABLE_VISUAL_CAR_DETECTION`
- `ENABLE_AUDIO_EVENT_DETECTION`
- `CAR_ACCEL_THRESHOLD`
- `CAR_MIN_SUSTAIN_SECONDS`
- `CAR_GUARD_MIN_AUDIO`
- `CAR_LOW_DIALOGUE_WPS`
- `CAR_START_EVENT_THRESHOLD`
- `CAR_STOP_EVENT_THRESHOLD`
- `CAR_EVENT_MIN_DELTA`
- `CAR_EVENT_SMOOTH_SECONDS`
- `CAR_EVENT_COOLDOWN_SECONDS`
- `CAR_EVENT_MIN_SCORE`
- `VISUAL_MOTION_SAMPLE_FPS`
- `VISUAL_MOTION_RESIZE_WIDTH`
- `VISUAL_MOTION_ROI_BOTTOM_RATIO`
- `VISUAL_START_EVENT_THRESHOLD`
- `VISUAL_STOP_EVENT_THRESHOLD`
- `VISUAL_EVENT_MIN_DELTA`
- `VISUAL_EVENT_SMOOTH_SECONDS`
- `VISUAL_EVENT_COOLDOWN_SECONDS`
- `VISUAL_EVENT_MIN_SCORE`
- `AUDIO_EVENT_PROVIDER`
- `AUDIO_EVENT_START_THRESHOLD`
- `AUDIO_EVENT_STOP_THRESHOLD`
- `AUDIO_EVENT_MIN_DELTA`
- `AUDIO_EVENT_SMOOTH_SECONDS`
- `AUDIO_EVENT_COOLDOWN_SECONDS`
- `AUDIO_EVENT_MIN_SCORE`
- `CLIP_PROFILE` (`auto`/`car`/`talking`/`general`)
- `CLIP_MIN_SECONDS`
- `CLIP_MAX_SECONDS`
- `PROFILE_CAR_MIN_SECONDS`
- `PROFILE_CAR_MAX_SECONDS`
- `PROFILE_TALKING_MIN_SECONDS`
- `PROFILE_TALKING_MAX_SECONDS`
- `PROFILE_GENERAL_MIN_SECONDS`
- `PROFILE_GENERAL_MAX_SECONDS`
- `PROFILE_AUTO_CAR_PEAKS_PER_MIN`
- `PROFILE_AUTO_TALKING_WPS`

Durée:
- Le profil actif choisit automatiquement une plage min/max selon le contenu.
- La config recommandée vise des clips courts/moyens; tu peux monter les durées si besoin.

Note Ollama:
- Ollama est appelé seulement si `has_transcript=true` (transcript non vide) et si le modèle est disponible.
- Si transcript vide, l analyse LLM est ignorée car il n y a pas de texte à évaluer.
- Le worker peut charger des transcripts `.json` et fallback `.txt` (format `[start-end] texte`).

## Presets export

- `9x16-crop`
- `9x16-fit`
- `1x1-crop`
- `1x1-fit`
- `16x9-fit`
- `4x5-crop`

Legacy:
- `talking` -> `9x16-crop`
- `gaming` -> `9x16-fit`

## Erreurs et reprise

- En cas d erreur job: statut `error`
- Pour relancer:

```powershell
curl -X POST http://localhost:8000/api/jobs/retry-stuck
```

Ce endpoint remet en `queued` les jobs `running`/`error`/`failed`.
