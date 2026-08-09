from __future__ import annotations

import logging


def _load_env_file() -> None:
    # Load .env with a fallback for Windows ANSI-encoded files.
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    try:
        load_dotenv(encoding="utf-8")
    except UnicodeDecodeError:
        load_dotenv(encoding="cp1252")


_load_env_file()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

LOGGER = logging.getLogger("clipvideo.worker")
