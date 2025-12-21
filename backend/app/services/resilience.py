"""
Resilience Module - Advanced error handling, retries, and circuit breakers.
Makes the Phase Omega system production-ready and fault-tolerant.
"""
import logging
import asyncio
import time
from typing import Callable, Any, Optional, Dict, TypeVar, Awaitable
from functools import wraps
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Circuit tripped, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker pattern for external service calls.
    Prevents cascading failures by failing fast when a service is down.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_duration: int = 60,
        success_threshold: int = 2,
    ):
        self.failure_threshold = failure_threshold
        self.timeout_duration = timeout_duration  # seconds
        self.success_threshold = success_threshold

        self.failure_count = 0
        self.success_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time: Optional[datetime] = None

    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.success_count = 0
                logger.info("Circuit breaker CLOSED - service recovered")

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        self.success_count = 0

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker OPEN - {self.failure_count} failures")

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True

        elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
        return elapsed >= self.timeout_duration


def retry_with_exponential_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff calculation
        exceptions: Tuple of exceptions to catch and retry
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            f"❌ {func.__name__} failed after {max_retries} retries: {e}",
                            exc_info=True,
                        )
                        raise e

                    logger.warning(
                        f"⚠️ {func.__name__} attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    await asyncio.sleep(delay)

                    # Exponential backoff
                    delay = min(delay * exponential_base, max_delay)

            # Should never reach here, but just in case
            raise last_exception

        return wrapper

    return decorator


class MetricsCollector:
    """
    Collects and aggregates metrics for monitoring.
    Provides insights into system performance and health.
    """

    def __init__(self):
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, list] = defaultdict(list)
        self.timers: Dict[str, list] = defaultdict(list)

    def increment(self, metric: str, value: int = 1):
        """Increment a counter metric"""
        self.counters[metric] += value
        logger.debug(f"📊 Metric {metric}: {self.counters[metric]}")

    def gauge(self, metric: str, value: float):
        """Set a gauge metric"""
        self.gauges[metric] = value
        logger.debug(f"📊 Gauge {metric}: {value}")

    def histogram(self, metric: str, value: float):
        """Record a histogram value"""
        self.histograms[metric].append(value)

        # Keep only last 1000 values
        if len(self.histograms[metric]) > 1000:
            self.histograms[metric] = self.histograms[metric][-1000:]

    def timer(self, metric: str):
        """Context manager for timing operations"""
        return TimerContext(self, metric)

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        summary = {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histograms": {
                metric: {
                    "count": len(values),
                    "min": min(values) if values else 0,
                    "max": max(values) if values else 0,
                    "avg": sum(values) / len(values) if values else 0,
                }
                for metric, values in self.histograms.items()
            },
        }
        return summary

    def reset(self):
        """Reset all metrics"""
        self.counters.clear()
        self.gauges.clear()
        self.histograms.clear()
        self.timers.clear()


class TimerContext:
    """Context manager for timing operations"""

    def __init__(self, collector: MetricsCollector, metric: str):
        self.collector = collector
        self.metric = metric
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.collector.histogram(self.metric, duration)
        return False


class RateLimiter:
    """
    Token bucket rate limiter for controlling request rates.
    Prevents overwhelming external services or databases.
    """

    def __init__(self, rate: float, capacity: int):
        """
        Args:
            rate: Tokens added per second
            capacity: Maximum tokens in bucket
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self.lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens from bucket.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens acquired, False if rate limit exceeded
        """
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_update

            # Add tokens based on elapsed time
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            else:
                return False

    async def wait_for_tokens(self, tokens: int = 1):
        """Wait until tokens are available"""
        while not await self.acquire(tokens):
            await asyncio.sleep(0.1)


# Singleton instances
_metrics_collector = MetricsCollector()
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector"""
    return _metrics_collector


def get_circuit_breaker(name: str) -> CircuitBreaker:
    """Get or create circuit breaker by name"""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker()
    return _circuit_breakers[name]


def monitored(metric_prefix: str = "function"):
    """
    Decorator to automatically monitor function execution.
    Records execution count, duration, and errors.
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            metrics = get_metrics_collector()
            func_name = func.__name__

            metrics.increment(f"{metric_prefix}.{func_name}.calls")

            try:
                with metrics.timer(f"{metric_prefix}.{func_name}.duration"):
                    result = await func(*args, **kwargs)

                metrics.increment(f"{metric_prefix}.{func_name}.success")
                return result

            except Exception as e:
                metrics.increment(f"{metric_prefix}.{func_name}.errors")
                raise e

        return wrapper

    return decorator


# Health check utilities
class HealthStatus(Enum):
    """Health check status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheck:
    """Performs health checks on system components"""

    def __init__(self):
        self.checks: Dict[str, Callable] = {}

    def register(self, name: str, check_func: Callable):
        """Register a health check"""
        self.checks[name] = check_func

    async def run_all(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {}
        overall_status = HealthStatus.HEALTHY

        for name, check_func in self.checks.items():
            try:
                result = await check_func()
                results[name] = result

                if result.get("status") == HealthStatus.UNHEALTHY.value:
                    overall_status = HealthStatus.UNHEALTHY
                elif result.get("status") == HealthStatus.DEGRADED.value and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED

            except Exception as e:
                logger.error(f"Health check {name} failed: {e}")
                results[name] = {
                    "status": HealthStatus.UNHEALTHY.value,
                    "error": str(e),
                }
                overall_status = HealthStatus.UNHEALTHY

        return {
            "status": overall_status.value,
            "checks": results,
            "timestamp": datetime.utcnow().isoformat(),
        }


_health_check = HealthCheck()


def get_health_check() -> HealthCheck:
    """Get global health check instance"""
    return _health_check
