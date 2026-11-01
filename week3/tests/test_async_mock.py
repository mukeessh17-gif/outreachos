# Week 3 Day 2: test for an async function with mocked HTTP
# Run with: pytest -v week3/tests/test_async_mock.py
# No real network calls - httpx is mocked.

from unittest.mock import AsyncMock, MagicMock, patch
import pytest


@pytest.mark.asyncio
async def test_fetch_one_success_with_mock():
    """An async fetch function should return True when the mocked response is OK."""
    import httpx

    async def fetch_one(client, url):
        response = await client.get(url, timeout=10.0)
        response.raise_for_status()
        return True

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    result = await fetch_one(mock_client, "https://example.com/1")
    assert result is True


@pytest.mark.asyncio
async def test_fetch_one_failure_with_mock():
    """An async fetch function should return False when the mocked response raises."""
    import httpx

    async def fetch_one(client, url):
        try:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            return True
        except httpx.HTTPError:
            return False

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(side_effect=httpx.HTTPError("boom"))

    result = await fetch_one(mock_client, "https://example.com/1")
    assert result is False