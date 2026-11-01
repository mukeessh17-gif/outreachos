# Week 3 Day 3: FastAPI basics
# OutreachOS - AI sales outreach tool
# Run from repo root: uvicorn week3.app.main:app --reload
# Then open: http://localhost:8000/docs

import sys
import os
import uuid
import logging
import time

# Add repo root to path so we can import week2.db.get_engine().
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, HTTPException, status, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from week2.db import get_engine
from .schemas import LeadCreate, LeadOut
from .logging_config import setup_logging, set_request_id
from .retry import retry_with_backoff

app = FastAPI(title="OutreachOS Leads API")

# Set up logging before anything else.
setup_logging()
logger = logging.getLogger("outreachos.app")

# Add middleware that logs every request: method, path, status code, duration.
# Never log request bodies or secrets.
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    set_request_id(request_id)

    start = time.monotonic()
    try:
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "%s %s -> %s (%dms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
    except Exception as error:
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.exception(
            "%s %s -> 500 (%dms) error: %s",
            request.method,
            request.url.path,
            duration_ms,
            error,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

# Allow only the local frontend origin. Never use "*" in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)

# Reuse the same engine from week2/db.py (connection pool).
engine = get_engine()


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint. Returns ok if the API is running."""
    return {"status": "ok"}


@app.get("/leads")
def list_leads(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
) -> list[dict]:
    """Return companies with optional pagination and name search."""
    # Build the query with parameters only - never f-strings in SQL.
    sql = "SELECT id, name, city, employees, has_website, created_at FROM companies"
    params: dict = {}

    if search:
        sql += " WHERE name ILIKE :search"
        params["search"] = f"%{search}%"

    sql += " ORDER BY id LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset

    with engine.connect() as connection:
        result = connection.execute(text(sql), params)
        leads = [dict(row._mapping) for row in result.fetchall()]
    return leads


# NOTE: /leads/good must be defined BEFORE /leads/{lead_id}.
# FastAPI matches routes in order. If /leads/{lead_id} came first,
# the path "good" would be captured as lead_id="good" and this route
# would never be reached.
@app.get("/leads/good")
def list_good_leads() -> list[dict]:
    """Return leads with 5-20 employees AND a website, sorted by score."""
    with engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT id, name, city, employees, has_website, created_at
                FROM companies
                WHERE employees >= 5 AND employees <= 20 AND has_website = TRUE
                ORDER BY id
            """)
        )
        leads = [dict(row._mapping) for row in result.fetchall()]

    # Sort by score (10 = both good, 5 = only one, 0 = neither).
    # Python's sorted is stable, so ties keep database order.
    def score(lead: dict) -> int:
        good_size = 5 <= (lead["employees"] or 0) <= 20
        if good_size and lead["has_website"]:
            return 10
        if good_size or lead["has_website"]:
            return 5
        return 0

    leads.sort(key=score, reverse=True)
    return leads


@app.post("/leads", status_code=status.HTTP_201_CREATED, response_model=LeadOut)
def create_lead(lead: LeadCreate) -> dict:
    """Create a new lead. Returns 201 on success, 409 if name already exists."""
    with engine.connect() as connection:
        result = connection.execute(
            text("""
                INSERT INTO companies (name, city, employees, has_website)
                VALUES (:name, :city, :employees, :has_website)
                ON CONFLICT (name) DO NOTHING
                RETURNING id, name, city, employees, has_website, created_at
            """),
            {
                "name": lead.name,
                "city": lead.city,
                "employees": lead.employees,
                "has_website": lead.has_website,
            },
        )
        row = result.fetchone()
        connection.commit()

    if row is None:
        # ON CONFLICT skipped because a company with this name exists.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A company named '{lead.name}' already exists.",
        )

    return dict(row._mapping)


@app.patch("/leads/{lead_id}")
def update_lead(
    lead_id: int,
    employees: int | None = None,
    has_website: bool | None = None,
) -> dict:
    """Update employees and/or has_website for a lead. Returns 404 if not found."""
    updates = []
    params: dict = {"id": lead_id}

    if employees is not None:
        updates.append("employees = :employees")
        params["employees"] = employees

    if has_website is not None:
        updates.append("has_website = :has_website")
        params["has_website"] = has_website

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update.",
        )

    sql = f"UPDATE companies SET {', '.join(updates)} WHERE id = :id RETURNING id, name, city, employees, has_website, created_at"

    with engine.connect() as connection:
        result = connection.execute(text(sql), params)
        row = result.fetchone()
        connection.commit()

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    return dict(row._mapping)


@app.delete("/leads/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(lead_id: int) -> None:
    """Delete a lead by id. Returns 204 on success, 404 if not found."""
    with engine.connect() as connection:
        result = connection.execute(
            text("DELETE FROM companies WHERE id = :id RETURNING id"),
            {"id": lead_id},
        )
        row = result.fetchone()
        connection.commit()

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")


@app.get("/leads/{lead_id}")
def get_lead(lead_id: int) -> dict:
    """Return one company by id, or 404 if not found."""
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT id, name, city, employees, has_website, created_at FROM companies WHERE id = :id"),
            {"id": lead_id},
        )
        row = result.fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return dict(row._mapping)