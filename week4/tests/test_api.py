from collections.abc import Iterator

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from week4 import models
from week4 import main as api
from week4.auth import get_current_org
from week4.email_delivery import create_unsubscribe_token


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.metadata.create_all(test_engine)
    with test_engine.begin() as connection:
        connection.execute(models.orgs.insert(), [{"id": 1, "name": "Org One"}, {"id": 2, "name": "Org Two"}])
        connection.execute(models.org_settings.insert(), [{"org_id": 1}, {"org_id": 2}])
    monkeypatch.setattr(api, "engine", test_engine)

    def test_org(request: Request) -> int:
        return int(request.headers.get("x-test-org", "1"))

    api.app.dependency_overrides[get_current_org] = test_org
    with TestClient(api.app) as test_client:
        yield test_client
    api.app.dependency_overrides.clear()
    test_engine.dispose()


def test_health_is_public(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_security_headers_and_localhost_cors(client: TestClient) -> None:
    response = client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"

    allowed = client.options(
        "/leads",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"

    blocked = client.options(
        "/leads",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in blocked.headers


def test_lead_routes_require_authentication() -> None:
    with TestClient(api.app) as unauthenticated:
        assert unauthenticated.get("/leads").status_code == 401


def test_orgs_cannot_read_edit_or_delete_each_others_leads(client: TestClient) -> None:
    created = client.post(
        "/leads",
        json={"name": "Org One Lead", "employees": 9, "has_website": True},
        headers={"x-test-org": "1"},
    )
    assert created.status_code == 201
    lead_id = created.json()["id"]

    assert client.get(f"/leads/{lead_id}", headers={"x-test-org": "2"}).status_code == 404
    assert client.patch(
        f"/leads/{lead_id}",
        json={"name": "Stolen Lead"},
        headers={"x-test-org": "2"},
    ).status_code == 404
    assert client.delete(
        f"/leads/{lead_id}",
        headers={"x-test-org": "2"},
    ).status_code == 404
    assert client.get("/leads", headers={"x-test-org": "2"}).json() == []
    assert client.get(f"/leads/{lead_id}", headers={"x-test-org": "1"}).status_code == 200


def test_csv_preview_reports_invalid_rows_without_importing(client: TestClient) -> None:
    response = client.post(
        "/leads/import/preview",
        content="name,city,employees,website\nFake Co,Coimbatore,10,https://example.com\nBad Co,Nowhere,not-a-number,\n",
        headers={"content-type": "text/csv"},
    )
    assert response.status_code == 200
    assert response.json()["accepted_count"] == 1
    assert response.json()["rejected"][0]["row"] == 3
    assert client.get("/leads").json() == []


def test_settings_are_scoped_by_org(client: TestClient) -> None:
    updated = client.put(
        "/settings",
        json={"tone": "friendly", "banned_phrases": ["guaranteed results"]},
        headers={"x-test-org": "1"},
    )
    assert updated.status_code == 200
    assert client.get("/settings", headers={"x-test-org": "2"}).json()["tone"] == "professional"


def test_contacts_are_scoped_to_their_organization(client: TestClient) -> None:
    lead = client.post(
        "/leads",
        json={"name": "Contact Test Company", "employees": 10},
        headers={"x-test-org": "1"},
    ).json()
    created = client.post(
        f"/leads/{lead['id']}/contacts",
        json={"full_name": "Fake Contact", "email": "fake@example.com"},
        headers={"x-test-org": "1"},
    )
    assert created.status_code == 201
    assert len(client.get(f"/leads/{lead['id']}/contacts", headers={"x-test-org": "1"}).json()) == 1
    assert client.get(f"/leads/{lead['id']}/contacts", headers={"x-test-org": "2"}).json() == []
    assert client.post(
        f"/leads/{lead['id']}/contacts",
        json={"full_name": "Cross Org", "email": "other@example.com"},
        headers={"x-test-org": "2"},
    ).status_code == 404


def test_unsubscribe_endpoint_is_public_and_persists_suppression(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret-with-more-than-thirty-two-characters")
    token = create_unsubscribe_token(1, "prospect@example.com")
    response = client.post(f"/unsubscribe?token={token}")
    assert response.status_code == 200
    with api.engine.begin() as connection:
        rows = connection.execute(models.suppression_list.select()).mappings().all()
    assert rows[0]["email"] == "prospect@example.com"


def test_pipeline_stage_changes_are_recorded(client: TestClient) -> None:
    lead = client.post(
        "/leads",
        json={"name": "Pipeline Test Company", "employees": 10},
    ).json()
    response = client.patch(
        f"/leads/{lead['id']}",
        json={"pipeline_stage": "contacted"},
    )
    assert response.status_code == 200
    with api.engine.begin() as connection:
        event = connection.execute(models.pipeline_events.select()).mappings().one()
    assert event["stage"] == "contacted"
