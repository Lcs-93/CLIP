from __future__ import annotations

import json
import os
import secrets
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(encoding="utf-8")
except Exception:
    pass

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import re

from clipvideo.config import EXPORTS_DIR, STORAGE_DIR, VIDEOS_DIR, ensure_dirs
from clipvideo.db import get_conn, init_db, rows_to_dicts
from clipvideo.utils import new_id, now_iso
import clipvideo.tiktok as tiktok_api

# Stockage temporaire en mémoire pour les états OAuth (state -> code_verifier)
_oauth_pending: dict[str, str] = {}

TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")
TIKTOK_REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI", "http://localhost:8000/api/tiktok/callback")

app = FastAPI(title="Clip Video Local API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    ensure_dirs()
    init_db()
    conn = get_conn()
    try:
        if _prune_orphan_videos(conn):
            conn.commit()
    finally:
        conn.close()


app.mount("/files", StaticFiles(directory=STORAGE_DIR), name="files")

EXPORT_PRESETS = {
    "9x16-crop",
    "9x16-fit",
    "1x1-crop",
    "1x1-fit",
    "16x9-fit",
    "4x5-crop",
}


def _storage_url(path_value: str | None) -> str | None:
    if not path_value:
        return None
    path = Path(path_value)
    try:
        relative = path.relative_to(STORAGE_DIR)
    except ValueError:
        return None
    return f"/files/{relative.as_posix()}"


def _safe_unlink(path_value: str | None) -> None:
    if not path_value:
        return
    try:
        Path(path_value).unlink(missing_ok=True)
    except Exception:
        return


def _safe_unlink_transcript_variants(path_value: str | None) -> None:
    """Delete transcript file and common sibling format (.json/.txt)."""
    if not path_value:
        return
    path = Path(path_value)
    candidates = {path}
    suffix = path.suffix.lower()
    if suffix == ".json":
        candidates.add(path.with_suffix(".txt"))
    elif suffix == ".txt":
        candidates.add(path.with_suffix(".json"))
    else:
        candidates.add(path.with_suffix(".json"))
        candidates.add(path.with_suffix(".txt"))
    for candidate in candidates:
        _safe_unlink(str(candidate))


def _path_missing(path_value: str | None) -> bool:
    if not path_value:
        return False
    try:
        return not Path(path_value).exists()
    except Exception:
        return True


def _fetch_one(conn, query: str, params: tuple = ()) -> dict | None:
    row = conn.execute(query, params).fetchone()
    return dict(row) if row else None


def _safe_filename(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"[^\w\s-]+", "", value, flags=re.UNICODE).strip()
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = cleaned.replace(" ", "_")
    cleaned = cleaned.strip("._")
    return cleaned or None


def _list_exports(conn, clip_id: str) -> list[dict]:
    exports = conn.execute(
        "SELECT * FROM exports WHERE clip_id = ? ORDER BY created_at",
        (clip_id,),
    ).fetchall()
    export_dicts = []
    for export in exports:
        export_dict = dict(export)
        if export_dict.get("status") == "done":
            export_dict["output_url"] = _storage_url(export_dict.get("output_path"))
        else:
            export_dict["output_url"] = None
        export_dicts.append(export_dict)
    return export_dicts


def _list_clips(conn, video_id: str) -> list[dict]:
    clips = conn.execute(
        "SELECT * FROM clips WHERE video_id = ? ORDER BY score DESC, start_seconds",
        (video_id,),
    ).fetchall()
    clip_dicts = []
    for clip in clips:
        clip_dict = dict(clip)
        clip_dict["preview_url"] = _storage_url(clip_dict.get("preview_path"))
        clip_dict["exports"] = _list_exports(conn, clip_dict["id"])
        clip_dicts.append(clip_dict)
    return clip_dicts


def _list_jobs(conn, video_id: str) -> list[dict]:
    jobs = conn.execute(
        "SELECT * FROM jobs WHERE video_id = ? ORDER BY created_at DESC",
        (video_id,),
    ).fetchall()
    return rows_to_dicts(jobs)


def _delete_clip(conn, clip_id: str) -> None:
    clip = _fetch_one(conn, "SELECT * FROM clips WHERE id = ?", (clip_id,))
    if not clip:
        return
    exports = conn.execute(
        "SELECT * FROM exports WHERE clip_id = ?",
        (clip_id,),
    ).fetchall()
    for export in exports:
        _safe_unlink(export["output_path"])
    _safe_unlink(clip.get("preview_path"))
    conn.execute("DELETE FROM exports WHERE clip_id = ?", (clip_id,))
    conn.execute("DELETE FROM clips WHERE id = ?", (clip_id,))


def _delete_export(conn, export_id: str) -> bool:
    export = _fetch_one(conn, "SELECT * FROM exports WHERE id = ?", (export_id,))
    if not export:
        return False
    _safe_unlink(export.get("output_path"))
    conn.execute("DELETE FROM exports WHERE id = ?", (export_id,))
    return True


def _delete_video(conn, video_id: str) -> None:
    video = _fetch_one(conn, "SELECT * FROM videos WHERE id = ?", (video_id,))
    if not video:
        return
    clips = conn.execute(
        "SELECT id FROM clips WHERE video_id = ?",
        (video_id,),
    ).fetchall()
    for clip in clips:
        _delete_clip(conn, clip["id"])
    _safe_unlink_transcript_variants(video.get("transcript_path"))
    _safe_unlink(video.get("source_path"))
    conn.execute("DELETE FROM jobs WHERE video_id = ?", (video_id,))
    conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))


