"""Dry-run-first Gmail OAuth, encrypted tokens, outbox, and suppression checks."""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Engine

from week2.db import get_engine
from week4 import models
from week4.auth import _jwt_secret
from week4.db import set_rls_context, tenant_transaction

GOOGLE_SCOPES = (
    "https://www.googleapis.com/auth/gmail.send "
    "https://www.googleapis.com/auth/gmail.readonly "
    "https://www.googleapis.com/auth/calendar.freebusy"
)
GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GMAIL_SEND_ENDPOINT = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
GMAIL_PROFILE_ENDPOINT = "https://gmail.googleapis.com/gmail/v1/users/me/profile"
CALENDAR_FREEBUSY_ENDPOINT = "https://www.googleapis.com/calendar/v3/freeBusy"


def _fernet() -> Fernet:
    key = os.getenv("FERNET_KEY")
    if not key:
        raise RuntimeError("FERNET_KEY must be configured before connecting Google accounts.")
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as error:
        raise RuntimeError("FERNET_KEY must be a valid Fernet key.") from error


def encrypt_token(credentials: dict[str, Any]) -> str:
    payload = json.dumps(credentials, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _fernet().encrypt(payload).decode("ascii")


def decrypt_token(ciphertext: str) -> dict[str, Any]:
    try:
        return json.loads(_fernet().decrypt(ciphertext.encode("ascii")))
    except (InvalidToken, ValueError, UnicodeEncodeError, json.JSONDecodeError) as error:
        raise RuntimeError("Stored Google credentials could not be decrypted.") from error


def create_unsubscribe_token(org_id: int, email: str) -> str:
    return jwt.encode(
        {
            "purpose": "unsubscribe",
            "org_id": org_id,
            "email": email.strip().lower(),
        },
        _jwt_secret(),
        algorithm="HS256",
    )


def verify_unsubscribe_token(token: str) -> tuple[int, str]:
    try:
        claims = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    except jwt.InvalidTokenError as error:
        raise HTTPException(status_code=400, detail="Invalid unsubscribe link.") from error
    email = claims.get("email")
    org_id = claims.get("org_id")
    if claims.get("purpose") != "unsubscribe" or not isinstance(email, str):
        raise HTTPException(status_code=400, detail="Invalid unsubscribe link.")
    try:
        normalized_org_id = int(org_id)
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=400, detail="Invalid unsubscribe link.") from error
    return normalized_org_id, email


def create_google_authorization_url(org_id: int, *, engine: Engine | None = None) -> str:
    client_id = os.getenv("GMAIL_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    if not client_id or not redirect_uri:
        raise HTTPException(
            status_code=503,
            detail="Configure GMAIL_CLIENT_ID and GOOGLE_REDIRECT_URI in .env first.",
        )
    nonce = secrets.token_urlsafe(24)
    state = jwt.encode(
        {
            "purpose": "google_oauth",
            "org_id": org_id,
            "nonce": nonce,
            "exp": int(datetime.now(timezone.utc).timestamp()) + 600,
        },
        _jwt_secret(),
        algorithm="HS256",
    )
    database = engine or get_engine()
    with tenant_transaction(org_id, engine=database) as connection:
        insert = postgresql_insert if connection.dialect.name == "postgresql" else sqlite_insert
        connection.execute(
            insert(models.oauth_states)
            .values(
                org_id=org_id,
                nonce=nonce,
                expires_at=datetime.fromtimestamp(
                    int(datetime.now(timezone.utc).timestamp()) + 600,
                    tz=timezone.utc,
                ),
            )
            .on_conflict_do_update(
                index_elements=[models.oauth_states.c.org_id],
                set_={"nonce": nonce, "expires_at": datetime.fromtimestamp(
                    int(datetime.now(timezone.utc).timestamp()) + 600,
                    tz=timezone.utc,
                )},
            )
        )
    parameters = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(parameters)}"


def _google_post(url: str, data: dict[str, str]) -> dict[str, Any]:
    try:
        response = httpx.post(url, data=data, timeout=15)
        if response.status_code >= 400:
            raise RuntimeError("Google OAuth request was rejected.")
        return response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise RuntimeError("Google OAuth request failed.") from error


