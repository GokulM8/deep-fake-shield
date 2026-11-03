"""Request guards for a single public instance: per-client rate limit and a cap on running analyses."""

import time
from collections import deque
from threading import BoundedSemaphore, Lock


class RateLimiter:
    """Sliding-window limit of accepted analyses per client key (an IP address)."""

    def __init__(self, limit: int, window_seconds: float = 3600.0) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    @property
    def enabled(self) -> bool:
        return self.limit > 0

    def _prune(self, now: float) -> None:
        cutoff = now - self.window
        for key in list(self._hits):
            hits = self._hits[key]
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if not hits:
                del self._hits[key]

    def retry_after(self, key: str) -> int | None:
        """Seconds until ``key`` may submit again, or None when it is under the limit."""
        if not self.enabled:
            return None
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            hits = self._hits.get(key)
            if hits is None or len(hits) < self.limit:
                return None
            return max(1, int(hits[0] + self.window - now) + 1)

    def record(self, key: str) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._hits.setdefault(key, deque()).append(time.monotonic())

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


class AnalysisSlots:
    """Non-blocking cap on analyses in flight, so extra uploads get a busy response instead of queueing."""

    def __init__(self, capacity: int) -> None:
        self.capacity = max(1, capacity)
        self._slots = BoundedSemaphore(self.capacity)

    def try_acquire(self) -> bool:
        return self._slots.acquire(blocking=False)

    def release(self) -> None:
        self._slots.release()
