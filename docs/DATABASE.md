# Database - CLIP VIDEO

Fichier DB: `data/app.db`

## Tables

### `videos`

Colonnes principales:
- `id` (PK)
- `filename`
- `source_path`
- `created_at`
- `duration_seconds`
- `status`
- `transcript_path`

Statuts video:
- `uploaded`
- `analyzing`
- `analyzed`
- `generating`
- `ready`
- `error`

### `jobs`

Colonnes principales:
- `id` (PK)
- `video_id`
- `type` (`analyze`, `generate`, `export`)
- `status`
- `progress`
- `message`
- `payload`
- `created_at`
- `started_at`
- `finished_at`

Statuts job:
- `queued`
- `running`
- `done`
- `error`

### `clips`

Colonnes principales:
- `id` (PK)
- `video_id`
- `start_seconds`
- `end_seconds`
- `score`
- `tag`
- `reason`
- `signals` (JSON texte)
- `tiktok_title`
- `user_title`
- `preview_path`
- `status`
- `created_at`

### `exports`

Colonnes principales:
- `id` (PK)
- `clip_id`
- `mode` (preset stocke)
- `output_path`
- `status`
- `created_at`

Statuts export:
- `queued`
- `done`
- `error`

## Relations

- 1 video -> N jobs
- 1 video -> N clips
- 1 clip -> N exports

## Notes implementation

- Schema defini dans `clipvideo/db.py`
- Colonnes additionnelles de `clips` gerees par `_ensure_columns()`
- `row_factory = sqlite3.Row` pour acces par nom

## Requetes utiles

```sql
SELECT * FROM jobs WHERE status = 'queued' ORDER BY created_at LIMIT 1;
```

```sql
SELECT * FROM clips WHERE video_id = ? ORDER BY score DESC, start_seconds;
```

```sql
SELECT * FROM exports WHERE clip_id = ? ORDER BY created_at;
```
