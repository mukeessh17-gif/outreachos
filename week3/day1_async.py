# Week 3 Day 1: async / await
# OutreachOS - AI sales outreach tool
# Run this file from inside the week3/ folder.

# ==================================================================
# 1. Plain-English explanation (restaurant analogy, 6 lines)
# ==================================================================
# Imagine one waiter in a restaurant with many tables.
# Without async: the waiter takes an order at table 1, stands there
# waiting for the food to cook, then delivers it. Only then does he
# go to table 2. Every table waits for the one before it.
# With async: the waiter takes an order at table 1, sends it to the
# kitchen, and immediately goes to table 2 while table 1's food cooks.
# When the food is ready, he comes back to deliver it. This matters for
# APIs because your program can start many requests and keep working
# while waiting for slow responses, instead of freezing on each one.

import asyncio
import time
import httpx

# The URL we will fetch 10 times (one per user id, 1 through 10).
BASE_URL = "https://jsonplaceholder.typicode.com/users/{}"


# ==================================================================
# 3. SLOW version: fetch URLs one after another
# ==================================================================
async def fetch_one_slow(client: httpx.AsyncClient, url: str) -> bool:
    """Fetch one URL and return True if it succeeded, False otherwise."""
    try:
        response = await client.get(url, timeout=10.0)
        # If the status code is an error, raise an exception so we can catch it.
        response.raise_for_status()
        return True
    except httpx.HTTPError:
        # One failure does not kill the rest; just report False.
        return False


async def slow_version() -> tuple[int, int, float]:
    """Fetch 10 URLs one at a time. Returns (succeeded, failed, total_seconds)."""
    succeeded = 0
    failed = 0
    start = time.monotonic()

    async with httpx.AsyncClient() as client:
        for i in range(1, 11):
            url = BASE_URL.format(i)
            ok = await fetch_one_slow(client, url)
            if ok:
                succeeded += 1
            else:
                failed += 1

    total = time.monotonic() - start
    return succeeded, failed, total


# ==================================================================
# 4. FAST version: fetch all URLs at once with asyncio.gather
# ==================================================================
# A Semaphore limits how many requests run at the same time.
# Free APIs rate-limit you, so 5 concurrent requests is safe.
SEMAPHORE = asyncio.Semaphore(5)


async def fetch_one_fast(
    client: httpx.AsyncClient, url: str, semaphore: asyncio.Semaphore
) -> bool:
    """Fetch one URL with a concurrency limit. Returns True on success."""
    async with semaphore:
        try:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            return True
        except httpx.HTTPError:
            return False


async def fast_version() -> tuple[int, int, float]:
    """Fetch 10 URLs concurrently with a limit of 5 at a time."""
    succeeded = 0
    failed = 0
    start = time.monotonic()

    async with httpx.AsyncClient() as client:
        # Create one task per URL.
        tasks = [
            fetch_one_fast(client, BASE_URL.format(i), SEMAPHORE) for i in range(1, 11)
        ]
        # asyncio.gather runs all tasks and waits for all of them.
        results = await asyncio.gather(*tasks)

    for ok in results:
        if ok:
            succeeded += 1
        else:
            failed += 1

    total = time.monotonic() - start
    return succeeded, failed, total


# ==================================================================
# 6. Run both versions and print times side by side
# ==================================================================
async def main() -> None:
    print("Fetching 10 URLs from jsonplaceholder.typicode.com ...")
    print()

    s_succ, s_fail, s_time = await slow_version()
    f_succ, f_fail, f_time = await fast_version()

    print(f"{'Version':<12} | {'Succeeded':<10} | {'Failed':<7} | {'Time (s)'}")
    print("-" * 45)
    print(f"{'Slow (sequential)':<12} | {s_succ:<10} | {s_fail:<7} | {s_time:.2f}")
    print(f"{'Fast (async + gather)':<12} | {f_succ:<10} | {f_fail:<7} | {f_time:.2f}")
    print()
    print(f"Speedup: {s_time / f_time:.1f}x faster with async.")


if __name__ == "__main__":
    asyncio.run(main())