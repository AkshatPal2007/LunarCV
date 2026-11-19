"""Persistent single-host job state and a bounded, isolated compute worker."""

import json
import multiprocessing
import sqlite3
import threading
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from app.config import settings

_pool = None
_pool_lock = threading.Lock()


def now():
    return datetime.now(UTC).isoformat()


class JobRepository:
    def __init__(self, path=None):
        self.path = Path(path or settings.JOB_DB_PATH)

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        connection.execute(
            "CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, status TEXT NOT NULL, payload TEXT NOT NULL)"
        )
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def create(self, job, max_pending=4):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            count = db.execute(
                "SELECT count(*) FROM jobs WHERE status IN ('pending','processing')"
            ).fetchone()[0]
            if count >= max_pending:
                raise RuntimeError("Compute queue is full; retry later")
            db.execute(
                "INSERT INTO jobs VALUES (?,?,?)",
                (job["job_id"], job["status"], json.dumps(job)),
            )

    def get(self, job_id):
        with self.connect() as db:
            row = db.execute(
                "SELECT payload FROM jobs WHERE id=?", (job_id,)
            ).fetchone()
        if row is None:
            raise KeyError(job_id)
        return json.loads(row[0])

    def update(self, job_id, **changes):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT payload FROM jobs WHERE id=?", (job_id,)
            ).fetchone()
            if row is None:
                raise KeyError(job_id)
            payload = json.loads(row[0])
            payload.update(changes)
            db.execute(
                "UPDATE jobs SET status=?,payload=? WHERE id=?",
                (payload["status"], json.dumps(payload), job_id),
            )
        return payload

    def list_recent(self, limit=30):
        with self.connect() as db:
            rows = db.execute(
                "SELECT payload FROM jobs ORDER BY rowid DESC LIMIT ?",
                (max(1, min(limit, 100)),),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def recover(self):
        with self.connect() as db:
            rows = db.execute(
                "SELECT id,payload FROM jobs WHERE status IN ('pending','processing')"
            ).fetchall()
            for job_id, encoded in rows:
                payload = json.loads(encoded)
                payload.update(
                    status="failed",
                    completed_at=now(),
                    error="Worker restarted; rerun to reuse verified caches",
                    message="Interrupted by worker restart",
                )
                db.execute(
                    "UPDATE jobs SET status='failed',payload=? WHERE id=?",
                    (json.dumps(payload), job_id),
                )


def submit_job(job_id, source, reference, request):
    global _pool
    # One GPU owner. Launch server with one API worker for this single-host profile.
    with _pool_lock:
        if _pool is None:
            _pool = ProcessPoolExecutor(
                max_workers=1, mp_context=multiprocessing.get_context("spawn")
            )
    from app.services.registration_service import run_registration

    future = _pool.submit(
        run_registration,
        job_id,
        str(source),
        str(reference),
        request,
        str(settings.JOB_DB_PATH),
    )

    def finished(result):
        if result.cancelled():
            JobRepository().update(
                job_id,
                status="cancelled",
                completed_at=now(),
                message="Cancelled during worker shutdown",
            )
            return
        if result.exception() is not None:
            JobRepository().update(
                job_id,
                status="failed",
                completed_at=now(),
                error=str(result.exception()),
                message="Compute worker failed",
            )

    future.add_done_callback(finished)
    return future


def shutdown_worker():
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.shutdown(wait=False, cancel_futures=True)
            _pool = None
