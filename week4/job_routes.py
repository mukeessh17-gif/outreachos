"""Organization-scoped queue status endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from week4.auth import CurrentOrg
from week4.db import tenant_transaction

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
def list_jobs(
    org_id: CurrentOrg,
    job_status: str | None = Query(
        default=None,
        alias="status",
        pattern="^(pending|running|done|dead)$",
    ),
) -> list[dict[str, Any]]:
    from week4.main import engine

    sql = (
        "SELECT id, lead_id, step, status, attempts, max_attempts, "
        "available_at, last_error, created_at FROM jobs WHERE org_id = :org_id"
    )
    params: dict[str, Any] = {"org_id": org_id}
    if job_status:
        sql += " AND status = :status"
        params["status"] = job_status
    sql += " ORDER BY created_at DESC LIMIT 200"
    with tenant_transaction(org_id, engine=engine) as connection:
        rows = connection.execute(text(sql), params).mappings().all()
    return [dict(row) for row in rows]


@router.get("/{job_id}")
def get_job(job_id: int, org_id: CurrentOrg) -> dict[str, Any]:
    from week4.main import engine

    with tenant_transaction(org_id, engine=engine) as connection:
        row = connection.execute(
            text(
                "SELECT id, lead_id, step, status, attempts, max_attempts, "
                "available_at, last_error, created_at FROM jobs "
                "WHERE id = :job_id AND org_id = :org_id"
            ),
            {"job_id": job_id, "org_id": org_id},
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return dict(row)
