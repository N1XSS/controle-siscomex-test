"""Simple token bucket rate limiter."""

from __future__ import annotations

import threading
import time


class TokenBucket:
    """Token bucket limiter for steady-rate throttling with burst support."""

    def __init__(self, rate_per_sec: float, capacity: int) -> None:
        self._rate_per_sec = rate_per_sec
        self._capacity = max(1, capacity)
        self._tokens = float(self._capacity)
        self._updated_at = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, tokens: float = 1.0) -> None:
        """Block until enough tokens are available."""
        if self._rate_per_sec <= 0:
            return

        tokens = max(0.0, float(tokens))
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = max(0.0, now - self._updated_at)
                self._tokens = min(self._capacity, self._tokens + elapsed * self._rate_per_sec)
                self._updated_at = now

                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return

                missing = tokens - self._tokens
                wait_time = missing / self._rate_per_sec

            time.sleep(wait_time)
