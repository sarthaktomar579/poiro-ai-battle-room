"""Async in-process job worker.

Design notes
------------
* The HTTP request that creates a submission **never** blocks on the
  provider. It writes ``Job(status=queued)`` and enqueues onto an
  ``asyncio.Queue``.
* A small pool of worker coroutines consumes the queue concurrently,
  bounded by ``WORKER_CONCURRENCY``.
* Each attempt is wrapped in ``asyncio.wait_for`` to enforce a per-job
  hard timeout (-> ``timed_out``).
* Retriable provider errors get one extra attempt (configurable). Each
  attempt creates a fresh ``Job`` row so the timeline is fully auditable.
* Every state change emits a ``room.events`` row **and** a websocket
  broadcast, so refreshing the page reconstructs the same state from DB.

This is intentionally **not** Celery/RQ. The assignment explicitly says
"a lightweight in-process worker" is acceptable and that's the simplest
honest choice for a single-process FastAPI app with SQLite.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from .. import events as ev
from .. import models
from ..config import get_settings
from ..database import SessionLocal
from ..providers import get_provider
from ..providers.base import GenerationResult, ProviderError, is_quota_or_rate_limit_error
from ..providers.mock import MockProvider
from ..ws.manager import manager

log = logging.getLogger("poiro.worker")


class JobQueue:
    def __init__(self) -> None:
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self._tasks: list[asyncio.Task] = []
        self._stopped = asyncio.Event()

    async def start(self) -> None:
        settings = get_settings()
        for i in range(max(1, settings.worker_concurrency)):
            self._tasks.append(asyncio.create_task(self._loop(i), name=f"job-worker-{i}"))
        log.info("Started %d job workers", len(self._tasks))

    async def stop(self) -> None:
        self._stopped.set()
        for t in self._tasks:
            t.cancel()
        for t in self._tasks:
            try:
                await t
            except asyncio.CancelledError:
                pass
        self._tasks.clear()

    async def enqueue(self, job_id: str) -> None:
        await self.queue.put(job_id)

    async def _loop(self, idx: int) -> None:
        while not self._stopped.is_set():
            try:
                job_id = await self.queue.get()
            except asyncio.CancelledError:
                return
            try:
                await _process_job(job_id)
            except Exception:
                log.exception("worker %d crashed processing %s", idx, job_id)
            finally:
                self.queue.task_done()


job_queue = JobQueue()


# ---------- Internals ----------


async def _process_job(job_id: str) -> None:
    """Run one attempt of a job, persisting state transitions as we go."""
    settings = get_settings()
    provider = get_provider()

    # 1) Mark running + load context
    ctx = _load_and_mark_running(job_id)
    if ctx is None:
        return  # Job vanished (shouldn't happen but be safe).
    room_id, submission_id, prompt, brief, attempt = ctx
    await manager.broadcast(
        room_id,
        ev.JOB_RUNNING,
        {"job_id": job_id, "submission_id": submission_id, "attempt": attempt},
    )

    # 2) Run the provider call under a hard timeout
    try:
        result = await asyncio.wait_for(
            provider.generate(prompt, context=brief),
            timeout=settings.job_timeout_seconds,
        )
    except asyncio.TimeoutError:
        _finalize(job_id, status=models.JobStatus.timed_out, error="Job exceeded timeout")
        await manager.broadcast(
            room_id,
            ev.JOB_TIMED_OUT,
            {"job_id": job_id, "submission_id": submission_id},
        )
        # Timeouts are not retried — a retry often stacks with quota limits.
        await _maybe_advance_round(room_id)
        return
    except ProviderError as e:
        if (
            settings.gemini_fallback_to_mock
            and is_quota_or_rate_limit_error(e)
        ):
            try:
                mock = MockProvider(
                    min_latency=0.4,
                    max_latency=0.8,
                    failure_rate=0.0,
                    timeout_rate=0.0,
                )
                result = await asyncio.wait_for(
                    mock.generate(prompt, context=brief),
                    timeout=settings.job_timeout_seconds,
                )
                result = GenerationResult(
                    output=(
                        f"[Gemini quota reached — mock fallback for demo]\n\n"
                        f"{result.output}"
                    ),
                    provider="mock:gemini-quota-fallback",
                )
            except Exception as fallback_err:  # noqa: BLE001
                log.warning("Mock fallback after quota error failed: %s", fallback_err)
            else:
                _finalize(
                    job_id,
                    status=models.JobStatus.completed,
                    output=result.output,
                    provider=result.provider,
                )
                await manager.broadcast(
                    room_id,
                    ev.JOB_COMPLETED,
                    {
                        "job_id": job_id,
                        "submission_id": submission_id,
                        "output": result.output,
                        "provider": result.provider,
                    },
                )
                await _maybe_advance_round(room_id)
                return

        _finalize(job_id, status=models.JobStatus.failed, error=str(e))
        await manager.broadcast(
            room_id,
            ev.JOB_FAILED,
            {"job_id": job_id, "submission_id": submission_id, "error": str(e)},
        )
        await _maybe_retry(job_id, room_id, submission_id, attempt, transient=e.retriable)
        await _maybe_advance_round(room_id)
        return
    except Exception as e:  # noqa: BLE001 - last-resort guard
        _finalize(job_id, status=models.JobStatus.failed, error=f"Unhandled: {e}")
        await manager.broadcast(
            room_id,
            ev.JOB_FAILED,
            {"job_id": job_id, "submission_id": submission_id, "error": str(e)},
        )
        await _maybe_advance_round(room_id)
        return

    # 3) Success
    _finalize(
        job_id,
        status=models.JobStatus.completed,
        output=result.output,
        provider=result.provider,
    )
    await manager.broadcast(
        room_id,
        ev.JOB_COMPLETED,
        {
            "job_id": job_id,
            "submission_id": submission_id,
            "output": result.output,
            "provider": result.provider,
        },
    )
    await _maybe_advance_round(room_id)


def _load_and_mark_running(
    job_id: str,
) -> Optional[tuple[str, str, str, str, int]]:
    """Atomically transition a job from queued -> running.

    Returns ``(room_id, submission_id, prompt, brief, attempt)`` or ``None``.
    """
    with SessionLocal() as db:  # type: Session
        job = db.get(models.Job, job_id)
        if not job:
            return None
        if job.status != models.JobStatus.queued:
            return None
        sub = db.get(models.Submission, job.submission_id)
        if not sub:
            return None
        rnd = db.get(models.Round, sub.round_id)
        room = db.get(models.Room, rnd.room_id) if rnd else None
        if not (rnd and room):
            return None

        job.status = models.JobStatus.running
        job.started_at = datetime.utcnow()
        db.add(
            models.Event(
                room_id=room.id,
                type=ev.JOB_RUNNING,
                payload={"job_id": job.id, "submission_id": sub.id, "attempt": job.attempt},
            )
        )
        db.commit()
        return room.id, sub.id, sub.prompt, room.prompt, job.attempt


def _finalize(
    job_id: str,
    *,
    status: models.JobStatus,
    output: Optional[str] = None,
    error: Optional[str] = None,
    provider: Optional[str] = None,
) -> None:
    with SessionLocal() as db:
        job = db.get(models.Job, job_id)
        if not job:
            return
        job.status = status
        job.output = output
        job.error = error
        if provider:
            job.provider = provider
        job.completed_at = datetime.utcnow()
        sub = db.get(models.Submission, job.submission_id)
        rnd = db.get(models.Round, sub.round_id) if sub else None
        if rnd:
            event_type = {
                models.JobStatus.completed: ev.JOB_COMPLETED,
                models.JobStatus.failed: ev.JOB_FAILED,
                models.JobStatus.timed_out: ev.JOB_TIMED_OUT,
            }.get(status, ev.JOB_FAILED)
            db.add(
                models.Event(
                    room_id=rnd.room_id,
                    type=event_type,
                    payload={
                        "job_id": job.id,
                        "submission_id": job.submission_id,
                        "status": status.value,
                        "attempt": job.attempt,
                        "error": error,
                    },
                )
            )
        db.commit()


async def _maybe_retry(
    job_id: str,
    room_id: str,
    submission_id: str,
    attempt: int,
    *,
    transient: bool,
) -> None:
    settings = get_settings()
    if not transient or attempt >= settings.job_max_attempts:
        return

    # Create a fresh queued job for the same submission. Linear ~1s backoff.
    await asyncio.sleep(1.0 * attempt)
    new_job_id: Optional[str] = None
    with SessionLocal() as db:
        new_job = models.Job(
            submission_id=submission_id,
            attempt=attempt + 1,
            status=models.JobStatus.queued,
        )
        db.add(new_job)
        db.flush()
        db.add(
            models.Event(
                room_id=room_id,
                type=ev.JOB_QUEUED,
                payload={"job_id": new_job.id, "submission_id": submission_id, "attempt": new_job.attempt, "retry": True},
            )
        )
        db.commit()
        new_job_id = new_job.id

    if new_job_id:
        await manager.broadcast(
            room_id,
            ev.JOB_QUEUED,
            {
                "job_id": new_job_id,
                "submission_id": submission_id,
                "attempt": attempt + 1,
                "retry": True,
            },
        )
        await job_queue.enqueue(new_job_id)


async def _maybe_advance_round(room_id: str) -> None:
    """If every submission has reached a terminal job state, flip the round to ``scoring``."""
    advanced_round_id: Optional[str] = None
    with SessionLocal() as db:
        room = db.get(models.Room, room_id)
        if not room or not room.current_round_id:
            return
        rnd = db.get(models.Round, room.current_round_id)
        if not rnd or rnd.status not in (models.RoundStatus.open, models.RoundStatus.generating):
            return

        subs = (
            db.query(models.Submission).filter(models.Submission.round_id == rnd.id).all()
        )
        if not subs:
            return

        for s in subs:
            latest = (
                db.query(models.Job)
                .filter(models.Job.submission_id == s.id)
                .order_by(models.Job.created_at.desc())
                .first()
            )
            if not latest or latest.status not in (
                models.JobStatus.completed,
                models.JobStatus.failed,
                models.JobStatus.timed_out,
            ):
                return  # at least one is still pending; do nothing

        rnd.status = models.RoundStatus.scoring
        room.status = models.RoomStatus.scoring
        db.add(
            models.Event(
                room_id=room.id,
                type=ev.ROUND_STATE_CHANGED,
                payload={"round_id": rnd.id, "status": rnd.status.value},
            )
        )
        db.commit()
        advanced_round_id = rnd.id

    if advanced_round_id is not None:
        await manager.broadcast(
            room_id,
            ev.ROUND_STATE_CHANGED,
            {"round_id": advanced_round_id, "status": models.RoundStatus.scoring.value},
        )
