"""Authenticated, organization-scoped OutreachOS API."""

import csv
import io
import logging
import os
import time
import uuid
from typing import Annotated, Any
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import JSON, bindparam, text
from sqlalchemy.exc import IntegrityError

from week2.db import get_engine
from week3.app.logging_config import set_request_id, setup_logging
from week4.auth import CurrentOrg
from week4.auth_routes import router as auth_router
from week4.advanced_routes import router as advanced_router
from week4.db import tenant_transaction
from week4.email_routes import router as email_router
from week4.job_queue import enqueue_job
from week4.job_routes import router as jobs_router
from week4 import models
from week4.plan_limits import enforce_lead_limit
from week4.integration_routes import router as integration_router
from week4.schemas import LeadCreate, LeadPatch, SettingsUpdate

load_dotenv()
setup_logging()
logger = logging.getLogger("outreachos.api")
engine = get_engine()


def _sanitize_sentry_event(event: dict[str, Any], _hint: Any) -> dict[str, Any]:
    request_data = event.get("request")
    if isinstance(request_data, dict):
        url = request_data.get("url")
        if isinstance(url, str):
            parsed = urlsplit(url)
            request_data["url"] = urlunsplit(
                (parsed.scheme, parsed.netloc, parsed.path, "", "")
            )
        headers = request_data.get("headers")
        if isinstance(headers, dict):
            request_data["headers"] = {
                key: value
                for key, value in headers.items()
                if key.casefold() not in {"authorization", "cookie", "set-cookie"}
            }
        request_data.pop("data", None)
    return event


if os.getenv("SENTRY_DSN"):
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration

    sentry_sdk.init(
        dsn=os.environ["SENTRY_DSN"],
        integrations=[FastApiIntegration()],
        send_default_pii=False,
        traces_sample_rate=0.0,
        before_send=_sanitize_sentry_event,
    )

