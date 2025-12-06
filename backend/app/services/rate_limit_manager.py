"""
Rate Limit Manager - Centralized OpenAI Rate-Limit Tracking

Manages per-model RPM (Requests Per Minute) and TPM (Tokens Per Minute) quotas
using sliding window counters to prevent 429 errors before they happen.

Production Limits:
- gpt-4o-mini: 200,000 TPM, 500 RPM, 10,000 RPD
- gpt-4o: 30,000 TPM, 500 RPM

Architecture:
- Thread-safe sliding windows for RPM/TPM
- Pre-flight quota checks before OpenAI calls
- Automatic quota release on failure
- Load shedding recommendations
"""
import time
import logging
import threading
from collections import deque
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class QuotaUsage:
    """Snapshot of current quota usage"""
    rpm_used: int
    rpm_limit: int
    tpm_used: int
    tpm_limit: int
    rpm_available: int
    tpm_available: int
    utilization_pct: float


class SlidingWindow:
    """Thread-safe sliding window counter for rate limiting"""

    def __init__(self, limit: int, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self.entries = deque()  # [(timestamp, value), ...]
        self.lock = threading.Lock()

    def add(self, value: int) -> bool:
        """Add entry to window. Returns True if within limit, False if exceeded."""
        now = time.time()

        with self.lock:
            # Remove expired entries
            self._cleanup(now)

            # Check if adding this would exceed limit
            current_total = sum(v for _, v in self.entries)
            if current_total + value > self.limit:
                return False

            # Add entry
            self.entries.append((now, value))
            return True

    def reserve(self, value: int) -> bool:
        """Try to reserve quota. Returns True if successful."""
        return self.add(value)

    def release(self, value: int):
        """
        🚨 CRITICAL FIX: Release quota when a reservation is not used.
        Used when RPM is reserved but TPM check fails.
        """
        now = time.time()
        with self.lock:
            # Remove the most recent entry that matches the value
            # (FIFO release - remove last added entry)
            for i in range(len(self.entries) - 1, -1, -1):
                timestamp, entry_value = self.entries[i]
                if entry_value == value and (now - timestamp) < 5.0:  # Only release recent entries
                    del self.entries[i]
                    logger.debug(f"Released quota: {value}")
                    return

    def get_usage(self) -> int:
        """Get current usage within window"""
        now = time.time()
        with self.lock:
            self._cleanup(now)
            return sum(v for _, v in self.entries)

    def get_available(self) -> int:
        """Get available quota"""
        return max(0, self.limit - self.get_usage())

    def _cleanup(self, now: float):
        """Remove entries older than window (must be called with lock held)"""
        cutoff = now - self.window_seconds
        while self.entries and self.entries[0][0] < cutoff:
            self.entries.popleft()


class RateLimitManager:
    """
    Centralized rate-limit manager for all OpenAI API calls.

    Prevents 429 errors by:
    1. Tracking RPM/TPM usage per model in sliding windows
    2. Pre-flight checks before making OpenAI calls
    3. Reserving quota before call, releasing on failure
    4. Providing load-shedding recommendations
    """

    # Production limits (from OpenAI dashboard)
    MODEL_LIMITS = {
        "gpt-4o-mini": {
            "rpm": 500,
            "tpm": 200000,
            "rpd": 10000,
        },
        "gpt-4o": {
            "rpm": 500,
            "tpm": 30000,
        },
        "gpt-4o-mini-audio-preview": {
            "rpm": 500,
            "tpm": 200000,
        },
    }

    # Warn thresholds (80% of limit)
    WARN_THRESHOLD = 0.80

    # Load shedding threshold (95% of limit)
    SHED_THRESHOLD = 0.95

    def __init__(self):
        """Initialize rate-limit manager with sliding windows for each model"""
        self.windows: Dict[str, Dict[str, SlidingWindow]] = {}

        # Create sliding windows for each model
        for model, limits in self.MODEL_LIMITS.items():
            self.windows[model] = {
                "rpm": SlidingWindow(limit=limits["rpm"], window_seconds=60),
                "tpm": SlidingWindow(limit=limits["tpm"], window_seconds=60),
            }

        logger.info("✅ Rate-limit manager initialized")
        logger.info(f"   Models: {list(self.MODEL_LIMITS.keys())}")

    def check_and_reserve(
        self,
        model: str,
        estimated_tokens: int,
    ) -> Tuple[bool, Optional[str]]:
        """
        Pre-flight check: Can we make this call?

        Args:
            model: OpenAI model name
            estimated_tokens: Estimated token count for request

        Returns:
            (success: bool, reason: Optional[str])
            - (True, None) if quota available and reserved
            - (False, "rpm_exceeded") if RPM quota exhausted
            - (False, "tpm_exceeded") if TPM quota exhausted
            - (False, "unknown_model") if model not configured
        """
        # Normalize model name
        model = self._normalize_model(model)

        if model not in self.windows:
            logger.warning(f"⚠️ Unknown model: {model}, allowing call")
            return (True, None)

        windows = self.windows[model]

        # Check RPM
        if not windows["rpm"].reserve(1):
            rpm_used = windows["rpm"].get_usage()
            rpm_limit = windows["rpm"].limit
            logger.warning(
                f"⛔ RPM limit exceeded for {model}: {rpm_used}/{rpm_limit}"
            )
            return (False, "rpm_exceeded")

        # Check TPM
        if not windows["tpm"].reserve(estimated_tokens):
            # 🚨 CRITICAL FIX: Release RPM reservation since TPM check failed
            windows["rpm"].release(1)
            tpm_used = windows["tpm"].get_usage()
            tpm_limit = windows["tpm"].limit
            logger.warning(
                f"⛔ TPM limit exceeded for {model}: {tpm_used}/{tpm_limit} (requested {estimated_tokens})"
            )
            logger.debug(f"🔓 Released RPM quota after TPM failure")
            return (False, "tpm_exceeded")

        logger.debug(
            f"✅ Quota reserved for {model}: 1 request, {estimated_tokens} tokens"
        )
        return (True, None)

    def record_success(self, model: str, actual_tokens: int):
        """
        Record successful API call with actual token usage.

        Note: Reservation already happened in check_and_reserve().
        This is just for logging/metrics.
        """
        model = self._normalize_model(model)
        logger.debug(f"✅ Recorded success for {model}: {actual_tokens} tokens")

    def get_quota_usage(self, model: str) -> QuotaUsage:
        """Get current quota usage for a model"""
        model = self._normalize_model(model)

        if model not in self.windows:
            return QuotaUsage(
                rpm_used=0,
                rpm_limit=0,
                tpm_used=0,
                tpm_limit=0,
                rpm_available=0,
                tpm_available=0,
                utilization_pct=0.0,
            )

        windows = self.windows[model]
        limits = self.MODEL_LIMITS[model]

        rpm_used = windows["rpm"].get_usage()
        tpm_used = windows["tpm"].get_usage()

        rpm_available = windows["rpm"].get_available()
        tpm_available = windows["tpm"].get_available()

        # Calculate utilization as max of RPM and TPM utilization
        rpm_util = (rpm_used / limits["rpm"]) * 100 if limits["rpm"] > 0 else 0
        tpm_util = (tpm_used / limits["tpm"]) * 100 if limits["tpm"] > 0 else 0
        utilization_pct = max(rpm_util, tpm_util)

        return QuotaUsage(
            rpm_used=rpm_used,
            rpm_limit=limits["rpm"],
            tpm_used=tpm_used,
            tpm_limit=limits["tpm"],
            rpm_available=rpm_available,
            tpm_available=tpm_available,
            utilization_pct=utilization_pct,
        )

    def should_shed_load(self, model: str) -> bool:
        """
        Check if we should shed load for this model.

        Returns True if utilization > 95%
        """
        usage = self.get_quota_usage(model)
        return usage.utilization_pct >= (self.SHED_THRESHOLD * 100)

    def should_warn(self, model: str) -> bool:
        """
        Check if we should warn about approaching limits.

        Returns True if utilization > 80%
        """
        usage = self.get_quota_usage(model)
        return usage.utilization_pct >= (self.WARN_THRESHOLD * 100)

    def recommend_model(self, preferred_model: str) -> str:
        """
        Recommend a model based on quota availability.

        If preferred model is rate-limited, fall back to gpt-4o-mini.
        """
        preferred_model = self._normalize_model(preferred_model)

        # Check if preferred model has capacity
        if not self.should_shed_load(preferred_model):
            return preferred_model

        # Try fallback to gpt-4o-mini
        fallback = "gpt-4o-mini"
        if fallback != preferred_model and not self.should_shed_load(fallback):
            logger.warning(
                f"⚠️ Falling back from {preferred_model} to {fallback} due to rate limits"
            )
            return fallback

        # All models rate-limited - return preferred anyway
        logger.error(f"🚨 All models rate-limited, using {preferred_model} anyway")
        return preferred_model

    def _normalize_model(self, model: str) -> str:
        """Normalize model name to match MODEL_LIMITS keys"""
        # Handle common variations
        if model in self.MODEL_LIMITS:
            return model

        # Try exact match first
        for key in self.MODEL_LIMITS.keys():
            if key in model or model in key:
                return key

        # Default to gpt-4o-mini for unknown models
        logger.warning(f"Unknown model {model}, defaulting to gpt-4o-mini limits")
        return "gpt-4o-mini"

    def get_all_quotas(self) -> Dict[str, QuotaUsage]:
        """Get quota usage for all models"""
        return {
            model: self.get_quota_usage(model) for model in self.MODEL_LIMITS.keys()
        }


# Singleton instance
_rate_limit_manager: Optional[RateLimitManager] = None


def get_rate_limit_manager() -> RateLimitManager:
    """Get singleton instance of RateLimitManager"""
    global _rate_limit_manager
    if _rate_limit_manager is None:
        _rate_limit_manager = RateLimitManager()
    return _rate_limit_manager
