# API Reference - CLIP VIDEO

Base URL: `http://localhost:8000`

## Health

- `GET /api/health`
  - Response: `{ "status": "ok" }`

## Videos

- `POST /api/videos`
  - Form-data: `file`
  - Cree une video en statut `uploaded`

- `GET /api/videos`
  - Liste les videos

- `GET /api/videos/{video_id}`
  - Detail video + clips + jobs

- `POST /api/videos/{video_id}/analyze`
  - Cree un job `analyze` (`queued`)
  - Passe la video en `analyzing`

- `POST /api/videos/{video_id}/generate`
  - Cree un job `generate` (`queued`)
  - Passe la video en `generating`

- `DELETE /api/videos/{video_id}`
  - Supprime video, clips, exports, jobs et fichiers associes

- `DELETE /api/videos/{video_id}/clips`
  - Supprime tous les clips d une video

- `DELETE /api/videos/{video_id}/jobs`
  - Supprime tous les jobs d une video

## Clips

- `GET /api/clips/{clip_id}`
  - Retourne:
    - `clip` (avec `preview_url`, `exports`)
    - `video` (infos minimales)

- `PATCH /api/clips/{clip_id}`
  - Payload JSON: `{ "user_title": "..." }` ou `null`
  - Met a jour le titre utilisateur

- `POST /api/clips/{clip_id}/export`
  - Payload JSON:
    - recommande: `{ "preset": "9x16-crop" }`
    - legacy accepte: `{ "mode": "talking" }` ou `{ "mode": "gaming" }`
  - Cree un export (`queued`) et un job `export` (`queued`)

- `DELETE /api/clips/{clip_id}`
  - Supprime le clip et ses exports

## Exports

- `GET /api/exports/{export_id}/download`
  - Telecharge un export `done`
  - Nom de fichier base sur `user_title` ou `tiktok_title` si disponible

- `DELETE /api/exports/{export_id}`
  - Supprime l export et le fichier disque

## Jobs

- `GET /api/jobs/stuck`
  - Liste les jobs `running`

- `POST /api/jobs/retry-stuck`
  - Replace les jobs `running`/`error`/`failed` en `queued`
  - Re-aligne les statuts video/export

## Admin

- `POST /api/reset`
  - Reset complet DB + stockage

## Presets export valides

- `9x16-crop`
- `9x16-fit`
- `1x1-crop`
- `1x1-fit`
- `16x9-fit`
- `4x5-crop`

Compat legacy:
- `talking` -> `9x16-crop`
- `gaming` -> `9x16-fit`

## Codes HTTP

- `200`: succes
- `400`: requete invalide
- `404`: ressource absente
- `500`: erreur serveur

Format erreur:

```json
{ "detail": "message" }
```
