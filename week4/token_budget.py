"""Atomic per-organization and per-lead AI token reservation."""

from datetime import datetime, timezone
from typing import Callable, TypeVar

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.engine import Engine

from week1.llm import request_validated
from week4.db import tenant_transaction
from week2.db import get_engine
from week4.plan_limits import PLAN_LIMITS

SchemaT = TypeVar("SchemaT", bound=BaseModel)


def request_budgeted(
    prompt: str,
    response_model: type[SchemaT],
    *,
    org_id: int,
    lead_id: int,
    purpose: str,
    engine: Engine | None = None,
    generator: Callable[..., tuple[SchemaT, int, int]] = request_validated,
) -> tuple[SchemaT, int, int]:
    """Reserve enough tokens for both validated-output attempts before calling AI."""
    database = engine or get_engine()
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    estimated_input = max(1, (len(prompt) + 2) // 3)
    with tenant_transaction(org_id, engine=database) as connection:
        lock_clause = " FOR UPDATE" if connection.dialect.name == "postgresql" else ""
        settings = connection.execute(
            text(
                "SELECT s.daily_token_budget, s.per_lead_token_budget, o.plan "
                "FROM org_settings s JOIN orgs o ON o.id = s.org_id "
                "WHERE s.org_id = :org_id" + lock_clause
            ),
            {"org_id": org_id},
        ).mappings().first()
        if settings is None:
            raise HTTPException(status_code=404, detail="Organization settings not found.")
        daily_used = connection.execute(
            text(
                "SELECT COALESCE(SUM(input_tokens + output_tokens), 0) FROM token_usage "
                "WHERE org_id = :org_id AND created_at >= :today"
            ),
            {"org_id": org_id, "today": today},
        ).scalar_one()
        lead_used = connection.execute(
            text(
                "SELECT COALESCE(SUM(input_tokens + output_tokens), 0) FROM token_usage "
                "WHERE org_id = :org_id AND lead_id = :lead_id AND created_at >= :today"
            ),
            {"org_id": org_id, "lead_id": lead_id, "today": today},
        ).scalar_one()
        remaining = min(
            min(
                settings["daily_token_budget"],
                PLAN_LIMITS.get(settings["plan"], PLAN_LIMITS["free"])["daily_tokens"],
            ) - daily_used,
            settings["per_lead_token_budget"] - lead_used,
        )
        max_output_per_attempt = min(2048, remaining // 2 - estimated_input - 100)
        if max_output_per_attempt < 1:
            raise HTTPException(
                status_code=429,
                detail="The organization or lead has reached its daily AI token budget.",
            )
        reserved_tokens = 2 * (estimated_input + max_output_per_attempt + 100)
        reservation = connection.execute(
            text(
                "INSERT INTO token_usage (org_id, lead_id, input_tokens, output_tokens) "
                "VALUES (:org_id, :lead_id, :reserved_tokens, 0) RETURNING id"
            ),
            {
                "org_id": org_id,
                "lead_id": lead_id,
                "reserved_tokens": reserved_tokens,
            },
        ).scalar_one()

    validated, input_tokens, output_tokens = generator(
        prompt,
        response_model,
        org_id=org_id,
        purpose=purpose,
        max_output_tokens=max_output_per_attempt,
    )
    with tenant_transaction(org_id, engine=database) as connection:
        connection.execute(
            text(
                "UPDATE token_usage SET input_tokens = :input_tokens, "
                "output_tokens = :output_tokens WHERE id = :reservation_id "
                "AND org_id = :org_id AND lead_id = :lead_id"
            ),
            {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "reservation_id": reservation,
                "org_id": org_id,
                "lead_id": lead_id,
            },
        )
    return validated, input_tokens, output_tokens
