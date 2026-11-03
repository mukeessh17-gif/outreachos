"""Gmail, outbox, contacts, feedback, and privacy data endpoints."""

import os
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import RedirectResponse
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError

from week4 import models
from week4.auth import CurrentIdentity, CurrentOrg
from week4.db import tenant_transaction
from week4.email_delivery import (
    add_suppression,
    complete_google_authorization,
    create_google_authorization_url,
    send_approved_draft,
    verify_unsubscribe_token,
)
from week4.schemas import ContactCreate, FeedbackRequest, InboxCreate, OutboxSendRequest

router = APIRouter(tags=["integrations and compliance"])


@router.post("/leads/{lead_id}/contacts", status_code=201)
def create_contact(
    lead_id: int,
    payload: ContactCreate,
    org_id: CurrentOrg,
) -> dict[str, Any]:
    from week4.main import engine

    try:
        with tenant_transaction(org_id, engine=engine) as connection:
            lead_exists = connection.execute(
                select(models.companies.c.id).where(
                    models.companies.c.id == lead_id,
                    models.companies.c.org_id == org_id,
                )
            ).first()
            if lead_exists is None:
                raise HTTPException(status_code=404, detail="Lead not found.")
            row = connection.execute(
                models.contacts.insert()
                .values(org_id=org_id, company_id=lead_id, **payload.model_dump())
                .returning(
                    models.contacts.c.id,
                    models.contacts.c.company_id,
                    models.contacts.c.full_name,
                    models.contacts.c.email,
                    models.contacts.c.role,
                    models.contacts.c.status,
                )
            ).mappings().one()
    except IntegrityError as error:
        raise HTTPException(status_code=409, detail="This contact already exists for the lead.") from error
    return dict(row)


@router.get("/leads/{lead_id}/contacts")
def list_contacts(lead_id: int, org_id: CurrentOrg) -> list[dict[str, Any]]:
    from week4.main import engine

    with tenant_transaction(org_id, engine=engine) as connection:
        rows = connection.execute(
            select(
                models.contacts.c.id,
                models.contacts.c.company_id,
                models.contacts.c.full_name,
                models.contacts.c.email,
                models.contacts.c.role,
                models.contacts.c.status,
            ).where(
                models.contacts.c.org_id == org_id,
                models.contacts.c.company_id == lead_id,
            )
        ).mappings().all()
    return [dict(row) for row in rows]


@router.post("/integrations/google/start")
def google_oauth_start(org_id: CurrentOrg) -> dict[str, str]:
    from week4.main import engine

    return {"authorization_url": create_google_authorization_url(org_id, engine=engine)}


@router.get("/integrations/google/callback")
def google_oauth_callback(code: str, state: str) -> RedirectResponse:
    from week4.main import engine

    org_id = complete_google_authorization(code, state, engine=engine)
    frontend = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")
    return RedirectResponse(
        url=f"{frontend}/settings?gmail=connected&org={quote(str(org_id))}",
        status_code=303,
    )


@router.post("/inboxes", status_code=201)
def create_dry_run_inbox(payload: InboxCreate, org_id: CurrentOrg) -> dict[str, Any]:
    from week4.main import engine

    with tenant_transaction(org_id, engine=engine) as connection:
        insert = postgresql_insert if connection.dialect.name == "postgresql" else sqlite_insert
        inserted = connection.execute(
            insert(models.inboxes)
            .values(org_id=org_id, email=payload.email, encrypted_token="")
            .on_conflict_do_nothing(
                index_elements=[models.inboxes.c.org_id, models.inboxes.c.email]
            )
            .returning(models.inboxes.c.id)
        ).scalar_one_or_none()
        row = connection.execute(
            select(
                models.inboxes.c.id,
                models.inboxes.c.email,
                models.inboxes.c.daily_limit,
                models.inboxes.c.encrypted_token,
            ).where(
                models.inboxes.c.org_id == org_id,
                models.inboxes.c.email == payload.email,
            )
        ).mappings().one()
    return {
        "id": row["id"],
        "email": row["email"],
        "daily_limit": row["daily_limit"],
        "connected": bool(row["encrypted_token"]),
        "created": inserted is not None,
    }


@router.get("/inboxes")
def list_inboxes(org_id: CurrentOrg) -> list[dict[str, Any]]:
    from week4.main import engine

    with tenant_transaction(org_id, engine=engine) as connection:
        rows = connection.execute(
            select(
                models.inboxes.c.id,
                models.inboxes.c.email,
                models.inboxes.c.daily_limit,
                models.inboxes.c.encrypted_token,
            ).where(models.inboxes.c.org_id == org_id)
        ).mappings().all()
    return [
        {
            "id": row["id"],
            "email": row["email"],
            "daily_limit": row["daily_limit"],
            "connected": bool(row["encrypted_token"]),
        }
        for row in rows
    ]


