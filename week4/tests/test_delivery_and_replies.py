import hashlib
import hmac
import json
import base64
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool
from cryptography.fernet import Fernet

from week4 import models
from week4.billing import handle_stripe_event, verify_stripe_signature
from week4.email_delivery import (
    decrypt_token,
    encrypt_token,
    schedule_approved_sequence,
    send_approved_draft,
)
from week4.replies import classify_and_save_reply, evaluate_fake_replies
from week4.scheduler import process_due_sends
from week4 import reply_sync
from week4.schemas import ReplyClassification


@pytest.fixture
def test_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(models.orgs.insert().values(id=1, name="Test Org"))
        connection.execute(models.org_settings.insert().values(
            org_id=1,
            sender_postal_address="123 Test Street",
        ))
        connection.execute(models.companies.insert().values(org_id=1, name="Fake Company"))
        connection.execute(models.inboxes.insert().values(
            org_id=1,
            email="owner@example.com",
            encrypted_token="",
        ))
        sequence_id = connection.execute(models.email_sequences.insert().values(
            org_id=1,
            lead_id=1,
            status="approved",
        ).returning(models.email_sequences.c.id)).scalar_one()
        connection.execute(models.email_drafts.insert().values(
            org_id=1,
            sequence_id=sequence_id,
            position=1,
            subject="A fictional workflow question",
            body="Would a simpler workflow be useful?",
            status="approved",
        ))
    yield engine
    engine.dispose()


def test_dry_run_outbox_is_idempotent_and_includes_compliance_text(
    test_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SEND_MODE", "dry-run")
    monkeypatch.setenv("JWT_SECRET", "test-secret-with-more-than-thirty-two-characters")

    result = send_approved_draft(
        1,
        1,
        1,
        "prospect@example.com",
        engine=test_engine,
    )
    duplicate = send_approved_draft(
        1,
        1,
        1,
        "prospect@example.com",
        engine=test_engine,
    )
    assert result["status"] == "dry_run"
    assert result["sent"] is False
    assert duplicate["duplicate"] is True
    with test_engine.begin() as connection:
        rows = connection.execute(select(models.outbox)).mappings().all()
    assert len(rows) == 1
    assert "123 Test Street" in rows[0]["body"]
    assert "/unsubscribe?token=" in rows[0]["body"]


def test_oauth_credentials_are_encrypted_at_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode("ascii"))
    credentials = {"access_token": "fake-oauth-token", "refresh_token": "fake-refresh"}
    ciphertext = encrypt_token(credentials)
    assert "fake-oauth-token" not in ciphertext
    assert decrypt_token(ciphertext) == credentials


