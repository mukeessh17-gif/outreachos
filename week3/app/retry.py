# Week 3 Day 5: retry with backoff
# OutreachOS - AI sales outreach tool
# Retries a function on specific exceptions with increasing delays and jitter.

import asyncio
import logging
import random
import time
from functools import wraps
from typing import Callable, TypeVar, Tuple, Type

logger = logging.getLogger("outreachos.retry")

T = TypeVar("T")


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """Decorator that retries an async function with exponential backoff.

    - Waits base_delay * 2^(attempt-1) seconds plus a little random jitter.
    - Logs each retry attempt.
    - Gives up after max_attempts and re-raises the last exception.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_error: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as error:
                    last_error = error
                    if attempt < max_attempts:
                        delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
                        logger.warning(
                            "Attempt %d/%d failed: %s. Retrying in %.1fs...",
                            attempt,
                            max_attempts,
                            error,
                            delay,
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "All %d attempts failed. Last error: %s",
                            max_attempts,
                            error,
                        )
            assert last_error is not None
            raise last_error

        return wrapper

    return decorator