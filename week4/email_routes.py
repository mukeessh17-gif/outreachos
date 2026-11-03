"""Organization-scoped email generation and approval queue endpoints."""

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import bindparam, text, update

from week4 import models
from week4.auth import CurrentOrg
from week4.db import tenant_transaction
from week4.email_writer import validate_email_sequence
from week4.job_queue import enqueue_job
from week4.schemas import (
    BulkApproveRequest,
    EmailDraftInput,
    EmailDraftPatch,
    EmailSequenceInput,
    EmailSequenceStatusUpdate,
    ResearchBrief,
)

router = APIRouter(prefix="/email-sequences", tags=["email approval"])


def _json_value(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _load_company_context(
    connection: Any,
    org_id: int,
    lead_id: int,
) -> tuple[dict[str, Any], ResearchBrief, dict[str, Any]]:
    lead = connection.execute(
        text("SELECT id, name FROM companies WHERE id = :lead_id AND org_id = :org_id"),
        {"lead_id": lead_id, "org_id": org_id},
    ).mappings().first()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    row = connection.execute(
        text(
            "SELECT pain_points, trigger, best_angle, confidence, sources "
            "FROM lead_research WHERE org_id = :org_id AND company_id = :lead_id "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"org_id": org_id, "lead_id": lead_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=409, detail="Research this lead before writing email.")
    brief = ResearchBrief(
        pain_points=_json_value(row["pain_points"]),
        trigger=row["trigger"],
        best_angle=row["best_angle"],
        confidence=row["confidence"],
        sources=_json_value(row["sources"]),
    )
    settings = connection.execute(
        text(
            "SELECT tone, sample_emails, banned_phrases FROM org_settings "
            "WHERE org_id = :org_id"
        ),
        {"org_id": org_id},
    ).mappings().first()
    if settings is None:
        raise HTTPException(status_code=404, detail="Organization settings not found.")
    return dict(lead), brief, {
        **dict(settings),
        "sample_emails": _json_value(settings["sample_emails"]),
        "banned_phrases": _json_value(settings["banned_phrases"]),
    }


@router.post("")
def create_sequence(
    org_id: CurrentOrg,
    lead_id: int = Query(ge=1),
    prompt_version: str = Query(default="v2", pattern="^(v1|v2)$"),
) -> dict[str, Any]:
    from week4.main import engine

    with tenant_transaction(org_id, engine=engine) as connection:
        exists = connection.execute(
            text("SELECT 1 FROM companies WHERE id = :lead_id AND org_id = :org_id"),
            {"lead_id": lead_id, "org_id": org_id},
        ).first()
        if exists is None:
            raise HTTPException(status_code=404, detail="Lead not found.")
    job_id = enqueue_job(
        org_id,
        lead_id,
        "write",
        {"prompt_version": prompt_version},
        engine=engine,
    )
    return {"job_id": job_id, "lead_id": lead_id, "status": "pending"}


@router.get("")
def list_sequences(
    org_id: CurrentOrg,
    sequence_status: str | None = Query(default=None, alias="status", pattern="^(draft|approved|rejected)$"),
) -> list[dict[str, Any]]:
    from week4.main import engine

    sql = (
        "SELECT s.id, s.lead_id, c.name AS company_name, s.status, s.prompt_version, "
        "s.created_at, COALESCE((SELECT SUM(t.input_tokens + t.output_tokens) "
        "FROM token_usage t WHERE t.org_id = s.org_id AND t.lead_id = s.lead_id), 0) "
        "AS tokens_used FROM email_sequences s JOIN companies c "
        "ON c.id = s.lead_id AND c.org_id = s.org_id WHERE s.org_id = :org_id"
    )
    params: dict[str, Any] = {"org_id": org_id}
    if sequence_status:
        sql += " AND s.status = :status"
        params["status"] = sequence_status
    sql += " ORDER BY s.created_at DESC"
    with tenant_transaction(org_id, engine=engine) as connection:
        rows = connection.execute(text(sql), params).mappings().all()
    return [{**dict(row), "cost_usd": 0.0} for row in rows]


@router.get("/{sequence_id}")
def get_sequence(sequence_id: int, org_id: CurrentOrg) -> dict[str, Any]:
    from week4.main import engine

    with tenant_transaction(org_id, engine=engine) as connection:
        sequence = connection.execute(
            text(
                "SELECT id, lead_id, status, prompt_version, created_at "
                "FROM email_sequences WHERE id = :sequence_id AND org_id = :org_id"
            ),
            {"sequence_id": sequence_id, "org_id": org_id},
        ).mappings().first()
        if sequence is None:
            raise HTTPException(status_code=404, detail="Email sequence not found.")
        drafts = connection.execute(
            text(
                "SELECT id, position, subject, body, send_delay_days, status "
                "FROM email_drafts WHERE sequence_id = :sequence_id AND org_id = :org_id "
                "ORDER BY position"
            ),
            {"sequence_id": sequence_id, "org_id": org_id},
        ).mappings().all()
    return {**dict(sequence), "emails": [dict(row) for row in drafts], "cost_usd": 0.0}


def _load_drafts(connection: Any, sequence_id: int, org_id: int) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in connection.execute(
            text(
                "SELECT id, position, subject, body, send_delay_days "
                "FROM email_drafts WHERE sequence_id = :sequence_id AND org_id = :org_id "
                "ORDER BY position"
            ),
            {"sequence_id": sequence_id, "org_id": org_id},
        ).mappings().all()
    ]


@router.patch("/{sequence_id}/drafts/{draft_id}")
def edit_draft(
    sequence_id: int,
    draft_id: int,
    payload: EmailDraftPatch,
    org_id: CurrentOrg,
) -> dict[str, Any]:
    from week4.main import engine

    with tenant_transaction(org_id, engine=engine) as connection:
        sequence = connection.execute(
            text(
                "SELECT lead_id, status FROM email_sequences "
                "WHERE id = :sequence_id AND org_id = :org_id"
            ),
            {"sequence_id": sequence_id, "org_id": org_id},
        ).mappings().first()
        if sequence is None:
            raise HTTPException(status_code=404, detail="Email sequence not found.")
        if sequence["status"] != "draft":
            raise HTTPException(status_code=409, detail="Only draft sequences can be edited.")
        draft = connection.execute(
            text(
                "SELECT id, position FROM email_drafts WHERE id = :draft_id "
                "AND sequence_id = :sequence_id AND org_id = :org_id"
            ),
            {"draft_id": draft_id, "sequence_id": sequence_id, "org_id": org_id},
        ).mappings().first()
        if draft is None:
            raise HTTPException(status_code=404, detail="Email draft not found.")
        lead, brief, settings = _load_company_context(
            connection,
            org_id,
            sequence["lead_id"],
        )
        current_drafts = _load_drafts(connection, sequence_id, org_id)
        current = next(item for item in current_drafts if item["id"] == draft_id)
        current.update(payload.model_dump())
        sequence_content = EmailSequenceInput(
            emails=[
                EmailDraftInput(
                    subject=item["subject"],
                    body=item["body"],
                    send_delay_days=item["send_delay_days"],
                )
                for item in current_drafts
            ]
        )
        validate_email_sequence(
            sequence_content,
            brief,
            lead["name"],
            settings["banned_phrases"],
        )
        connection.execute(
            text(
                "UPDATE email_drafts SET subject = :subject, body = :body, "
                "send_delay_days = :send_delay_days WHERE id = :draft_id "
                "AND sequence_id = :sequence_id AND org_id = :org_id"
            ),
            {
                **payload.model_dump(),
                "draft_id": draft_id,
                "sequence_id": sequence_id,
                "org_id": org_id,
            },
        )
    return {"id": draft_id, **payload.model_dump()}


def _validate_sequence_for_approval(
    connection: Any,
    sequence_id: int,
    org_id: int,
) -> None:
    sequence = connection.execute(
        text(
            "SELECT lead_id FROM email_sequences "
            "WHERE id = :sequence_id AND org_id = :org_id"
        ),
        {"sequence_id": sequence_id, "org_id": org_id},
    ).mappings().first()
    if sequence is None:
        raise HTTPException(status_code=404, detail="Email sequence not found.")
    lead, brief, settings = _load_company_context(connection, org_id, sequence["lead_id"])
    drafts = _load_drafts(connection, sequence_id, org_id)
    validated = EmailSequenceInput(
        emails=[
            EmailDraftInput(
                subject=item["subject"],
                body=item["body"],
                send_delay_days=item["send_delay_days"],
            )
            for item in drafts
        ]
    )
    validate_email_sequence(validated, brief, lead["name"], settings["banned_phrases"])


@router.patch("/{sequence_id}/status")
def update_sequence_status(
    sequence_id: int,
    payload: EmailSequenceStatusUpdate,
    org_id: CurrentOrg,
) -> dict[str, Any]:
    from week4.main import engine

    with tenant_transaction(org_id, engine=engine) as connection:
        if payload.status == "approved":
            _validate_sequence_for_approval(connection, sequence_id, org_id)
        result = connection.execute(
            text(
                "UPDATE email_sequences SET status = :status "
                "WHERE id = :sequence_id AND org_id = :org_id AND status = 'draft'"
            ),
            {"status": payload.status, "sequence_id": sequence_id, "org_id": org_id},
        )
        if result.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Draft email sequence not found.",
            )
        connection.execute(
            text(
                "UPDATE email_drafts SET status = :status "
                "WHERE sequence_id = :sequence_id AND org_id = :org_id"
            ),
            {"status": payload.status, "sequence_id": sequence_id, "org_id": org_id},
        )
    return {"id": sequence_id, "status": payload.status}