def complete_google_authorization(
    code: str,
    state: str,
    *,
    engine: Engine | None = None,
) -> int:
    try:
        claims = jwt.decode(state, _jwt_secret(), algorithms=["HS256"])
        org_id = int(claims["org_id"])
        nonce = str(claims["nonce"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=400, detail="Google authorization state is invalid or expired.") from error
    if claims.get("purpose") != "google_oauth":
        raise HTTPException(status_code=400, detail="Google authorization state is invalid.")

    client_id = os.getenv("GMAIL_CLIENT_ID")
    client_secret = os.getenv("GMAIL_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    if not client_id or not client_secret or not redirect_uri:
        raise HTTPException(status_code=503, detail="Google OAuth environment settings are incomplete.")

    database = engine or get_engine()
    with tenant_transaction(org_id, engine=database) as connection:
        saved_nonce = connection.execute(
            select(models.oauth_states.c.nonce).where(
                models.oauth_states.c.org_id == org_id,
            )
        ).scalar_one_or_none()
    if saved_nonce is None or not hmac.compare_digest(saved_nonce, nonce):
        raise HTTPException(status_code=400, detail="Google authorization state has already been used.")

    tokens = _google_post(
        GOOGLE_TOKEN_ENDPOINT,
        {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
    )
    access_token = tokens.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise HTTPException(status_code=502, detail="Google did not return an access token.")
    try:
        profile_response = httpx.get(
            GMAIL_PROFILE_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        profile_response.raise_for_status()
        email = profile_response.json()["emailAddress"].strip().lower()
    except (httpx.HTTPError, KeyError, ValueError, AttributeError) as error:
        raise HTTPException(status_code=502, detail="Google could not verify the Gmail inbox.") from error

    expires_at = int(datetime.now(timezone.utc).timestamp()) + int(tokens.get("expires_in", 3600))
    encrypted = encrypt_token(
        {
            "access_token": access_token,
            "refresh_token": tokens.get("refresh_token"),
            "expires_at": expires_at,
        }
    )
    with tenant_transaction(org_id, engine=database) as connection:
        set_rls_context(connection, org_id)
        nonce_is_current = connection.execute(
            select(models.oauth_states.c.nonce).where(
                models.oauth_states.c.org_id == org_id,
            )
        ).scalar_one_or_none()
        if nonce_is_current is None or not hmac.compare_digest(nonce_is_current, nonce):
            raise HTTPException(status_code=400, detail="Google authorization state has already been used.")
        connection.execute(
            models.oauth_states.delete().where(models.oauth_states.c.org_id == org_id)
        )
        insert = postgresql_insert if connection.dialect.name == "postgresql" else sqlite_insert
        connection.execute(
            insert(models.inboxes)
            .values(
                org_id=org_id,
                email=email,
                encrypted_token=encrypted,
                daily_limit=30,
            )
            .on_conflict_do_update(
                index_elements=[models.inboxes.c.org_id, models.inboxes.c.email],
                set_={"encrypted_token": encrypted},
            )
        )
    return org_id


def _access_token(org_id: int, inbox_id: int, engine: Engine) -> tuple[str, str]:
    with tenant_transaction(org_id, engine=engine) as connection:
        row = connection.execute(
            select(models.inboxes.c.email, models.inboxes.c.encrypted_token).where(
                models.inboxes.c.id == inbox_id,
                models.inboxes.c.org_id == org_id,
            )
        ).mappings().first()
    if row is None or not row["encrypted_token"]:
        raise HTTPException(
            status_code=409,
            detail="Connect this inbox with Gmail OAuth before live sending.",
        )
    credentials = decrypt_token(row["encrypted_token"])
    expiry = int(credentials.get("expires_at", 0))
    if expiry <= int(datetime.now(timezone.utc).timestamp()) + 60:
        refresh_token = credentials.get("refresh_token")
        if not isinstance(refresh_token, str) or not refresh_token:
            raise HTTPException(status_code=401, detail="Gmail access expired; reconnect this inbox.")
        client_id = os.getenv("GMAIL_CLIENT_ID")
        client_secret = os.getenv("GMAIL_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise HTTPException(status_code=503, detail="Google OAuth environment settings are incomplete.")
        refreshed = _google_post(
            GOOGLE_TOKEN_ENDPOINT,
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        credentials.update(refreshed)
        credentials["refresh_token"] = refresh_token
        credentials["expires_at"] = int(datetime.now(timezone.utc).timestamp()) + int(
            refreshed.get("expires_in", 3600)
        )
        encrypted = encrypt_token(credentials)
        with tenant_transaction(org_id, engine=engine) as connection:
            connection.execute(
                update(models.inboxes)
                .where(
                    models.inboxes.c.id == inbox_id,
                    models.inboxes.c.org_id == org_id,
                )
                .values(encrypted_token=encrypted)
            )
    return str(credentials["access_token"]), str(row["email"])


def _gmail_send(
    access_token: str,
    sender: str,
    recipient: str,
    subject: str,
    body: str,
) -> tuple[str, str]:
    message = EmailMessage()
    message["To"] = recipient
    message["From"] = sender
    message["Subject"] = subject
    message.set_content(body)
    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
    try:
        response = httpx.post(
            GMAIL_SEND_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"},
            json={"raw": encoded},
            timeout=20,
        )
        if response.status_code >= 400:
            raise RuntimeError("Gmail rejected the message.")
        result = response.json()
        message_id = result.get("id")
        thread_id = result.get("threadId")
        if not isinstance(message_id, str) or not isinstance(thread_id, str):
            raise RuntimeError("Gmail did not return message and thread IDs.")
        return message_id, thread_id
    except (httpx.HTTPError, ValueError) as error:
        raise RuntimeError("Gmail send failed.") from error


def google_freebusy(
    org_id: int,
    inbox_id: int,
    starts_at: datetime,
    ends_at: datetime,
    *,
    engine: Engine | None = None,
) -> list[dict[str, str]]:
    database = engine or get_engine()
    access_token, _ = _access_token(org_id, inbox_id, database)
    try:
        response = httpx.post(
            CALENDAR_FREEBUSY_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "timeMin": starts_at.isoformat(),
                "timeMax": ends_at.isoformat(),
                "items": [{"id": "primary"}],
            },
            timeout=15,
        )
        response.raise_for_status()
        busy = response.json()["calendars"]["primary"]["busy"]
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
        raise HTTPException(status_code=502, detail="Google Calendar free/busy lookup failed.") from error
    if not isinstance(busy, list) or any(
        not isinstance(item, dict)
        or not isinstance(item.get("start"), str)
        or not isinstance(item.get("end"), str)
        for item in busy
    ):
        raise HTTPException(status_code=502, detail="Google Calendar returned invalid availability data.")
    return [
        {"start": item["start"], "end": item["end"]}
        for item in busy
    ]


def send_approved_draft(
    org_id: int,
    draft_id: int,
    inbox_id: int,
    recipient: str,
    *,
    engine: Engine | None = None,
    _scheduled_claimed: bool = False,
) -> dict[str, Any]:
    database = engine or get_engine()
    normalized_recipient = recipient.strip().lower()
    send_mode = os.getenv("SEND_MODE", "dry-run").strip().lower()
    if send_mode not in {"dry-run", "live"}:
        raise RuntimeError("SEND_MODE must be dry-run or live.")

    with tenant_transaction(org_id, engine=database) as connection:
        inbox = connection.execute(
            select(
                models.inboxes.c.id,
                models.inboxes.c.email,
                models.inboxes.c.daily_limit,
            ).where(
                models.inboxes.c.id == inbox_id,
                models.inboxes.c.org_id == org_id,
            )
        ).mappings().first()
        if inbox is None:
            raise HTTPException(status_code=404, detail="Inbox not found.")
        if connection.dialect.name == "postgresql":
            connection.execute(
                select(models.inboxes.c.id)
                .where(
                    models.inboxes.c.id == inbox_id,
                    models.inboxes.c.org_id == org_id,
                )
                .with_for_update()
            ).first()

        draft = connection.execute(
            text(
                "SELECT d.id AS draft_id, d.subject, d.body, d.status AS draft_status, "
                "s.id AS sequence_id, s.status AS sequence_status, s.lead_id, "
                "settings.sender_postal_address "
                "FROM email_drafts d JOIN email_sequences s "
                "ON s.id = d.sequence_id AND s.org_id = d.org_id "
                "JOIN org_settings settings ON settings.org_id = d.org_id "
                "WHERE d.id = :draft_id AND d.org_id = :org_id"
            ),
            {"draft_id": draft_id, "org_id": org_id},
        ).mappings().first()
        if draft is None:
            raise HTTPException(status_code=404, detail="Email draft not found.")
        if draft["draft_status"] != "approved" or draft["sequence_status"] != "approved":
            raise HTTPException(status_code=409, detail="Only approved email drafts can be sent.")
        if not draft["sender_postal_address"].strip():
            raise HTTPException(status_code=409, detail="Add the sender postal address in Settings first.")
        suppressed = connection.execute(
            select(models.suppression_list.c.id).where(
                models.suppression_list.c.org_id == org_id,
                models.suppression_list.c.email == normalized_recipient,
            )
        ).first()
        if suppressed is not None:
            raise HTTPException(status_code=409, detail="This address is permanently suppressed.")
        existing = connection.execute(
            select(
                models.outbox.c.id,
                models.outbox.c.status,
                models.outbox.c.scheduled_at,
            ).where(
                models.outbox.c.org_id == org_id,
                models.outbox.c.draft_id == draft_id,
            )
        ).mappings().first()
        if existing is not None and existing["status"] == "scheduled":
            return {"id": existing["id"], "status": "scheduled", "duplicate": True}
        if existing is not None and existing["status"] == "processing" and not _scheduled_claimed:
            return {"id": existing["id"], "status": existing["status"], "duplicate": True}
        if existing is not None and existing["status"] not in {"processing"}:
            return {"id": existing["id"], "status": existing["status"], "duplicate": True}

        now = datetime.now(timezone.utc)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        send_count = connection.execute(
            select(models.outbox.c.id).where(
                models.outbox.c.org_id == org_id,
                models.outbox.c.inbox_id == inbox_id,
                models.outbox.c.sent_at >= today,
                models.outbox.c.status.in_(("dry_run", "pending", "sent")),
            )
        ).all()
        if len(send_count) >= min(int(inbox["daily_limit"]), 30):
            raise HTTPException(status_code=429, detail="This inbox has reached its daily send limit.")

        unsubscribe = create_unsubscribe_token(org_id, normalized_recipient)
        frontend_url = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")
        unsubscribe_url = f"{frontend_url}/unsubscribe?token={unsubscribe}"
        complete_body = (
            f"{draft['body'].rstrip()}\n\n"
            f"{draft['sender_postal_address'].strip()}\n"
            f"To unsubscribe: {unsubscribe_url}"
        )
        if send_mode == "live":
            allowlist = {
                address.strip().lower()
                for address in os.getenv("ALLOWLIST", "").split(",")
                if address.strip()
            }
            if not allowlist:
                raise HTTPException(
                    status_code=409,
                    detail="Live sending is disabled until ALLOWLIST contains your own inbox.",
                )
            if normalized_recipient not in allowlist:
                raise HTTPException(status_code=403, detail="Live mode only sends to your allowlisted addresses.")

        status_value = "pending" if send_mode == "live" else "dry_run"
        if existing is not None:
            outbox_id = int(existing["id"])
            connection.execute(
                update(models.outbox)
                .where(
                    models.outbox.c.id == outbox_id,
                    models.outbox.c.org_id == org_id,
                    models.outbox.c.status == "processing",
                )
                .values(
                    recipient=normalized_recipient,
                    subject=draft["subject"],
                    body=complete_body,
                    status=status_value,
                    scheduled_at=None,
                    locked_at=None,
                    sent_at=now,
                )
            )
        else:
            insert = postgresql_insert if connection.dialect.name == "postgresql" else sqlite_insert
            result = connection.execute(
                insert(models.outbox)
                .values(
                    org_id=org_id,
                    lead_id=draft["lead_id"],
                    draft_id=draft_id,
                    inbox_id=inbox_id,
                    recipient=normalized_recipient,
                    subject=draft["subject"],
                    body=complete_body,
                    status=status_value,
                    sent_at=now,
                )
                .on_conflict_do_nothing(
                    index_elements=[models.outbox.c.org_id, models.outbox.c.draft_id]
                )
                .returning(models.outbox.c.id)
            )
            inserted_id = result.scalar_one_or_none()
            if inserted_id is None:
                existing = connection.execute(
                    select(models.outbox.c.id, models.outbox.c.status).where(
                        models.outbox.c.org_id == org_id,
                        models.outbox.c.draft_id == draft_id,
                    )
                ).mappings().one()
                return {"id": existing["id"], "status": existing["status"], "duplicate": True}
            outbox_id = int(inserted_id)

    if send_mode == "dry-run":
        return {"id": outbox_id, "status": "dry_run", "sent": False}

    try:
        access_token, sender = _access_token(org_id, inbox_id, database)
        message_id, thread_id = _gmail_send(
            access_token,
            sender,
            normalized_recipient,
            str(draft["subject"]),
            complete_body,
        )
    except Exception as error:
        with tenant_transaction(org_id, engine=database) as connection:
            connection.execute(
                update(models.outbox)
                .where(
                    models.outbox.c.id == outbox_id,
                    models.outbox.c.org_id == org_id,
                )
                .values(status="failed")
            )
        if isinstance(error, HTTPException):
            raise
        raise HTTPException(status_code=502, detail="Gmail send failed; the outbox entry is marked failed.") from error

    with tenant_transaction(org_id, engine=database) as connection:
        connection.execute(
            update(models.outbox)
            .where(
                models.outbox.c.id == outbox_id,
                models.outbox.c.org_id == org_id,
            )
            .values(status="sent", message_id=message_id, thread_id=thread_id)
        )
    return {"id": outbox_id, "status": "sent", "sent": True}


def schedule_approved_sequence(
    org_id: int,
    sequence_id: int,
    inbox_id: int,
    recipient: str,
    *,
    engine: Engine | None = None,
) -> list[dict[str, Any]]:
    database = engine or get_engine()
    normalized_recipient = recipient.strip().lower()
    now = datetime.now(timezone.utc)
    with tenant_transaction(org_id, engine=database) as connection:
        sequence = connection.execute(
            select(models.email_sequences.c.id, models.email_sequences.c.lead_id).where(
                models.email_sequences.c.id == sequence_id,
                models.email_sequences.c.org_id == org_id,
                models.email_sequences.c.status == "approved",
            )
        ).mappings().first()
        if sequence is None:
            raise HTTPException(status_code=404, detail="Approved email sequence not found.")
        inbox = connection.execute(
            select(models.inboxes.c.id).where(
                models.inboxes.c.id == inbox_id,
                models.inboxes.c.org_id == org_id,
            )
        ).first()
        if inbox is None:
            raise HTTPException(status_code=404, detail="Inbox not found.")
        settings = connection.execute(
            select(
                models.org_settings.c.sender_postal_address,
                models.org_settings.c.calendar_link,
            ).where(models.org_settings.c.org_id == org_id)
        ).mappings().first()
        if settings is None or not settings["sender_postal_address"].strip():
            raise HTTPException(status_code=409, detail="Add the sender postal address in Settings first.")
        suppressed = connection.execute(
            select(models.suppression_list.c.id).where(
                models.suppression_list.c.org_id == org_id,
                models.suppression_list.c.email == normalized_recipient,
            )
        ).first()
        if suppressed is not None:
            raise HTTPException(status_code=409, detail="This address is permanently suppressed.")
        drafts = connection.execute(
            select(
                models.email_drafts.c.id,
                models.email_drafts.c.subject,
                models.email_drafts.c.body,
                models.email_drafts.c.send_delay_days,
                models.email_drafts.c.status,
            ).where(
                models.email_drafts.c.org_id == org_id,
                models.email_drafts.c.sequence_id == sequence_id,
            ).order_by(models.email_drafts.c.position)
        ).mappings().all()
        scheduled: list[dict[str, Any]] = []
        insert = postgresql_insert if connection.dialect.name == "postgresql" else sqlite_insert
        for draft in drafts:
            if draft["status"] != "approved":
                raise HTTPException(status_code=409, detail="Every email in the sequence must be approved.")
            token = create_unsubscribe_token(org_id, normalized_recipient)
            frontend_url = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")
            body = (
                f"{draft['body'].rstrip()}\n\n"
                f"{settings['sender_postal_address'].strip()}\n"
                f"To unsubscribe: {frontend_url}/unsubscribe?token={token}"
            )
            delivery_time = now + timedelta(days=int(draft["send_delay_days"]))
            inserted_id = connection.execute(
                insert(models.outbox)
                .values(
                    org_id=org_id,
                    lead_id=sequence["lead_id"],
                    draft_id=draft["id"],
                    inbox_id=inbox_id,
                    recipient=normalized_recipient,
                    subject=draft["subject"],
                    body=body,
                    status="scheduled",
                    scheduled_at=delivery_time,
                )
                .on_conflict_do_nothing(
                    index_elements=[models.outbox.c.org_id, models.outbox.c.draft_id]
                )
                .returning(models.outbox.c.id)
            ).scalar_one_or_none()
            if inserted_id is not None:
                scheduled.append({"id": int(inserted_id), "scheduled_at": delivery_time.isoformat()})
            else:
                existing = connection.execute(
                    select(models.outbox.c.id, models.outbox.c.scheduled_at).where(
                        models.outbox.c.org_id == org_id,
                        models.outbox.c.draft_id == draft["id"],
                    )
                ).mappings().one()
                scheduled.append(
                    {
                        "id": int(existing["id"]),
                        "scheduled_at": existing["scheduled_at"].isoformat()
                        if existing["scheduled_at"]
                        else None,
                    }
                )
    return scheduled


def add_suppression(
    org_id: int,
    email: str,
    reason: str,
    *,
    engine: Engine | None = None,
) -> None:
    database = engine or get_engine()
    normalized_email = email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized_email):
        raise HTTPException(status_code=422, detail="A valid email address is required.")
    with tenant_transaction(org_id, engine=database) as connection:
        insert = postgresql_insert if connection.dialect.name == "postgresql" else sqlite_insert
        connection.execute(
            insert(models.suppression_list)
            .values(org_id=org_id, email=normalized_email, reason=reason[:40])
            .on_conflict_do_nothing(
                index_elements=[
                    models.suppression_list.c.org_id,
                    models.suppression_list.c.email,
                ]
            )
        )
