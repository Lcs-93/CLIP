"""
TikTok Content Posting API — mode INBOX (brouillons).
Gère OAuth 2.0 PKCE, refresh token, et l'upload de vidéos.
"""
from __future__ import annotations

import base64
import hashlib
import math
import secrets
from pathlib import Path
from urllib.parse import urlencode

import requests

TIKTOK_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_USER_INFO_URL = "https://open.tiktokapis.com/v2/user/info/"
TIKTOK_INBOX_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
TIKTOK_STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"

CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB


# ---------------------------------------------------------------------------
# PKCE helpers
# ---------------------------------------------------------------------------

def generate_pkce() -> tuple[str, str]:
    """Retourne (code_verifier, code_challenge) pour OAuth PKCE."""
    code_verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return code_verifier, code_challenge


def build_auth_url(client_key: str, redirect_uri: str, state: str, code_challenge: str) -> str:
    params = {
        "client_key": client_key,
        "redirect_uri": redirect_uri,
        "scope": "user.info.basic,video.upload",
        "response_type": "code",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return TIKTOK_AUTH_URL + "?" + urlencode(params)


# ---------------------------------------------------------------------------
# Token exchange
# ---------------------------------------------------------------------------

def exchange_code(
    client_key: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
    code_verifier: str,
) -> dict:
    resp = requests.post(
        TIKTOK_TOKEN_URL,
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(client_key: str, client_secret: str, refresh_token: str) -> dict:
    resp = requests.post(
        TIKTOK_TOKEN_URL,
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# User info
# ---------------------------------------------------------------------------

def get_user_info(access_token: str) -> dict:
    resp = requests.get(
        TIKTOK_USER_INFO_URL,
        params={"fields": "open_id,display_name,avatar_url"},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("data", {}).get("user", {})


# ---------------------------------------------------------------------------
# Video upload (INBOX)
# ---------------------------------------------------------------------------

def upload_video_to_inbox(access_token: str, video_path: str) -> dict:
    """
    Upload une vidéo en mode INBOX (brouillon dans l'app TikTok).
    Retourne {"publish_id": "...", "status": "processing_upload"}.
    """
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Fichier vidéo introuvable : {video_path}")

    video_size = path.stat().st_size
    total_chunks = math.ceil(video_size / CHUNK_SIZE)

    # 1. Initialiser l'upload
    init_resp = requests.post(
        TIKTOK_INBOX_INIT_URL,
        json={
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": CHUNK_SIZE,
                "total_chunk_count": total_chunks,
            }
        },
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
        timeout=30,
    )
    init_resp.raise_for_status()
    init_data = init_resp.json()

    error = init_data.get("error", {})
    if error.get("code", "ok") != "ok":
        raise RuntimeError(f"TikTok init error: {error.get('message')}")

    upload_url = init_data["data"]["upload_url"]
    publish_id = init_data["data"]["publish_id"]

    # 2. Uploader les chunks
    with path.open("rb") as f:
        for chunk_idx in range(total_chunks):
            chunk_data = f.read(CHUNK_SIZE)
            start = chunk_idx * CHUNK_SIZE
            end = start + len(chunk_data) - 1
            put_resp = requests.put(
                upload_url,
                data=chunk_data,
                headers={
                    "Content-Range": f"bytes {start}-{end}/{video_size}",
                    "Content-Length": str(len(chunk_data)),
                    "Content-Type": "video/mp4",
                },
                timeout=120,
            )
            put_resp.raise_for_status()

    return {"publish_id": publish_id, "status": "processing_upload"}


def get_publish_status(access_token: str, publish_id: str) -> dict:
    resp = requests.post(
        TIKTOK_STATUS_URL,
        json={"publish_id": publish_id},
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
