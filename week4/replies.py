"""Validated reply classification and a deterministic synthetic evaluation set."""

import re
from collections.abc import Callable
from typing import Any

from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Engine

from week1.llm import request_validated
from week4 import models
from week4.db import tenant_transaction
from week4.email_delivery import add_suppression
from week4.schemas import ReplyClassification
from week4.token_budget import request_budgeted


_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "unsubscribe",
        re.compile(r"\b(unsubscribe|opt out|remove me|stop emailing|do not email)\b", re.IGNORECASE),
    ),
    (
        "out-of-office",
        re.compile(r"\b(out of office|away from (?:my )?email|on leave|return on)\b", re.IGNORECASE),
    ),
    (
        "objection",
        re.compile(
            r"\b(not interested|no budget|do not have budget|already use|not a fit|not now)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "interested",
        re.compile(
            r"\b(interested|let'?s talk|schedule|book a (?:call|meeting)|send more|share more)\b",
            re.IGNORECASE,
        ),
    ),
)


def classify_reply_text(body: str) -> str:
    for category, pattern in _RULES:
        if pattern.search(body):
            return category
    return "other"


def classify_and_save_reply(
    org_id: int,
    lead_id: int,
    sender_email: str,
    body: str,
    *,
    engine: Engine,
    classifier: Callable[..., Any] = request_validated,
    source_message_id: str | None = None,
    thread_id: str | None = None,
) -> dict[str, Any]:
    with tenant_transaction(org_id, engine=engine) as connection:
        lead = connection.execute(
            models.companies.select()
            .with_only_columns(models.companies.c.id)
            .where(
                models.companies.c.id == lead_id,
                models.companies.c.org_id == org_id,
            )
        ).first()
        if source_message_id is not None:
            existing = connection.execute(
                models.replies.select()
                .with_only_columns(models.replies.c.id)
                .where(
                    models.replies.c.org_id == org_id,
                    models.replies.c.source_message_id == source_message_id,
                )
            ).first()
            if existing is not None:
                return {"id": int(existing[0]), "duplicate": True}
    if lead is None:
        raise ValueError("Lead not found.")

    prompt = (
        "Classify this email reply. Return only the validated JSON schema. "
        "Categories: interested, objection, unsubscribe, out-of-office, other. "
        "Draft a brief response only when appropriate; do not send it.\n"
        f"Reply text:\n{body}"
    )
    classification, _, _ = request_budgeted(
        prompt,
        ReplyClassification,
        org_id=org_id,
        lead_id=lead_id,
        purpose="reply_classification",
        engine=engine,
        generator=classifier,
    )
    status = "handled" if classification.category == "unsubscribe" else "draft"
    with tenant_transaction(org_id, engine=engine) as connection:
        values = {
            "org_id": org_id,
            "lead_id": lead_id,
            "sender_email": sender_email.strip().lower(),
            "source_message_id": source_message_id,
            "thread_id": thread_id,
            "body": body,
            "category": classification.category,
            "draft_response": classification.draft_response,
            "status": status,
        }
        insert = models.replies.insert()
        if source_message_id is not None:
            dialect_insert = (
                postgresql_insert
                if connection.dialect.name == "postgresql"
                else sqlite_insert
            )
            insert = (
                dialect_insert(models.replies).values(**values)
                .on_conflict_do_nothing(
                    index_elements=[models.replies.c.org_id, models.replies.c.source_message_id]
                )
            )
        else:
            insert = insert.values(**values)
        reply_id = connection.execute(
            insert.returning(models.replies.c.id)
        ).scalar_one_or_none()
        if reply_id is None:
            return {"duplicate": True}
    if classification.category == "unsubscribe":
        add_suppression(org_id, sender_email, "unsubscribe", engine=engine)
    return {
        "id": int(reply_id),
        "category": classification.category,
        "confidence": classification.confidence,
        "draft_response": classification.draft_response,
        "status": status,
    }


def build_fake_replies() -> list[dict[str, str]]:
    examples = {
        "interested": [
            "I am interested. Send more information.",
            "Let's schedule a call next week.",
            "Can we book a quick meeting?",
            "Please share more about the workflow.",
            "This sounds useful; let's talk.",
        ],
        "objection": [
            "We already use another provider.",
            "Not interested at this time.",
            "We do not have budget this quarter.",
            "This is not a fit for our team.",
            "Please reach out next year; not now.",
        ],
        "unsubscribe": [
            "Please unsubscribe me.",
            "Remove me from your list.",
            "Stop emailing this address.",
            "Do not email me again.",
            "I want to opt out.",
        ],
        "out-of-office": [
            "I am out of office until Monday.",
            "Away from email for the rest of the week.",
            "I am on leave; return on Friday.",
            "This is an automatic out of office reply.",
            "I will be away from my email.",
        ],
        "other": [
            "Thanks for the note.",
            "I will take a look.",
            "Please contact the main office.",
            "We received your message.",
            "Could you clarify the company name?",
        ],
    }
    return [
        {"body": message, "category": category}
        for category, messages in examples.items()
        for message in messages * 4
    ]


def evaluate_fake_replies() -> dict[str, Any]:
    labels = ("interested", "objection", "unsubscribe", "out-of-office", "other")
    confusion: dict[str, dict[str, int]] = {
        label: {prediction: 0 for prediction in labels} for label in labels
    }
    examples = build_fake_replies()
    for example in examples:
        prediction = classify_reply_text(example["body"])
        confusion[example["category"]][prediction] += 1
    correct = sum(confusion[label][label] for label in labels)
    return {
        "cases": len(examples),
        "accuracy": correct / len(examples),
        "confusion": confusion,
    }
