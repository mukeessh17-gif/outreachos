"""Replies, calendar, billing, and expanded analytics endpoints."""

import json
import os
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query, Request
from sqlalchemy import select, text, update

from week4 import models
from week4.auth import CurrentIdentity, CurrentOrg
from week4.billing import create_checkout_session, handle_stripe_event, verify_stripe_signature
from week4.db import tenant_transaction
from week4.email_delivery import google_freebusy
from week4.email_delivery import schedule_approved_sequence
from week4.replies import classify_and_save_reply, evaluate_fake_replies
from week4.reply_sync import sync_gmail_replies
from week4.schemas import (
    CalendarBookingRequest,
    FreeBusyRequest,
    PromptExperimentRequest,
    ReplyRequest,
    ScheduleSequenceRequest,
)

router = APIRouter(tags=["replies, calendar, and billing"])


@router.post("/email-sequences/{sequence_id}/schedule")
def schedule_sequence(
    sequence_id: int,
    payload: ScheduleSequenceRequest,
    org_id: CurrentOrg,
) -> dict[str, Any]:
    from week4.main import engine

    scheduled = schedule_approved_sequence(
        org_id,
        sequence_id,
        payload.inbox_id,
        payload.recipient,
        engine=engine,
    )
    return {"scheduled": scheduled}


@router.post("/integrations/google/replies/sync")
def sync_replies(
    org_id: CurrentOrg,
    inbox_id: int = Query(ge=1),
) -> dict[str, int]:
    from week4.main import engine

    return sync_gmail_replies(org_id, inbox_id, engine=engine)


@router.post("/replies/classify", status_code=201)
def classify_reply(payload: ReplyRequest, org_id: CurrentOrg) -> dict[str, Any]:
    from week4.main import engine

    try:
        return classify_and_save_reply(
            org_id,
            payload.lead_id,
            payload.sender_email,
            payload.body,
            engine=engine,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/replies")
def list_replies(
    org_id: CurrentOrg,
    status_filter: str | None = Query(
        default=None,
        alias="status",
        pattern="^(draft|handled|approved|rejected)$",
    ),
) -> list[dict[str, Any]]:
    from week4.main import engine

    statement = text(
        "SELECT id, lead_id, sender_email, body, category, draft_response, status, created_at "
        "FROM replies WHERE org_id = :org_id"
        + (" AND status = :status" if status_filter else "")
        + " ORDER BY created_at DESC LIMIT 200"
    )
    params: dict[str, Any] = {"org_id": org_id}
    if status_filter:
        params["status"] = status_filter
    with tenant_transaction(org_id, engine=engine) as connection:
        rows = connection.execute(statement, params).mappings().all()
    return [dict(row) for row in rows]


@router.post("/replies/{reply_id}/approve")
def approve_reply(reply_id: int, org_id: CurrentOrg) -> dict[str, str]:
    return _set_reply_status(reply_id, org_id, "approved")


@router.post("/replies/{reply_id}/reject")
def reject_reply(reply_id: int, org_id: CurrentOrg) -> dict[str, str]:
    return _set_reply_status(reply_id, org_id, "rejected")


def _set_reply_status(reply_id: int, org_id: int, status: str) -> dict[str, str]:
    from week4.main import engine

    with tenant_transaction(org_id, engine=engine) as connection:
        result = connection.execute(
            update(models.replies)
            .where(
                models.replies.c.id == reply_id,
                models.replies.c.org_id == org_id,
                models.replies.c.status == "draft",
            )
            .values(status=status)
        )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Reply draft not found.")
    return {"status": status}


@router.post("/calendar/freebusy")
def calendar_freebusy(
    payload: FreeBusyRequest,
    org_id: CurrentOrg,
    inbox_id: int = Query(ge=1),
) -> dict[str, Any]:
    from week4.main import engine

    with tenant_transaction(org_id, engine=engine) as connection:
        connected = connection.execute(
            select(models.inboxes.c.id).where(
                models.inboxes.c.id == inbox_id,
                models.inboxes.c.org_id == org_id,
                models.inboxes.c.encrypted_token != "",
            )
        ).first()
    if connected is None:
        raise HTTPException(status_code=409, detail="Connect a Google inbox with Calendar access first.")
    busy = google_freebusy(
        org_id,
        inbox_id,
        payload.starts_at,
        payload.ends_at,
        engine=engine,
    )
    return {"busy": busy, "available": not busy}


@router.get("/calendar/booking-link")
def get_booking_link(org_id: CurrentOrg) -> dict[str, str]:
    from week4.main import engine

    with tenant_transaction(org_id, engine=engine) as connection:
        link = connection.execute(
            select(models.org_settings.c.calendar_link).where(
                models.org_settings.c.org_id == org_id,
            )
        ).scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=404, detail="Organization settings not found.")
    return {"booking_link": link}


