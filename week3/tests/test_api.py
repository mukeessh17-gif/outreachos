# Week 3 Day 5: API tests using FastAPI TestClient
# OutreachOS - AI sales outreach tool
# Run with: pytest -v week3/tests/test_api.py
# These tests use a MOCKED database layer - never your real Supabase data.

from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import pytest

from app.main import app

client = TestClient(app)


# ------------------------------------------------------------
# Fixture: mock the database engine
# ------------------------------------------------------------
@pytest.fixture
def mock_engine():
    """Replace week3.app.main.engine with a MagicMock for all tests."""
    with patch("app.main.engine") as mock:
        mock_connect = MagicMock()
        mock.connect.return_value.__enter__.return_value = mock_connect
        mock_result = MagicMock()
        # Make result iterable (code does "for row in result")
        mock_result.__iter__.return_value = iter([])
        mock_connect.execute.return_value = mock_result
        yield mock_connect


# ------------------------------------------------------------
# /health
# ------------------------------------------------------------
def test_health(mock_engine):
    response = client.get("/health")
    assert response.status_code == 200


# ------------------------------------------------------------
# POST /leads valid
# ------------------------------------------------------------
def test_post_leads_valid(mock_engine):
    mock_row = MagicMock()
    mock_row._mapping = {
        "id": 2,
        "name": "New Co",
        "city": "Coimbatore",
        "employees": 10,
        "has_website": True,
        "created_at": "2024-01-01T00:00:00",
    }
    mock_result = MagicMock()
    mock_result.fetchone.return_value = mock_row
    mock_engine.execute.return_value = mock_result

    response = client.post(
        "/leads",
        json={"name": "New Co", "city": "Coimbatore", "employees": 10, "has_website": True},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Co"


# ------------------------------------------------------------
# POST /leads invalid (422)
# ------------------------------------------------------------
def test_post_leads_invalid(mock_engine):
    # employees = -5 violates ge=0, empty name violates min_length=2
    response = client.post(
        "/leads",
        json={"name": "", "city": "X", "employees": -5, "has_website": True},
    )
    assert response.status_code == 422


# ------------------------------------------------------------
# POST /leads duplicate (409)
# ------------------------------------------------------------
def test_post_leads_duplicate(mock_engine):
    # ON CONFLICT returns no row -> mock fetchone returns None
    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    mock_engine.execute.return_value = mock_result

    response = client.post(
        "/leads",
        json={"name": "Existing Co", "city": "Coimbatore", "employees": 10, "has_website": True},
    )
    assert response.status_code == 409


# ------------------------------------------------------------
# GET /leads/{lead_id} missing (404)
# ------------------------------------------------------------
def test_get_lead_not_found(mock_engine):
    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    mock_engine.execute.return_value = mock_result

    response = client.get("/leads/99999")
    assert response.status_code == 404


# ------------------------------------------------------------
# DELETE /leads/{lead_id}
# ------------------------------------------------------------
def test_get_leads(mock_engine):
    mock_row = MagicMock()
    mock_row._mapping = {
        "id": 1,
        "name": "Kovai Textiles",
        "city": "Coimbatore",
        "employees": 15,
        "has_website": True,
        "created_at": "2024-01-01T00:00:00",
    }
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [mock_row]
    mock_engine.execute.return_value = mock_result

    response = client.get("/leads")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Kovai Textiles"


# ------------------------------------------------------------
# GET /leads/good
# ------------------------------------------------------------
def test_get_leads_good(mock_engine):
    mock_row = MagicMock()
    mock_row._mapping = {
        "id": 1,
        "name": "Good Co",
        "city": "Coimbatore",
        "employees": 10,
        "has_website": True,
        "created_at": "2024-01-01T00:00:00",
    }
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [mock_row]
    mock_engine.execute.return_value = mock_result

    response = client.get("/leads/good")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Good Co"


# ------------------------------------------------------------
# PATCH /leads/{lead_id}
# ------------------------------------------------------------
def test_patch_lead(mock_engine):
    mock_row = MagicMock()
    mock_row._mapping = {
        "id": 1,
        "name": "Updated Co",
        "city": "Coimbatore",
        "employees": 15,
        "has_website": False,
        "created_at": "2024-01-01T00:00:00",
    }
    mock_result = MagicMock()
    mock_result.fetchone.return_value = mock_row
    mock_engine.execute.return_value = mock_result

    response = client.patch("/leads/1?employees=15&has_website=false")
    assert response.status_code == 200


# ------------------------------------------------------------
# DELETE /leads/{lead_id}
# ------------------------------------------------------------
def test_delete_lead(mock_engine):
    mock_row = MagicMock()
    mock_result = MagicMock()
    mock_result.fetchone.return_value = mock_row
    mock_engine.execute.return_value = mock_result

    response = client.delete("/leads/1")
    assert response.status_code == 204