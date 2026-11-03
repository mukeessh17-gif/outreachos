"""Claim and process scheduled outbox records for one organization."""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.engine import Engine

from week4 import models
from week4.db import tenant_transaction
from week4.email_delivery import send_approved_draft

logger = logging.getLogger("outreachos.scheduler")


def process_due_sends(
    org_id: int,
    *,
    engine: Engine,
    now: datetime | None = None,
    limit: int = 20,
) -> dict[str, int]:
    current_time = now or datetime.now(timezone.utc)
    with tenant_transaction(org_id, engine=engine) as connection:
        rows = connection.execute(
            select(
                models.outbox.c.id,
                models.outbox.c.draft_id,
                models.outbox.c.inbox_id,
                models.outbox.c.recipient,
            )
            .where(
                models.outbox.c.org_id == org_id,
                models.outbox.c.status == "scheduled",
                models.outbox.c.scheduled_at <= current_time,
            )
            .order_by(models.outbox.c.scheduled_at, models.outbox.c.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).mappings().all()
        for row in rows:
            connection.execute(
                update(models.outbox)
                .where(
                    models.outbox.c.id == row["id"],
                    models.outbox.c.org_id == org_id,
                    models.outbox.c.status == "scheduled",
                )
                .values(status="processing", locked_at=current_time)
            )

    counts = {"processed": 0, "sent": 0, "dry_run": 0, "failed": 0}
    for row in rows:
        try:
            result = send_approved_draft(
                org_id,
                row["draft_id"],
                row["inbox_id"],
                row["recipient"],
                engine=engine,
                _scheduled_claimed=True,
            )
        except Exception as error:
            with tenant_transaction(org_id, engine=engine) as connection:
                connection.execute(
                    update(models.outbox)
                    .where(
                        models.outbox.c.id == row["id"],
                        models.outbox.c.org_id == org_id,
                        models.outbox.c.status.in_(("processing", "pending")),
                    )
                    .values(status="failed", locked_at=None)
                )
            logger.error(
                "scheduled delivery failed id=%s error_type=%s",
                row["id"],
                type(error).__name__,
            )
            counts["failed"] += 1
            continue
        counts["processed"] += 1
        status = result.get("status")
        if status in {"sent", "dry_run"}:
            counts[status] += 1
        else:
            counts["failed"] += 1
    return counts
