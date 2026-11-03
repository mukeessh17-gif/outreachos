"""Postgres-backed, idempotent jobs with SKIP LOCKED claims and retries."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from sqlalchemy import and_, or_, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Engine

from week4 import models
from week4.db import tenant_transaction

logger = logging.getLogger("outreachos.jobs")
JobHandler = Callable[[dict[str, Any]], Any]
LEASE_TIME = timedelta(minutes=5)


def enqueue_job(
    org_id: int,
    lead_id: int,
    step: str,
    payload: dict[str, Any] | None = None,
    *,
    engine: Engine,
) -> int:
    if step not in {"research", "write"}:
        raise ValueError("Unsupported job step.")
    with tenant_transaction(org_id, engine=engine) as connection:
        insert = (
            postgresql_insert if connection.dialect.name == "postgresql" else sqlite_insert
        )
        inserted = connection.execute(
            insert(models.jobs)
            .values(
                org_id=org_id,
                lead_id=lead_id,
                step=step,
                payload=payload or {},
                status="pending",
            )
            .on_conflict_do_nothing(
                index_elements=[
                    models.jobs.c.org_id,
                    models.jobs.c.lead_id,
                    models.jobs.c.step,
                ]
            )
            .returning(models.jobs.c.id)
        ).scalar_one_or_none()
        if inserted is not None:
            return int(inserted)
        existing = connection.execute(
            select(models.jobs.c.id).where(
                models.jobs.c.org_id == org_id,
                models.jobs.c.lead_id == lead_id,
                models.jobs.c.step == step,
            )
        ).scalar_one()
    return int(existing)


def _claim_job(org_id: int, engine: Engine, now: datetime) -> dict[str, Any] | None:
    stale_before = now - LEASE_TIME
    with tenant_transaction(org_id, engine=engine) as connection:
        connection.execute(
            update(models.jobs)
            .where(
                models.jobs.c.org_id == org_id,
                models.jobs.c.status == "running",
                models.jobs.c.locked_at <= stale_before,
                models.jobs.c.attempts >= models.jobs.c.max_attempts,
            )
            .values(
                status="dead",
                locked_at=None,
                last_error="WorkerLeaseExpired",
            )
        )
        query = (
            select(models.jobs)
            .where(
                models.jobs.c.org_id == org_id,
                models.jobs.c.available_at <= now,
                models.jobs.c.attempts < models.jobs.c.max_attempts,
                or_(
                    models.jobs.c.status == "pending",
                    and_(
                        models.jobs.c.status == "running",
                        models.jobs.c.locked_at <= stale_before,
                    ),
                ),
            )
            .order_by(models.jobs.c.available_at, models.jobs.c.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        row = connection.execute(query).mappings().first()
        if row is None:
            return None
        claimed = connection.execute(
            update(models.jobs)
            .where(
                models.jobs.c.id == row["id"],
                models.jobs.c.org_id == org_id,
            )
            .values(
                status="running",
                attempts=models.jobs.c.attempts + 1,
                locked_at=now,
            )
            .returning(models.jobs)
        ).mappings().one()
        return dict(claimed)


def _finish_job(
    job: dict[str, Any],
    org_id: int,
    engine: Engine,
) -> None:
    with tenant_transaction(org_id, engine=engine) as connection:
        connection.execute(
            update(models.jobs)
            .where(
                models.jobs.c.id == job["id"],
                models.jobs.c.org_id == org_id,
                models.jobs.c.status == "running",
            )
            .values(status="done", locked_at=None, last_error=None)
        )


def _fail_job(
    job: dict[str, Any],
    org_id: int,
    engine: Engine,
    error: Exception,
    now: datetime,
) -> str:
    dead = job["attempts"] >= job["max_attempts"]
    delay_seconds = min(2 ** min(job["attempts"], 10), 3600)
    with tenant_transaction(org_id, engine=engine) as connection:
        connection.execute(
            update(models.jobs)
            .where(
                models.jobs.c.id == job["id"],
                models.jobs.c.org_id == org_id,
                models.jobs.c.status == "running",
            )
            .values(
                status="dead" if dead else "pending",
                available_at=now if dead else now + timedelta(seconds=delay_seconds),
                locked_at=None,
                last_error=type(error).__name__,
            )
        )
    logger.error(
        "job failed id=%s step=%s error_type=%s final=%s",
        job["id"],
        job["step"],
        type(error).__name__,
        dead,
    )
    return "dead" if dead else "retry"


def process_one(
    org_id: int,
    handlers: dict[str, JobHandler],
    *,
    engine: Engine,
    now: datetime | None = None,
) -> str:
    """Run one job for one org; caller can loop for a worker process."""
    current_time = now or datetime.now(timezone.utc)
    job = _claim_job(org_id, engine, current_time)
    if job is None:
        return "idle"
    handler = handlers.get(job["step"])
    if handler is None:
        _fail_job(
            job,
            org_id,
            engine,
            ValueError("No handler registered for this job step."),
            current_time,
        )
        raise ValueError(f"No worker handler is configured for step {job['step']!r}.")
    try:
        handler(job)
    except Exception as error:
        return _fail_job(job, org_id, engine, error, current_time)
    _finish_job(job, org_id, engine)
    return "done"
