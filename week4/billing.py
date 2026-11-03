"""Stripe test-mode checkout and signed, idempotent webhook processing."""

import hashlib
import hmac
import os
import time
from typing import Any

import httpx
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Engine

from week2.db import get_engine
from week4 import models
from week4.db import tenant_transaction

STRIPE_CHECKOUT_ENDPOINT = "https://api.stripe.com/v1/checkout/sessions"


def create_checkout_session(org_id: int, *, engine: Engine | None = None) -> str:
    secret_key = os.getenv("STRIPE_SECRET_KEY", "")
    price_id = os.getenv("STRIPE_PRICE_ID", "")
    if not secret_key.startswith("sk_test_"):
        raise HTTPException(status_code=503, detail="Configure a Stripe TEST-mode key before checkout.")
    if not price_id:
        raise HTTPException(status_code=503, detail="Configure STRIPE_PRICE_ID for a Stripe test product.")
    success_url = os.getenv("STRIPE_SUCCESS_URL", "http://localhost:3000/settings?billing=success")
    cancel_url = os.getenv("STRIPE_CANCEL_URL", "http://localhost:3000/settings?billing=cancelled")
    try:
        response = httpx.post(
            STRIPE_CHECKOUT_ENDPOINT,
            auth=(secret_key, ""),
            data={
                "mode": "subscription",
                "line_items[0][price]": price_id,
                "line_items[0][quantity]": "1",
                "success_url": success_url,
                "cancel_url": cancel_url,
                "metadata[org_id]": str(org_id),
                "metadata[plan]": "starter",
                "subscription_data[metadata][org_id]": str(org_id),
                "subscription_data[metadata][plan]": "starter",
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise HTTPException(status_code=502, detail="Stripe test checkout could not be created.") from error
    url = payload.get("url")
    if not isinstance(url, str) or not url.startswith("https://checkout.stripe.com/"):
        raise HTTPException(status_code=502, detail="Stripe returned an invalid checkout URL.")
    return url


def verify_stripe_signature(
    payload: bytes,
    signature_header: str | None,
    *,
    now: int | None = None,
) -> None:
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if not secret.startswith("whsec_") or not signature_header:
        raise HTTPException(status_code=400, detail="Stripe webhook signature is missing or not configured.")
    parts: dict[str, list[str]] = {}
    for item in signature_header.split(","):
        key, separator, value = item.partition("=")
        if separator:
            parts.setdefault(key, []).append(value)
    try:
        timestamp = int(parts["t"][0])
        signatures = parts["v1"]
    except (KeyError, IndexError, ValueError) as error:
        raise HTTPException(status_code=400, detail="Stripe webhook signature is malformed.") from error
    current_time = int(time.time()) if now is None else now
    if abs(current_time - timestamp) > 300:
        raise HTTPException(status_code=400, detail="Stripe webhook signature has expired.")
    signed_payload = str(timestamp).encode("ascii") + b"." + payload
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, candidate) for candidate in signatures):
        raise HTTPException(status_code=400, detail="Stripe webhook signature is invalid.")


def handle_stripe_event(
    event: dict[str, Any],
    *,
    engine: Engine | None = None,
) -> bool:
    event_id = event.get("id")
    event_type = event.get("type")
    if not isinstance(event_id, str) or not isinstance(event_type, str):
        raise HTTPException(status_code=400, detail="Stripe event is malformed.")
    if event.get("livemode") is not False:
        raise HTTPException(status_code=400, detail="Only Stripe TEST-mode events are accepted.")
    if event_type not in {
        "checkout.session.completed",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        return False
    event_data = event.get("data")
    data = event_data.get("object", {}) if isinstance(event_data, dict) else {}
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Stripe event payload is malformed.")
    metadata = data.get("metadata", {}) if isinstance(data, dict) else {}
    if not isinstance(metadata, dict):
        raise HTTPException(status_code=400, detail="Stripe event metadata is malformed.")
    try:
        org_id = int(metadata["org_id"])
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=400, detail="Stripe event is missing its organization metadata.") from error
    plan = metadata.get("plan", "free")
    if plan not in {"free", "starter", "team"}:
        raise HTTPException(status_code=400, detail="Stripe event contains an unsupported plan.")
    database = engine or get_engine()
    with tenant_transaction(org_id, engine=database) as connection:
        organization_exists = connection.execute(
            select(models.orgs.c.id).where(models.orgs.c.id == org_id)
        ).first()
        if organization_exists is None:
            raise HTTPException(status_code=404, detail="Stripe event organization was not found.")
        insert = postgresql_insert if connection.dialect.name == "postgresql" else sqlite_insert
        inserted = connection.execute(
            insert(models.stripe_events)
            .values(id=event_id, org_id=org_id, event_type=event_type)
            .on_conflict_do_nothing(index_elements=[models.stripe_events.c.id])
            .returning(models.stripe_events.c.id)
        ).scalar_one_or_none()
        if inserted is None:
            return False
        if event_type in {"checkout.session.completed", "customer.subscription.updated"}:
            connection.execute(
                update(models.orgs)
                .where(models.orgs.c.id == org_id)
                .values(plan=plan)
            )
            subscription_id = data.get("subscription") or data.get("id")
            connection.execute(
                insert(models.stripe_subscriptions)
                .values(
                    org_id=org_id,
                    customer_id=data.get("customer"),
                    subscription_id=subscription_id,
                    price_id=os.getenv("STRIPE_PRICE_ID"),
                    status=str(data.get("status", "active")),
                )
                .on_conflict_do_update(
                    index_elements=[models.stripe_subscriptions.c.org_id],
                    set_={
                        "customer_id": data.get("customer"),
                        "subscription_id": subscription_id,
                        "price_id": os.getenv("STRIPE_PRICE_ID"),
                        "status": str(data.get("status", "active")),
                    },
                )
            )
        elif event_type == "customer.subscription.deleted":
            connection.execute(
                update(models.orgs)
                .where(models.orgs.c.id == org_id)
                .values(plan="free")
            )
            connection.execute(
                update(models.stripe_subscriptions)
                .where(models.stripe_subscriptions.c.org_id == org_id)
                .values(status="canceled")
            )
    return True
