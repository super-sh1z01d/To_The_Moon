"""Asynchronous token-bucket rate limiter for outbound API calls."""

from __future__ import annotations

import asyncio
import time
from typing import Optional


class AsyncRateLimiter:
    """Simple async token bucket limiter.

    Parameters
    ----------
    rate_per_sec:
        Number of tokens refilled each second.
    max_burst:
        Maximum burst capacity.
    """

    def __init__(self, rate_per_sec: float, max_burst: int) -> None:
        if rate_per_sec <= 0:
            raise ValueError("rate_per_sec must be positive")
        if max_burst <= 0:
            raise ValueError("max_burst must be positive")

        self._rate = float(rate_per_sec)
        self._capacity = int(max_burst)
        self._tokens = float(max_burst)
        self._lock = asyncio.Lock()
        self._last_refill = time.monotonic()

    async def acquire(self, cost: int = 1, timeout: Optional[float] = None) -> None:
        """Acquire tokens from the bucket, waiting when necessary."""
        if cost <= 0:
            return

        deadline = None if timeout is None else time.monotonic() + timeout

        async with self._lock:
            while True:
                self._refill()
                if self._tokens >= cost:
                    self._tokens -= cost
                    return

                wait_time = (cost - self._tokens) / self._rate

                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise asyncio.TimeoutError("Rate limiter acquire timed out")
                    wait_time = min(wait_time, max(0.0, remaining))

                await asyncio.sleep(wait_time)

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        if elapsed <= 0:
            return
        self._last_refill = now
        refill = elapsed * self._rate
        if refill <= 0:
            return
        self._tokens = min(self._tokens + refill, self._capacity)

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def rate(self) -> float:
        return self._rate