def _prune_orphan_videos(conn) -> int:
    """
    Supprime les videos orphelines (fichier source manquant) et leurs donnees associees.
    """
    rows = conn.execute("SELECT id, source_path FROM videos").fetchall()
    removed = 0
    for row in rows:
        if _path_missing(row["source_path"]):
            _delete_video(conn, row["id"])
            removed += 1
    return removed


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/api/videos")
async def upload_video(file: UploadFile = File(...)) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    safe_name = Path(file.filename).name
    video_id = new_id("video")
    output_path = VIDEOS_DIR / f"{video_id}_{safe_name}"
    with output_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO videos (id, filename, source_path, created_at, status) VALUES (?, ?, ?, ?, ?)",
            (video_id, safe_name, str(output_path), now_iso(), "uploaded"),
        )
        conn.commit()
    finally:
        conn.close()

    return {"id": video_id, "filename": safe_name, "status": "uploaded"}


@app.get("/api/videos")
async def list_videos() -> list[dict]:
    conn = get_conn()
    try:
        if _prune_orphan_videos(conn):
            conn.commit()
        rows = conn.execute("SELECT * FROM videos ORDER BY created_at DESC").fetchall()
        return rows_to_dicts(rows)
    finally:
        conn.close()


@app.get("/api/videos/{video_id}")
async def get_video(video_id: str) -> dict:
    conn = get_conn()
    try:
        if _prune_orphan_videos(conn):
            conn.commit()
        video = _fetch_one(conn, "SELECT * FROM videos WHERE id = ?", (video_id,))
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        video["clips"] = _list_clips(conn, video_id)
        video["jobs"] = _list_jobs(conn, video_id)
        return video
    finally:
        conn.close()


@app.get("/api/clips/{clip_id}")
async def get_clip(clip_id: str) -> dict:
    conn = get_conn()
    try:
        clip = _fetch_one(conn, "SELECT * FROM clips WHERE id = ?", (clip_id,))
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        video = _fetch_one(conn, "SELECT * FROM videos WHERE id = ?", (clip["video_id"],))
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")

        clip["preview_url"] = _storage_url(clip.get("preview_path"))
        clip["exports"] = _list_exports(conn, clip["id"])

        video_info = {
            "id": video.get("id"),
            "filename": video.get("filename"),
            "duration_seconds": video.get("duration_seconds"),
            "status": video.get("status"),
        }
        return {"clip": clip, "video": video_info}
    finally:
        conn.close()


