from __future__ import annotations

import time

from clipvideo.config import ensure_dirs
from clipvideo.db import get_conn, init_db

from worker.worker_logging import LOGGER
from worker.worker_jobs import (
    _fetch_one,
    _mark_export_error,
    _mark_job_running,
    _mark_video_error,
    _update_job,
    handle_analyze,
    handle_export,
    handle_generate,
)


def run_loop() -> None:
    ensure_dirs()
    init_db()
    LOGGER.info("Worker started - waiting for jobs...")

    while True:
        conn = get_conn()
        try:
            job = _fetch_one(
                conn,
                "SELECT * FROM jobs WHERE status = 'queued' ORDER BY created_at LIMIT 1",
            )
            if not job:
                conn.close()
                time.sleep(1.0)
                continue

            LOGGER.info("Job picked: %s (%s)", job["id"], job["type"])
            _mark_job_running(conn, job["id"])
            conn.commit()

            try:
                if job["type"] == "analyze":
                    handle_analyze(conn, job)
                elif job["type"] == "generate":
                    handle_generate(conn, job)
                elif job["type"] == "export":
                    handle_export(conn, job)
                else:
                    raise RuntimeError(f"Unknown job type: {job['type']}")

                _update_job(conn, job["id"], "done")
                LOGGER.info("Job done: %s (%s)", job["id"], job["type"])
            except Exception as exc:
                if job["type"] == "export":
                    _mark_export_error(conn, job, str(exc))
                else:
                    _mark_video_error(conn, job)
                LOGGER.exception("Job failed: %s (%s)", job["id"], job["type"])
                _update_job(conn, job["id"], "error", str(exc))
            conn.commit()
        finally:
            conn.close()


if __name__ == "__main__":
    run_loop()
