from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
STORAGE_DIR = DATA_DIR / "storage"
VIDEOS_DIR = STORAGE_DIR / "videos"
PREVIEWS_DIR = STORAGE_DIR / "previews"
EXPORTS_DIR = STORAGE_DIR / "exports"
TRANSCRIPTS_DIR = STORAGE_DIR / "transcripts"
TEMP_DIR = STORAGE_DIR / "tmp"
DB_PATH = DATA_DIR / "app.db"


def ensure_dirs() -> None:
    for directory in [
        DATA_DIR,
        STORAGE_DIR,
        VIDEOS_DIR,
        PREVIEWS_DIR,
        EXPORTS_DIR,
        TRANSCRIPTS_DIR,
        TEMP_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)
