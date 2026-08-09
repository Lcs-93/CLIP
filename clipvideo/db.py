from __future__ import annotations

import sqlite3
from typing import Iterable

from .config import DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    source_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    duration_seconds REAL,
    status TEXT NOT NULL,
    transcript_path TEXT
);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    video_id TEXT,
    type TEXT NOT NULL,
    status TEXT NOT NULL,
    progress REAL,
    message TEXT,
    payload TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS clips (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL,
    start_seconds REAL NOT NULL,
    end_seconds REAL NOT NULL,
    score REAL,
    tag TEXT,
    reason TEXT,
    signals TEXT,
    tiktok_title TEXT,
    user_title TEXT,
    preview_path TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS exports (
    id TEXT PRIMARY KEY,
    clip_id TEXT NOT NULL,
    mode TEXT NOT NULL,
    output_path TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tiktok_accounts (
    id TEXT PRIMARY KEY,
    open_id TEXT NOT NULL UNIQUE,
    display_name TEXT,
    avatar_url TEXT,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    token_expires_at TEXT NOT NULL,
    refresh_expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    try:
        conn.executescript(SCHEMA)
        _ensure_columns(conn)
        conn.commit()
    finally:
        conn.close()


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict]:
    return [dict(row) for row in rows]


def _ensure_columns(conn: sqlite3.Connection) -> None:
    existing = {
        row["name"] for row in conn.execute("PRAGMA table_info(clips)").fetchall()
    }
    columns = {
        "tag": "TEXT",
        "reason": "TEXT",
        "signals": "TEXT",
        "tiktok_title": "TEXT",
        "user_title": "TEXT",
    }
    for name, definition in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE clips ADD COLUMN {name} {definition}")

    # Migration : créer tiktok_accounts si absente (bases existantes)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tiktok_accounts (
            id TEXT PRIMARY KEY,
            open_id TEXT NOT NULL UNIQUE,
            display_name TEXT,
            avatar_url TEXT,
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            token_expires_at TEXT NOT NULL,
            refresh_expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