@app.patch("/api/clips/{clip_id}")
async def update_clip(clip_id: str, payload: dict) -> dict:
    user_title = payload.get("user_title")
    if user_title is not None:
        user_title = str(user_title).strip()
        if user_title == "":
            user_title = None

    conn = get_conn()
    try:
        clip = _fetch_one(conn, "SELECT * FROM clips WHERE id = ?", (clip_id,))
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        conn.execute(
            "UPDATE clips SET user_title = ? WHERE id = ?",
            (user_title, clip_id),
        )
        conn.commit()
        clip = _fetch_one(conn, "SELECT * FROM clips WHERE id = ?", (clip_id,))
        if clip:
            clip["preview_url"] = _storage_url(clip.get("preview_path"))
            clip["exports"] = _list_exports(conn, clip_id)
        return {"clip": clip}
    finally:
        conn.close()


@app.post("/api/videos/{video_id}/analyze")
async def analyze_video(video_id: str) -> dict:
    conn = get_conn()
    try:
        video = _fetch_one(conn, "SELECT * FROM videos WHERE id = ?", (video_id,))
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        job_id = new_id("job")
        conn.execute(
            "INSERT INTO jobs (id, video_id, type, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (job_id, video_id, "analyze", "queued", now_iso()),
        )
        conn.execute(
            "UPDATE videos SET status = ? WHERE id = ?",
            ("analyzing", video_id),
        )
        conn.commit()
        return {"job_id": job_id, "status": "queued"}
    finally:
        conn.close()


@app.post("/api/videos/{video_id}/generate")
async def generate_clips(video_id: str) -> dict:
    conn = get_conn()
    try:
        video = _fetch_one(conn, "SELECT * FROM videos WHERE id = ?", (video_id,))
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        job_id = new_id("job")
        conn.execute(
            "INSERT INTO jobs (id, video_id, type, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (job_id, video_id, "generate", "queued", now_iso()),
        )
        conn.execute(
            "UPDATE videos SET status = ? WHERE id = ?",
            ("generating", video_id),
        )
        conn.commit()
        return {"job_id": job_id, "status": "queued"}
    finally:
        conn.close()


@app.post("/api/clips/{clip_id}/export")
async def export_clip(clip_id: str, payload: dict) -> dict:
    mode = payload.get("mode")
    preset = payload.get("preset")
    if preset:
        if preset not in EXPORT_PRESETS:
            raise HTTPException(status_code=400, detail="Invalid preset")
    else:
        if mode not in {"talking", "gaming"}:
            raise HTTPException(status_code=400, detail="Invalid mode")

    conn = get_conn()
    try:
        clip = _fetch_one(conn, "SELECT * FROM clips WHERE id = ?", (clip_id,))
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")

        export_id = new_id("export")
        export_mode = preset or mode
        output_path = str((EXPORTS_DIR / f"{clip_id}_{export_mode}.mp4").resolve())
        conn.execute(
            "INSERT INTO exports (id, clip_id, mode, output_path, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (export_id, clip_id, export_mode, output_path, "queued", now_iso()),
        )
        job_id = new_id("job")
        job_payload = json.dumps(
            {"clip_id": clip_id, "export_id": export_id, "mode": mode, "preset": preset}
        )
        conn.execute(
            "INSERT INTO jobs (id, video_id, type, status, payload, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (job_id, clip.get("video_id"), "export", "queued", job_payload, now_iso()),
        )
        conn.commit()
        return {"job_id": job_id, "export_id": export_id, "status": "queued"}
    finally:
        conn.close()


@app.delete("/api/clips/{clip_id}")
async def delete_clip(clip_id: str) -> dict:
    conn = get_conn()
    try:
        clip = _fetch_one(conn, "SELECT * FROM clips WHERE id = ?", (clip_id,))
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        _delete_clip(conn, clip_id)
        conn.commit()
        return {"status": "deleted"}
    finally:
        conn.close()


@app.delete("/api/videos/{video_id}/clips")
async def clear_video_clips(video_id: str) -> dict:
    conn = get_conn()
    try:
        video = _fetch_one(conn, "SELECT * FROM videos WHERE id = ?", (video_id,))
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        clips = conn.execute("SELECT id FROM clips WHERE video_id = ?", (video_id,)).fetchall()
        for clip in clips:
            _delete_clip(conn, clip["id"])
        next_status = "analyzed" if video.get("duration_seconds") else "uploaded"
        conn.execute("UPDATE videos SET status = ? WHERE id = ?", (next_status, video_id))
        conn.commit()
        return {"status": "cleared"}
    finally:
        conn.close()


