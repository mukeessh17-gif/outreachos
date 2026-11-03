"""Poll a connected Gmail inbox for replies to known sent threads."""

import base64
import binascii
from email.utils import parseaddr
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.engine import Engine

from week4 import models
from week4.db import tenant_transaction
from week4.email_delivery import _access_token, add_suppression
from week4.replies import classify_and_save_reply

GMAIL_MESSAGES_ENDPOINT = "https://gmail.googleapis.com/gmail/v1/users/me/messages"


def _decode_message_part(part: dict[str, Any]) -> str:
    mime_type = part.get("mimeType")
    if mime_type == "text/plain":
        body_part = part.get("body", {})
        data = body_part.get("data") if isinstance(body_part, dict) else None
        if isinstance(data, str):
            data = data[:40_000]
            data = data[: len(data) - len(data) % 4]
            padding = "=" * (-len(data) % 4)
            try:
                decoded = base64.urlsafe_b64decode(data + padding)
            except (binascii.Error, ValueError):
                return ""
            return decoded.decode("utf-8", errors="replace")
    children = part.get("parts", [])
    if isinstance(children, list):
        for child in children:
            if isinstance(child, dict):
                result = _decode_message_part(child)
                if result:
                    return result
    return ""


def _gmail_get(url: str, token: str, *, params: dict[str, str] | None = None) -> dict[str, Any]:
    try:
        response = httpx.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise HTTPException(status_code=502, detail="Gmail reply synchronization failed.") from error
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="Gmail returned an invalid response.")
    return data


def sync_gmail_replies(
    org_id: int,
    inbox_id: int,
    *,
    engine: Engine,
    classifier: Any = None,
) -> dict[str, int]:
    access_token, _ = _access_token(org_id, inbox_id, engine)
    listed = _gmail_get(
        GMAIL_MESSAGES_ENDPOINT,
        access_token,
        params={"q": "in:inbox newer_than:30d", "maxResults": "100"},
    )
    messages = listed.get("messages", [])
    if not isinstance(messages, list):
        raise HTTPException(status_code=502, detail="Gmail returned an invalid message list.")

    processed = 0
    ignored = 0
    bounced = 0
    for item in messages:
        if not isinstance(item, dict):
            ignored += 1
            continue
        message_id = item.get("id")
        thread_id = item.get("threadId")
        if not isinstance(message_id, str) or not isinstance(thread_id, str):
            ignored += 1
            continue
        with tenant_transaction(org_id, engine=engine) as connection:
            duplicate = connection.execute(
                select(models.replies.c.id).where(
                    models.replies.c.org_id == org_id,
                    models.replies.c.source_message_id == message_id,
                )
            ).first()
            sent_message = connection.execute(
                text(
                    "SELECT o.lead_id, o.recipient FROM outbox o "
                    "WHERE o.org_id = :org_id AND o.inbox_id = :inbox_id "
                    "AND o.thread_id = :thread_id AND o.status = 'sent' "
                    "ORDER BY o.created_at DESC LIMIT 1"
                ),
                {"org_id": org_id, "inbox_id": inbox_id, "thread_id": thread_id},
            ).mappings().first()
        if duplicate is not None:
            ignored += 1
            continue
        if sent_message is None:
            ignored += 1
            continue
        message = _gmail_get(
            f"{GMAIL_MESSAGES_ENDPOINT}/{quote(message_id, safe='')}",
            access_token,
            params={"format": "full"},
        )
        payload = message.get("payload", {})
        headers = payload.get("headers", []) if isinstance(payload, dict) else []
        if not isinstance(headers, list):
            headers = []
        from_header = next(
            (
                header.get("value", "")
                for header in headers
                if isinstance(header, dict)
                and isinstance(header.get("name"), str)
                and header["name"].casefold() == "from"
            ),
            "",
        )
        sender = parseaddr(from_header if isinstance(from_header, str) else "")[1].strip().lower()
        body = _decode_message_part(payload) if isinstance(payload, dict) else ""
        if not body.strip():
            ignored += 1
            continue
        is_bounce = (
            sender.startswith(("mailer-daemon@", "postmaster@"))
            and any(
                marker in body.casefold()
                for marker in (
                    "delivery status notification",
                    "delivery failed",
                    "undelivered mail",
                    "could not be delivered",
                )
            )
        )
        if is_bounce:
            add_suppression(
                org_id,
                sent_message["recipient"],
                "bounce",
                engine=engine,
            )
            bounced += 1
            continue
        if not sender or sender != sent_message["recipient"].strip().lower():
            ignored += 1
            continue
        options: dict[str, Any] = {}
        if classifier is not None:
            options["classifier"] = classifier
        result = classify_and_save_reply(
            org_id,
            sent_message["lead_id"],
            sender,
            body[:10_000],
            engine=engine,
            source_message_id=message_id,
            thread_id=thread_id,
            **options,
        )
        if result.get("duplicate"):
            ignored += 1
        else:
            processed += 1
    return {"processed": processed, "ignored": ignored, "bounced": bounced}
