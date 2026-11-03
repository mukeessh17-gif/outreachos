"""Free and Stripe-test plan quotas enforced by API routes."""

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.engine import Connection

PLAN_LIMITS = {
    "free": {"leads": 100, "daily_tokens": 10_000},
    "starter": {"leads": 1_000, "daily_tokens": 100_000},
    "team": {"leads": 10_000, "daily_tokens": 1_000_000},
}


def enforce_lead_limit(connection: Connection, org_id: int) -> None:
    org_query = connection.execute(
        text(
            "SELECT plan FROM orgs WHERE id = :org_id"
            + (" FOR UPDATE" if connection.dialect.name == "postgresql" else "")
        ),
        {"org_id": org_id},
    ).scalar_one_or_none()
    if org_query is None:
        raise HTTPException(status_code=404, detail="Organization not found.")
    lead_count = connection.execute(
        text("SELECT COUNT(*) FROM companies WHERE org_id = :org_id"),
        {"org_id": org_id},
    ).scalar_one()
    limit = PLAN_LIMITS.get(org_query, PLAN_LIMITS["free"])["leads"]
    if lead_count >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"This plan allows up to {limit} leads. Remove leads or upgrade the test-mode plan.",
        )