@app.delete("/api/videos/{video_id}/jobs")
async def clear_video_jobs(video_id: str) -> dict:
    conn = get_conn()
    try:
        video = _fetch_one(conn, "SELECT * FROM videos WHERE id = ?", (video_id,))
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        conn.execute("DELETE FROM jobs WHERE video_id = ?", (video_id,))
        conn.commit()
        return {"status": "cleared"}
    finally:
        conn.close()


@app.post("/api/jobs/retry-stuck")
async def retry_stuck_jobs() -> dict:
    """
    Remet en queue les jobs bloqués (status = 'running') ou en erreur (status = 'error'/'failed').
    Ne supprime PAS les transcripts ni les clips déjà encodés.
    """
    conn = get_conn()
    try:
        # Trouve les jobs bloqués ou en erreur
        stuck_jobs = conn.execute(
            "SELECT * FROM jobs WHERE status IN ('running', 'error', 'failed')"
        ).fetchall()
        
        reset_count = 0
        for job in stuck_jobs:
            job_id = job["id"]
            video_id = job["video_id"]
            job_type = job["type"]
            previous_status = job["status"]
            
            # Remet le job en "queued"
            conn.execute(
                "UPDATE jobs SET status = 'queued', started_at = NULL, finished_at = NULL, progress = NULL, message = ? WHERE id = ?",
                (
                    "Relancé après blocage" if previous_status == "running" else "Relancé après erreur",
                    job_id,
                ),
            )
            
            # Remet la vidéo dans un état cohérent selon le type de job
            if job_type == "analyze":
                conn.execute(
                    "UPDATE videos SET status = 'analyzing' WHERE id = ?",
                    (video_id,),
                )
            elif job_type == "generate":
                conn.execute(
                    "UPDATE videos SET status = 'generating' WHERE id = ?",
                    (video_id,),
                )
            elif job_type == "export":
                payload = json.loads(job.get("payload") or "{}")
                export_id = payload.get("export_id")
                if export_id:
                    conn.execute(
                        "UPDATE exports SET status = 'queued' WHERE id = ?",
                        (export_id,),
                    )
            
            reset_count += 1
        
        conn.commit()
        return {"status": "ok", "jobs_reset": reset_count}
    finally:
        conn.close()


@app.get("/api/jobs/stuck")
async def get_stuck_jobs() -> list[dict]:
    """Liste les jobs actuellement bloqués (status = 'running')."""
    conn = get_conn()
    try:
        jobs = conn.execute(
            "SELECT j.*, v.filename FROM jobs j LEFT JOIN videos v ON j.video_id = v.id WHERE j.status = 'running' ORDER BY j.started_at"
        ).fetchall()
        return rows_to_dicts(jobs)
    finally:
        conn.close()