app = FastAPI(title="OutreachOS API", version="4.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth_router)
app.include_router(email_router)
app.include_router(jobs_router)
app.include_router(integration_router)
app.include_router(advanced_router)


@app.middleware("http")
async def request_logging(request: Request, call_next: Any) -> Response:
    request_id = str(uuid.uuid4())[:8]
    set_request_id(request_id)
    started = time.monotonic()
    try:
        response = await call_next(request)
    except Exception as error:
        logger.error(
            "request failed req=%s method=%s path=%s error_type=%s",
            request_id,
            request.method,
            request.url.path,
            type(error).__name__,
        )
        raise
    logger.info(
        "%s %s -> %s (%dms)",
        request.method,
        request.url.path,
        response.status_code,
        int((time.monotonic() - started) * 1000),
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _lead_query(connection: Any, org_id: int, lead_id: int) -> dict[str, Any]:
    row = connection.execute(
        text(
            "SELECT id, org_id, name, city, employees, has_website, website, "
            "pipeline_stage, created_at FROM companies "
            "WHERE id = :lead_id AND org_id = :org_id"
        ),
        {"lead_id": lead_id, "org_id": org_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return dict(row)


@app.get("/leads")
def list_leads(
    org_id: CurrentOrg,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=100),
    stage: str | None = Query(default=None, pattern="^(new|contacted|replied|meeting|closed)$"),
) -> list[dict[str, Any]]:
    conditions = ["org_id = :org_id"]
    params: dict[str, Any] = {"org_id": org_id, "limit": limit, "offset": offset}
    if search:
        conditions.append("LOWER(name) LIKE LOWER(:search)")
        params["search"] = f"%{search}%"
    if stage:
        conditions.append("pipeline_stage = :stage")
        params["stage"] = stage
    with tenant_transaction(org_id, engine=engine) as connection:
        rows = connection.execute(
            text(
                "SELECT id, name, city, employees, has_website, website, "
                "pipeline_stage, created_at FROM companies WHERE "
                + " AND ".join(conditions)
                + " ORDER BY id LIMIT :limit OFFSET :offset"
            ),
            params,
        ).mappings().all()
    return [dict(row) for row in rows]


@app.get("/leads/good")
def list_good_leads(org_id: CurrentOrg) -> list[dict[str, Any]]:
    with tenant_transaction(org_id, engine=engine) as connection:
        rows = connection.execute(
            text(
                "SELECT id, name, city, employees, has_website, website, "
                "pipeline_stage, created_at FROM companies "
                "WHERE org_id = :org_id AND employees BETWEEN 5 AND 20 "
                "AND has_website = TRUE ORDER BY id"
            ),
            {"org_id": org_id},
        ).mappings().all()
    return [dict(row) for row in rows]


@app.post("/leads/{lead_id}/research")
def research_company(lead_id: int, org_id: CurrentOrg) -> dict[str, Any]:
    with tenant_transaction(org_id, engine=engine) as connection:
        exists = connection.execute(
            text("SELECT 1 FROM companies WHERE id = :lead_id AND org_id = :org_id"),
            {"lead_id": lead_id, "org_id": org_id},
        ).first()
    if exists is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    job_id = enqueue_job(org_id, lead_id, "research", engine=engine)
    return {"job_id": job_id, "lead_id": lead_id, "status": "pending"}


@app.post("/leads", status_code=status.HTTP_201_CREATED)
def create_lead(payload: LeadCreate, org_id: CurrentOrg) -> dict[str, Any]:
    try:
        with tenant_transaction(org_id, engine=engine) as connection:
            enforce_lead_limit(connection, org_id)
            row = connection.execute(
                text(
                    "INSERT INTO companies "
                    "(org_id, name, city, employees, has_website, website) "
                    "VALUES (:org_id, :name, :city, :employees, :has_website, :website) "
                    "RETURNING id, name, city, employees, has_website, website, "
                    "pipeline_stage, created_at"
                ),
                {"org_id": org_id, **payload.model_dump()},
            ).mappings().one()
    except IntegrityError as error:
        raise HTTPException(status_code=409, detail="A lead with this name already exists.") from error
    return dict(row)


@app.get("/leads/{lead_id}")
def get_lead(lead_id: int, org_id: CurrentOrg) -> dict[str, Any]:
    with tenant_transaction(org_id, engine=engine) as connection:
        return _lead_query(connection, org_id, lead_id)


@app.patch("/leads/{lead_id}")
def update_lead(lead_id: int, payload: LeadPatch, org_id: CurrentOrg) -> dict[str, Any]:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Provide at least one field to update.")
    assignments = ", ".join(f"{key} = :{key}" for key in updates)
    try:
        with tenant_transaction(org_id, engine=engine) as connection:
            previous_stage = None
            if "pipeline_stage" in updates:
                previous_stage = connection.execute(
                    text(
                        "SELECT pipeline_stage FROM companies "
                        "WHERE id = :lead_id AND org_id = :org_id"
                    ),
                    {"lead_id": lead_id, "org_id": org_id},
                ).scalar_one_or_none()
            row = connection.execute(
                text(
                    "UPDATE companies SET "
                    + assignments
                    + " WHERE id = :lead_id AND org_id = :org_id "
                    + "RETURNING id, name, city, employees, has_website, website, "
                    "pipeline_stage, created_at"
                ),
                {**updates, "lead_id": lead_id, "org_id": org_id},
            ).mappings().first()
            if (
                row is not None
                and "pipeline_stage" in updates
                and previous_stage != row["pipeline_stage"]
            ):
                connection.execute(
                    models.pipeline_events.insert().values(
                        org_id=org_id,
                        lead_id=lead_id,
                        stage=row["pipeline_stage"],
                    )
                )
    except IntegrityError as error:
        raise HTTPException(status_code=409, detail="A lead with this name already exists.") from error
    if row is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return dict(row)


@app.delete("/leads/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(lead_id: int, org_id: CurrentOrg) -> Response:
    with tenant_transaction(org_id, engine=engine) as connection:
        result = connection.execute(
            text("DELETE FROM companies WHERE id = :lead_id AND org_id = :org_id"),
            {"lead_id": lead_id, "org_id": org_id},
        )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def parse_lead_csv(content: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    reader = csv.DictReader(io.StringIO(content))
    headers = {header.strip().lower() for header in (reader.fieldnames or [])}
    if not {"name", "employees"}.issubset(headers):
        raise HTTPException(
            status_code=422,
            detail="CSV must include at least the name and employees columns.",
        )
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for line_number, row in enumerate(reader, start=2):
        normalized = {key.strip().lower(): (value or "").strip() for key, value in row.items() if key}
        try:
            lead = LeadCreate(
                name=normalized.get("name", ""),
                city=normalized.get("city") or None,
                employees=int(normalized.get("employees", "")),
                website=normalized.get("website") or None,
                has_website=bool(normalized.get("website")),
            )
        except (ValueError, TypeError) as error:
            rejected.append({"row": line_number, "reason": str(error)})
            continue
        accepted.append(lead.model_dump())
    if not accepted and not rejected:
        raise HTTPException(status_code=422, detail="CSV has no data rows.")
    return accepted, rejected


async def _read_csv_body(request: Request) -> str:
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > 2_000_000:
                raise HTTPException(status_code=413, detail="CSV upload must be 2 MB or smaller.")
        except ValueError as error:
            raise HTTPException(status_code=400, detail="Content-Length header is invalid.") from error
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > 2_000_000:
            raise HTTPException(status_code=413, detail="CSV upload must be 2 MB or smaller.")
    try:
        return bytes(content).decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise HTTPException(status_code=422, detail="CSV must be valid UTF-8 text.") from error


@app.post("/leads/import/preview")
async def preview_csv(request: Request, _org_id: CurrentOrg) -> dict[str, Any]:
    content = await _read_csv_body(request)
    accepted, rejected = parse_lead_csv(content)
    return {"accepted_count": len(accepted), "accepted": accepted, "rejected": rejected}


@app.post("/leads/import")
async def import_csv(request: Request, org_id: CurrentOrg) -> dict[str, Any]:
    content = await _read_csv_body(request)
    accepted, rejected = parse_lead_csv(content)
    inserted = 0
    duplicates = 0
    with tenant_transaction(org_id, engine=engine) as connection:
        for lead in accepted:
            exists = connection.execute(
                text("SELECT 1 FROM companies WHERE org_id = :org_id AND name = :name"),
                {"org_id": org_id, "name": lead["name"]},
            ).first()
            if exists is not None:
                duplicates += 1
                continue
            enforce_lead_limit(connection, org_id)
            result = connection.execute(
                text(
                    "INSERT INTO companies "
                    "(org_id, name, city, employees, has_website, website) "
                    "VALUES (:org_id, :name, :city, :employees, :has_website, :website) "
                    "ON CONFLICT (org_id, name) DO NOTHING RETURNING id"
                ),
                {"org_id": org_id, **lead},
            )
            if result.first() is None:
                duplicates += 1
            else:
                inserted += 1
    return {"inserted": inserted, "duplicates": duplicates, "rejected": rejected}


@app.get("/settings")
def get_settings(org_id: CurrentOrg) -> dict[str, Any]:
    with tenant_transaction(org_id, engine=engine) as connection:
        row = connection.execute(
            text(
                "SELECT tone, sample_emails, banned_phrases, sender_postal_address, calendar_link, "
                "daily_token_budget, per_lead_token_budget, daily_lead_limit "
                "FROM org_settings WHERE org_id = :org_id"
            ),
            {"org_id": org_id},
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Organization settings not found.")
    return dict(row)


@app.put("/settings")
def put_settings(payload: SettingsUpdate, org_id: CurrentOrg) -> dict[str, Any]:
    fields = payload.model_dump()
    assignments = ", ".join(f"{key} = :{key}" for key in fields)
    statement = text(
        "UPDATE org_settings SET "
        + assignments
        + " WHERE org_id = :org_id RETURNING tone, sample_emails, banned_phrases, "
        "sender_postal_address, calendar_link, daily_token_budget, per_lead_token_budget, daily_lead_limit"
    ).bindparams(
        bindparam("sample_emails", type_=JSON),
        bindparam("banned_phrases", type_=JSON),
    )
    with tenant_transaction(org_id, engine=engine) as connection:
        row = connection.execute(
            statement,
            {"org_id": org_id, **fields},
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Organization settings not found.")
    return dict(row)


@app.get("/pipeline")
def pipeline(org_id: CurrentOrg) -> dict[str, list[dict[str, Any]]]:
    stages = ("new", "contacted", "replied", "meeting", "closed")
    with tenant_transaction(org_id, engine=engine) as connection:
        result: dict[str, list[dict[str, Any]]] = {}
        for stage in stages:
            rows = connection.execute(
                text(
                    "SELECT id, name, city, employees, pipeline_stage, created_at "
                    "FROM companies WHERE org_id = :org_id AND pipeline_stage = :stage "
                    "ORDER BY created_at DESC"
                ),
                {"org_id": org_id, "stage": stage},
            ).mappings().all()
            result[stage] = [dict(row) for row in rows]
    return result


@app.get("/analytics/dashboard")
def dashboard(org_id: CurrentOrg) -> dict[str, int | float]:
    with tenant_transaction(org_id, engine=engine) as connection:
        sent = connection.execute(
            text(
                "SELECT COUNT(*) FROM outbox "
                "WHERE org_id = :org_id AND status = 'sent'"
            ),
            {"org_id": org_id},
        ).scalar_one()
        reply_count = connection.execute(
            text("SELECT COUNT(*) FROM replies WHERE org_id = :org_id"),
            {"org_id": org_id},
        ).scalar_one()
        meetings = connection.execute(
            text(
                "SELECT COUNT(*) FROM companies "
                "WHERE org_id = :org_id AND pipeline_stage = 'meeting'"
            ),
            {"org_id": org_id},
        ).scalar_one()
        lead_count = connection.execute(
            text("SELECT COUNT(*) FROM companies WHERE org_id = :org_id"),
            {"org_id": org_id},
        ).scalar_one()
    return {
        "sent": sent,
        "replies": reply_count,
        "reply_rate": round(reply_count / sent, 4) if sent else 0,
        "meetings": meetings,
        "cost_per_lead": 0,
        "lead_count": lead_count,
    }