def test_suppressed_address_cannot_be_added_to_outbox(
    test_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SEND_MODE", "dry-run")
    with test_engine.begin() as connection:
        connection.execute(models.suppression_list.insert().values(
            org_id=1,
            email="prospect@example.com",
            reason="unsubscribe",
        ))
    with pytest.raises(HTTPException) as error:
        send_approved_draft(
            1,
            1,
            1,
            "prospect@example.com",
            engine=test_engine,
        )
    assert error.value.status_code == 409


def test_live_mode_rejects_non_allowlisted_recipient(
    test_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SEND_MODE", "live")
    monkeypatch.setenv("ALLOWLIST", "owner@example.com")
    monkeypatch.setenv("JWT_SECRET", "test-secret-with-more-than-thirty-two-characters")
    with pytest.raises(HTTPException) as error:
        send_approved_draft(
            1,
            1,
            1,
            "prospect@example.com",
            engine=test_engine,
        )
    assert error.value.status_code == 403
    with test_engine.begin() as connection:
        assert connection.execute(select(models.outbox.c.id)).first() is None


def test_scheduled_sequence_runs_in_dry_run_mode(
    test_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SEND_MODE", "dry-run")
    monkeypatch.setenv("JWT_SECRET", "test-secret-with-more-than-thirty-two-characters")
    scheduled = schedule_approved_sequence(
        1,
        1,
        1,
        "prospect@example.com",
        engine=test_engine,
    )
    assert len(scheduled) == 1
    result = process_due_sends(
        1,
        engine=test_engine,
        now=datetime.now(timezone.utc),
    )
    assert result == {"processed": 1, "sent": 0, "dry_run": 1, "failed": 0}
    with test_engine.begin() as connection:
        row = connection.execute(select(models.outbox)).mappings().one()
    assert row["status"] == "dry_run"
    assert row["sent_at"] is not None


def test_reply_unsubscribe_is_suppressed_and_message_id_is_idempotent(
    test_engine,
) -> None:
    calls = 0

    def fake_classifier(*args, **kwargs):
        nonlocal calls
        calls += 1
        return ReplyClassification(
            category="unsubscribe",
            confidence=0.99,
            draft_response=None,
        ), 10, 4

    result = classify_and_save_reply(
        1,
        1,
        "prospect@example.com",
        "Please unsubscribe me.",
        engine=test_engine,
        classifier=fake_classifier,
        source_message_id="gmail-message-1",
        thread_id="gmail-thread-1",
    )
    duplicate = classify_and_save_reply(
        1,
        1,
        "prospect@example.com",
        "Please unsubscribe me.",
        engine=test_engine,
        classifier=fake_classifier,
        source_message_id="gmail-message-1",
        thread_id="gmail-thread-1",
    )
    assert result["status"] == "handled"
    assert duplicate["duplicate"] is True
    assert calls == 1
    with test_engine.begin() as connection:
        suppressed = connection.execute(select(models.suppression_list)).mappings().all()
        replies = connection.execute(select(models.replies)).mappings().all()
    assert suppressed[0]["email"] == "prospect@example.com"
    assert replies[0]["source_message_id"] == "gmail-message-1"


def test_synthetic_reply_eval_has_one_hundred_cases_and_over_ninety_percent_accuracy():
    report = evaluate_fake_replies()
    assert report["cases"] == 100
    assert report["accuracy"] >= 0.9


def test_gmail_sync_only_processes_known_sent_threads_once(
    test_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with test_engine.begin() as connection:
        connection.execute(models.outbox.insert().values(
            org_id=1,
            lead_id=1,
            draft_id=1,
            inbox_id=1,
            recipient="prospect@example.com",
            subject="Hello",
            body="Hello",
            status="sent",
            thread_id="gmail-thread-1",
        ))
    body = base64.urlsafe_b64encode(b"Please send more details.").decode().rstrip("=")

    def fake_get(url, token, *, params=None):
        if url.endswith("/messages"):
            return {"messages": [{"id": "message-1", "threadId": "gmail-thread-1"}]}
        return {
            "payload": {
                "headers": [{"name": "From", "value": "Prospect <prospect@example.com>"}],
                "mimeType": "text/plain",
                "body": {"data": body},
            }
        }

    monkeypatch.setattr(reply_sync, "_access_token", lambda *args: ("token", "owner@example.com"))
    monkeypatch.setattr(reply_sync, "_gmail_get", fake_get)

    def fake_classifier(*args, **kwargs):
        return ReplyClassification(
            category="interested",
            confidence=0.95,
            draft_response="I can share more.",
        ), 12, 6

    first = reply_sync.sync_gmail_replies(
        1,
        1,
        engine=test_engine,
        classifier=fake_classifier,
    )
    second = reply_sync.sync_gmail_replies(
        1,
        1,
        engine=test_engine,
        classifier=fake_classifier,
    )
    assert first == {"processed": 1, "ignored": 0, "bounced": 0}
    assert second == {"processed": 0, "ignored": 1, "bounced": 0}


def test_gmail_bounce_sync_permanently_suppresses_recipient(
    test_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with test_engine.begin() as connection:
        connection.execute(models.outbox.insert().values(
            org_id=1,
            lead_id=1,
            draft_id=1,
            inbox_id=1,
            recipient="prospect@example.com",
            subject="Hello",
            body="Hello",
            status="sent",
            thread_id="gmail-thread-bounce",
        ))
    body = base64.urlsafe_b64encode(
        b"Delivery Status Notification: delivery failed"
    ).decode().rstrip("=")

    def fake_get(url, token, *, params=None):
        if url.endswith("/messages"):
            return {"messages": [{"id": "bounce-1", "threadId": "gmail-thread-bounce"}]}
        return {
            "payload": {
                "headers": [{"name": "From", "value": "Mail Delivery Subsystem <mailer-daemon@gmail.com>"}],
                "mimeType": "text/plain",
                "body": {"data": body},
            }
        }

    monkeypatch.setattr(reply_sync, "_access_token", lambda *args: ("token", "owner@example.com"))
    monkeypatch.setattr(reply_sync, "_gmail_get", fake_get)
    result = reply_sync.sync_gmail_replies(1, 1, engine=test_engine)
    with test_engine.begin() as connection:
        suppressed = connection.execute(select(models.suppression_list.c.email)).scalar_one()
    assert result == {"processed": 0, "ignored": 0, "bounced": 1}
    assert suppressed == "prospect@example.com"


def test_stripe_webhook_signature_and_event_idempotency(
    test_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "whsec_test_secret"
    timestamp = int(datetime.now(timezone.utc).timestamp())
    payload = json.dumps({
        "id": "evt_test_1",
        "type": "checkout.session.completed",
        "livemode": False,
        "data": {"object": {
            "id": "cs_test_1",
            "customer": "cus_test_1",
            "subscription": "sub_test_1",
            "status": "active",
            "metadata": {"org_id": "1", "plan": "starter"},
        }},
    }).encode()
    digest = hmac.new(
        secret.encode(),
        str(timestamp).encode() + b"." + payload,
        hashlib.sha256,
    ).hexdigest()
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", secret)
    verify_stripe_signature(payload, f"t={timestamp},v1={digest}", now=timestamp)
    event = json.loads(payload)
    assert handle_stripe_event(event, engine=test_engine) is True
    assert handle_stripe_event(event, engine=test_engine) is False
    with test_engine.begin() as connection:
        plan = connection.execute(select(models.orgs.c.plan).where(models.orgs.c.id == 1)).scalar_one()
    assert plan == "starter"