@router.post("/calendar/bookings", status_code=201)
def create_booking(
    payload: CalendarBookingRequest,
    org_id: CurrentOrg,
) -> dict[str, Any]:
    from week4.main import engine

    with tenant_transaction(org_id, engine=engine) as connection:
        lead = connection.execute(
            select(models.companies.c.id).where(
                models.companies.c.id == payload.lead_id,
                models.companies.c.org_id == org_id,
            )
        ).first()
        inbox = connection.execute(
            select(models.inboxes.c.id).where(
                models.inboxes.c.org_id == org_id,
                models.inboxes.c.encrypted_token != "",
            ).order_by(models.inboxes.c.id)
        ).first()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    if inbox is None:
        raise HTTPException(status_code=409, detail="Connect a Google Calendar inbox first.")
    busy = google_freebusy(
        org_id,
        inbox["id"],
        payload.starts_at,
        payload.ends_at,
        engine=engine,
    )
    requested_start = payload.starts_at.timestamp()
    requested_end = payload.ends_at.timestamp()
    for period in busy:
        busy_start = datetime.fromisoformat(period["start"].replace("Z", "+00:00")).timestamp()
        busy_end = datetime.fromisoformat(period["end"].replace("Z", "+00:00")).timestamp()
        if requested_start < busy_end and requested_end > busy_start:
            raise HTTPException(status_code=409, detail="The requested time is not available.")
    with tenant_transaction(org_id, engine=engine) as connection:
        booking_id = connection.execute(
            models.bookings.insert()
            .values(
                org_id=org_id,
                lead_id=payload.lead_id,
                starts_at=payload.starts_at,
                ends_at=payload.ends_at,
                status="requested",
            )
            .returning(models.bookings.c.id)
        ).scalar_one()
    return {"id": int(booking_id), "status": "requested"}


@router.get("/analytics/ab")
def ab_results(org_id: CurrentOrg) -> dict[str, Any]:
    from week4.main import engine

    with tenant_transaction(org_id, engine=engine) as connection:
        rows = connection.execute(
            text(
                "SELECT version, outcome, COUNT(*) AS count FROM prompt_experiments "
                "WHERE org_id = :org_id GROUP BY version, outcome ORDER BY version, outcome"
            ),
            {"org_id": org_id},
        ).mappings().all()
    return {
        version: {
            outcome: count
            for row in rows
            if row["version"] == version
            for outcome, count in [(row["outcome"], row["count"])]
        }
        for version in ("v1", "v2")
    }


@router.post("/analytics/experiments", status_code=201)
def record_prompt_outcome(
    payload: PromptExperimentRequest,
    org_id: CurrentOrg,
) -> dict[str, int]:
    from week4.main import engine

    with tenant_transaction(org_id, engine=engine) as connection:
        lead = connection.execute(
            select(models.companies.c.id).where(
                models.companies.c.id == payload.lead_id,
                models.companies.c.org_id == org_id,
            )
        ).first()
        if lead is None:
            raise HTTPException(status_code=404, detail="Lead not found.")
        experiment_id = connection.execute(
            models.prompt_experiments.insert()
            .values(org_id=org_id, **payload.model_dump())
            .returning(models.prompt_experiments.c.id)
        ).scalar_one()
    return {"id": int(experiment_id)}


@router.get("/analytics/costs")
def cost_dashboard(org_id: CurrentOrg) -> dict[str, Any]:
    from week4.main import engine

    with tenant_transaction(org_id, engine=engine) as connection:
        organization = connection.execute(
            select(models.orgs.c.plan).where(models.orgs.c.id == org_id)
        ).scalar_one_or_none()
        rows = connection.execute(
            text(
                "SELECT c.id AS lead_id, c.name, "
                "COALESCE(SUM(t.input_tokens + t.output_tokens), 0) AS tokens_used "
                "FROM companies c LEFT JOIN token_usage t "
                "ON t.lead_id = c.id AND t.org_id = c.org_id "
                "WHERE c.org_id = :org_id GROUP BY c.id, c.name ORDER BY c.name"
            ),
            {"org_id": org_id},
        ).mappings().all()
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found.")
    return {
        "plan": organization,
        "plan_price_usd": float(os.getenv("STRIPE_STARTER_PRICE_USD", "0")),
        "ai_provider_cost_usd": 0.0,
        "note": "The Gemini free tier has no metered API charge here; add any later paid infrastructure costs separately.",
        "leads": [dict(row) | {"ai_provider_cost_usd": 0.0} for row in rows],
    }


@router.get("/evals/replies")
def reply_evaluation() -> dict[str, Any]:
    return evaluate_fake_replies()


@router.post("/billing/checkout")
def checkout(org_id: CurrentOrg, identity: CurrentIdentity) -> dict[str, str]:
    if identity["role"] != "owner":
        raise HTTPException(status_code=403, detail="Only an organization owner can manage billing.")
    return {"checkout_url": create_checkout_session(org_id)}


@router.post("/billing/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict[str, bool]:
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > 1_000_000:
        raise HTTPException(status_code=413, detail="Stripe webhook payload is too large.")
    payload = await request.body()
    if len(payload) > 1_000_000:
        raise HTTPException(status_code=413, detail="Stripe webhook payload is too large.")
    verify_stripe_signature(payload, stripe_signature)
    try:
        event = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise HTTPException(status_code=400, detail="Stripe webhook JSON is invalid.") from error
    if not isinstance(event, dict):
        raise HTTPException(status_code=400, detail="Stripe webhook body must be an object.")
    return {"processed": handle_stripe_event(event)}
