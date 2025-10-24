import time
from typing import Dict, Tuple


class SimpleRateLimiter:
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self.buckets: Dict[str, Tuple[int, float]] = {}

    def allow(self, key: str) -> bool:
        now = time.time()
        count, start = self.buckets.get(key, (0, now))
        if now - start > self.window:
            self.buckets[key] = (1, now)
            return True
        if count < self.max_requests:
            self.buckets[key] = (count + 1, start)
            return True
        return False