@router.post("/outbox/send")
def send_draft(payload: OutboxSendRequest, org_id: CurrentOrg) -> dict[str, Any]:
    from week4.main import engine

    return send_approved_draft(
        org_id,
        payload.draft_id,
        payload.inbox_id,
        payload.recipient,
        engine=engine,
    )


@router.get("/outbox")
def list_outbox(
    org_id: CurrentOrg,
    outbox_status: str | None = Query(
        default=None,
        alias="status",
        pattern="^(scheduled|processing|dry_run|pending|sent|failed)$",
    ),
) -> list[dict[str, Any]]:
    from week4.main import engine

    statement = text(
        "SELECT id, lead_id, draft_id, inbox_id, recipient, subject, body, status, "
        "created_at, scheduled_at, sent_at FROM outbox WHERE org_id = :org_id"
        + (" AND status = :status" if outbox_status else "")
        + " ORDER BY created_at DESC LIMIT 200"
    )
    params: dict[str, Any] = {"org_id": org_id}
    if outbox_status:
        params["status"] = outbox_status
    with tenant_transaction(org_id, engine=engine) as connection:
        rows = connection.execute(statement, params).mappings().all()
    return [dict(row) for row in rows]


@router.get("/unsubscribe")
def inspect_unsubscribe(token: str) -> dict[str, str]:
    verify_unsubscribe_token(token)
    return {"message": "Confirm to add this address to the permanent suppression list."}


@router.post("/unsubscribe")
def unsubscribe(token: str) -> dict[str, str]:
    from week4.main import engine

    org_id, email = verify_unsubscribe_token(token)
    add_suppression(org_id, email, "unsubscribe", engine=engine)
    return {"message": "This address has been permanently unsubscribed."}


@router.post("/integrations/bounce")
def record_bounce(email: str, org_id: CurrentOrg) -> dict[str, str]:
    from week4.main import engine

    add_suppression(org_id, email, "bounce", engine=engine)
    return {"status": "suppressed"}


@router.post("/feedback", status_code=201)
def save_feedback(payload: FeedbackRequest, org_id: CurrentOrg) -> dict[str, int]:
    from week4.main import engine

    with tenant_transaction(org_id, engine=engine) as connection:
        feedback_id = connection.execute(
            models.feedback.insert()
            .values(org_id=org_id, **payload.model_dump())
            .returning(models.feedback.c.id)
        ).scalar_one()
    return {"id": int(feedback_id)}


@router.get("/data/export")
def export_org_data(org_id: CurrentOrg) -> dict[str, Any]:
    from week4.main import engine

    export: dict[str, Any] = {}
    with tenant_transaction(org_id, engine=engine) as connection:
        organization = connection.execute(
            select(models.orgs.c.id, models.orgs.c.name, models.orgs.c.plan).where(
                models.orgs.c.id == org_id,
            )
        ).mappings().first()
        if organization is None:
            raise HTTPException(status_code=404, detail="Organization not found.")
        export["organization"] = dict(organization)
        export["members"] = [
            dict(row)
            for row in connection.execute(
                text(
                    "SELECT u.id, u.email, m.role FROM users u "
                    "JOIN memberships m ON m.user_id = u.id "
                    "WHERE m.org_id = :org_id"
                ),
                {"org_id": org_id},
            ).mappings().all()
        ]
        for table_name, table in models.metadata.tables.items():
            if table_name in {"oauth_states", "users", "orgs"} or "org_id" not in table.c:
                continue
            columns = [column for column in table.c if column.name != "encrypted_token"]
            rows = connection.execute(
                select(*columns).where(table.c.org_id == org_id)
            ).mappings().all()
            export[table_name] = [dict(row) for row in rows]
    return jsonable_encoder(export)


@router.delete("/data/account")
def delete_org_data(
    confirmation: str,
    org_id: CurrentOrg,
    identity: CurrentIdentity,
) -> dict[str, str]:
    from week4.main import engine

    if identity["role"] != "owner":
        raise HTTPException(status_code=403, detail="Only an organization owner can delete workspace data.")
    with tenant_transaction(org_id, int(identity["user_id"]), engine=engine) as connection:
        organization = connection.execute(
            select(models.orgs.c.name).where(models.orgs.c.id == org_id)
        ).scalar_one_or_none()
        if organization is None:
            raise HTTPException(status_code=404, detail="Organization not found.")
        if confirmation.strip() != organization:
            raise HTTPException(status_code=400, detail="Confirmation must exactly match the workspace name.")
        connection.execute(
            models.orgs.delete().where(models.orgs.c.id == org_id)
        )
        connection.execute(
            text(
                "DELETE FROM users WHERE id = :user_id "
                "AND NOT EXISTS (SELECT 1 FROM memberships WHERE user_id = :user_id)"
            ),
            {"user_id": identity["user_id"]},
        )
    return {"status": "deleted"}