@router.post("/bulk-approve")
def bulk_approve(payload: BulkApproveRequest, org_id: CurrentOrg) -> dict[str, int]:
    from week4.main import engine

    sequence_ids = list(dict.fromkeys(payload.sequence_ids))
    with tenant_transaction(org_id, engine=engine) as connection:
        statement = text(
            "SELECT id FROM email_sequences WHERE org_id = :org_id "
            "AND status = 'draft' AND id IN :sequence_ids"
        ).bindparams(bindparam("sequence_ids", expanding=True))
        existing_ids = [
            row["id"]
            for row in connection.execute(
                statement,
                {"org_id": org_id, "sequence_ids": sequence_ids},
            ).mappings()
        ]
        if len(existing_ids) != len(sequence_ids):
            raise HTTPException(status_code=404, detail="One or more draft sequences were not found.")
        for sequence_id in existing_ids:
            _validate_sequence_for_approval(connection, sequence_id, org_id)
        connection.execute(
            update(models.email_sequences)
            .where(
                models.email_sequences.c.org_id == org_id,
                models.email_sequences.c.id.in_(existing_ids),
                models.email_sequences.c.status == "draft",
            )
            .values(status="approved")
        )
        connection.execute(
            update(models.email_drafts)
            .where(
                models.email_drafts.c.org_id == org_id,
                models.email_drafts.c.sequence_id.in_(existing_ids),
            )
            .values(status="approved")
        )
    return {"approved": len(existing_ids)}