@app.get("/api/exports/{export_id}/download")
async def download_export(export_id: str):
    conn = get_conn()
    try:
        export = _fetch_one(conn, "SELECT * FROM exports WHERE id = ?", (export_id,))
        if not export:
            raise HTTPException(status_code=404, detail="Export not found")
        if export.get("status") != "done":
            raise HTTPException(status_code=400, detail="Export not ready")
        output_path = export.get("output_path")
        if not output_path:
            raise HTTPException(status_code=404, detail="Export file missing")
        path = Path(output_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Export file missing")
        clip = _fetch_one(conn, "SELECT * FROM clips WHERE id = ?", (export.get("clip_id"),))
        base_name = None
        if clip:
            base_name = _safe_filename(clip.get("user_title")) or _safe_filename(
                clip.get("tiktok_title")
            )
        preset = export.get("mode") or "export"
        if base_name:
            filename = f"{base_name}_{preset}.mp4"
        else:
            filename = path.name
        return FileResponse(path, media_type="video/mp4", filename=filename)
    finally:
        conn.close()


@app.delete("/api/exports/{export_id}")
async def delete_export(export_id: str) -> dict:
    conn = get_conn()
    try:
        deleted = _delete_export(conn, export_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Export not found")
        conn.commit()
        return {"status": "deleted"}
    finally:
        conn.close()


@app.delete("/api/videos/{video_id}")
async def delete_video(video_id: str) -> dict:
    conn = get_conn()
    try:
        video = _fetch_one(conn, "SELECT * FROM videos WHERE id = ?", (video_id,))
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        _delete_video(conn, video_id)
        conn.commit()
        return {"status": "deleted"}
    finally:
        conn.close()


def _clean_storage_folder(folder: Path) -> int:
    """Supprime tous les fichiers dans un dossier de stockage, retourne le nombre supprimé."""
    count = 0
    if folder.exists():
        for f in folder.iterdir():
            if f.is_file():
                try:
                    f.unlink()
                    count += 1
                except Exception:
                    pass
    return count


@app.post("/api/reset")
async def reset_all() -> dict:
    conn = get_conn()
    try:
        rows = conn.execute("SELECT id FROM videos").fetchall()
        for row in rows:
            _delete_video(conn, row["id"])
        conn.execute("DELETE FROM exports")
        conn.execute("DELETE FROM clips")
        conn.execute("DELETE FROM jobs")
        conn.execute("DELETE FROM videos")
        conn.commit()
        
        # Nettoyage des fichiers orphelins dans tous les dossiers de stockage
        storage = Path(STORAGE_DIR)
        _clean_storage_folder(storage / "transcripts")
        _clean_storage_folder(storage / "videos")
        _clean_storage_folder(storage / "previews")
        _clean_storage_folder(storage / "exports")
        _clean_storage_folder(storage / "tmp")
        
        return {"status": "reset"}
    finally:
        conn.close()


# ===========================================================================
# TikTok — OAuth et upload INBOX
# ===========================================================================

@app.get("/api/tiktok/login")
async def tiktok_login():
    """Démarre le flow OAuth TikTok. Redirige l'utilisateur vers TikTok."""
    if not TIKTOK_CLIENT_KEY:
        raise HTTPException(status_code=500, detail="TIKTOK_CLIENT_KEY non configuré dans .env")
    state = secrets.token_urlsafe(16)
    code_verifier, code_challenge = tiktok_api.generate_pkce()
    _oauth_pending[state] = code_verifier
    auth_url = tiktok_api.build_auth_url(TIKTOK_CLIENT_KEY, TIKTOK_REDIRECT_URI, state, code_challenge)
    return RedirectResponse(auth_url)


@app.get("/api/tiktok/callback")
async def tiktok_callback(code: str = "", state: str = "", error: str = ""):
    """Callback OAuth TikTok — échange le code contre des tokens et stocke le compte."""
    if error:
        return RedirectResponse(f"http://localhost:3000/settings?tiktok_error={error}")
    if not state or state not in _oauth_pending:
        raise HTTPException(status_code=400, detail="State OAuth invalide ou expiré")
    code_verifier = _oauth_pending.pop(state)

    try:
        token_data = tiktok_api.exchange_code(
            TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, code, TIKTOK_REDIRECT_URI, code_verifier
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur échange token TikTok : {e}")

    access_token = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 86400)
    refresh_expires_in = token_data.get("refresh_expires_in", 31536000)
    open_id = token_data.get("open_id", "")

    now = datetime.now(timezone.utc)
    token_expires_at = (now + timedelta(seconds=expires_in)).isoformat()
    refresh_expires_at = (now + timedelta(seconds=refresh_expires_in)).isoformat()

    # Récupérer le nom d'affichage
    display_name = ""
    avatar_url = ""
    try:
        user_info = tiktok_api.get_user_info(access_token)
        display_name = user_info.get("display_name", "")
        avatar_url = user_info.get("avatar_url", "")
    except Exception:
        pass

    account_id = new_id("tiktok")
    conn = get_conn()
    try:
        existing = conn.execute(
            "SELECT id FROM tiktok_accounts WHERE open_id = ?", (open_id,)
        ).fetchone()
        if existing:
            conn.execute(
                """UPDATE tiktok_accounts
                   SET access_token=?, refresh_token=?, token_expires_at=?,
                       refresh_expires_at=?, display_name=?, avatar_url=?
                   WHERE open_id=?""",
                (access_token, refresh_token, token_expires_at,
                 refresh_expires_at, display_name, avatar_url, open_id),
            )
        else:
            conn.execute(
                """INSERT INTO tiktok_accounts
                   (id, open_id, display_name, avatar_url, access_token, refresh_token,
                    token_expires_at, refresh_expires_at, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (account_id, open_id, display_name, avatar_url, access_token,
                 refresh_token, token_expires_at, refresh_expires_at, now_iso()),
            )
        conn.commit()
    finally:
        conn.close()

    return RedirectResponse("http://localhost:3000/settings?tiktok_connected=1")


@app.get("/api/tiktok/accounts")
async def list_tiktok_accounts() -> list[dict]:
    """Liste les comptes TikTok connectés."""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT id, open_id, display_name, avatar_url, token_expires_at, refresh_expires_at, created_at FROM tiktok_accounts ORDER BY created_at"
        ).fetchall()
        return rows_to_dicts(rows)
    finally:
        conn.close()


@app.delete("/api/tiktok/accounts/{account_id}")
async def delete_tiktok_account(account_id: str) -> dict:
    """Supprime un compte TikTok connecté."""
    conn = get_conn()
    try:
        row = conn.execute("SELECT id FROM tiktok_accounts WHERE id = ?", (account_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Compte TikTok introuvable")
        conn.execute("DELETE FROM tiktok_accounts WHERE id = ?", (account_id,))
        conn.commit()
        return {"status": "deleted"}
    finally:
        conn.close()


@app.post("/api/tiktok/upload")
async def tiktok_upload(payload: dict) -> dict:
    """
    Envoie un export en brouillon (INBOX) sur TikTok.
    Body: { "export_id": "...", "account_id": "..." }
    """
    export_id = payload.get("export_id", "")
    account_id = payload.get("account_id", "")
    if not export_id or not account_id:
        raise HTTPException(status_code=400, detail="export_id et account_id requis")

    conn = get_conn()
    try:
        export = conn.execute("SELECT * FROM exports WHERE id = ?", (export_id,)).fetchone()
        if not export:
            raise HTTPException(status_code=404, detail="Export introuvable")
        if dict(export).get("status") != "done":
            raise HTTPException(status_code=400, detail="Export pas encore prêt")

        account = conn.execute(
            "SELECT * FROM tiktok_accounts WHERE id = ?", (account_id,)
        ).fetchone()
        if not account:
            raise HTTPException(status_code=404, detail="Compte TikTok introuvable")
        account = dict(account)
    finally:
        conn.close()

    # Rafraîchir le token si expiré
    access_token = account["access_token"]
    try:
        expires_at = datetime.fromisoformat(account["token_expires_at"])
        if datetime.now(timezone.utc) >= expires_at - timedelta(minutes=5):
            refreshed = tiktok_api.refresh_access_token(
                TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, account["refresh_token"]
            )
            access_token = refreshed["access_token"]
            new_expires = (datetime.now(timezone.utc) + timedelta(seconds=refreshed.get("expires_in", 86400))).isoformat()
            conn2 = get_conn()
            try:
                conn2.execute(
                    "UPDATE tiktok_accounts SET access_token=?, token_expires_at=? WHERE id=?",
                    (access_token, new_expires, account_id),
                )
                conn2.commit()
            finally:
                conn2.close()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur refresh token TikTok : {e}")

    video_path = dict(export).get("output_path", "")
    try:
        result = tiktok_api.upload_video_to_inbox(access_token, video_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Fichier vidéo introuvable sur le disque")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur upload TikTok : {e}")

    return {"status": "uploaded", "publish_id": result["publish_id"]}


@app.get("/api/tiktok/status/{publish_id}")
async def tiktok_publish_status(publish_id: str, account_id: str) -> dict:
    """Vérifie le statut d'un post TikTok (polling après upload)."""
    conn = get_conn()
    try:
        account = conn.execute(
            "SELECT access_token FROM tiktok_accounts WHERE id = ?", (account_id,)
        ).fetchone()
        if not account:
            raise HTTPException(status_code=404, detail="Compte TikTok introuvable")
        access_token = dict(account)["access_token"]
    finally:
        conn.close()

    try:
        data = tiktok_api.get_publish_status(access_token, publish_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur statut TikTok : {e}")
    return data
