# Week 3 Day 5: tests for retry_with_backoff
# Run with: pytest -v week3/tests/test_retry.py

import pytest
from app.retry import retry_with_backoff


class CustomError(Exception):
    """A custom exception for testing retries."""


@pytest.mark.asyncio
async def test_retry_succeeds_after_failures():
    """A function that fails twice then succeeds should return the success value."""
    call_count = 0

    @retry_with_backoff(max_attempts=3, base_delay=0.01, exceptions=(CustomError,))
    async def flaky():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise CustomError("not yet")
        return "success"

    result = await flaky()
    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_gives_up_after_max_attempts():
    """A function that always fails should raise after max_attempts."""
    call_count = 0

    @retry_with_backoff(max_attempts=2, base_delay=0.01, exceptions=(CustomError,))
    async def always_fails():
        nonlocal call_count
        call_count += 1
        raise CustomError("always fails")

    with pytest.raises(CustomError):
        await always_fails()
    assert call_count == 2


@pytest.mark.asyncio
async def test_retry_does_not_retry_non_matching_exception():
    """An exception not in the exceptions tuple should not be retried."""
    call_count = 0

    @retry_with_backoff(max_attempts=3, base_delay=0.01, exceptions=(CustomError,))
    async def wrong_error():
        nonlocal call_count
        call_count += 1
        raise ValueError("wrong type")

    with pytest.raises(ValueError):
        await wrong_error()
    assert call_count == 1