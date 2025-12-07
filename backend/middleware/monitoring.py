import logging
from time import time
from typing import Callable

from fastapi import Request

logger = logging.getLogger(__name__)


async def monitor_requests(request: Request, call_next: Callable):
    """Monitor API requests for latency and errors."""
    start_time = time()
    logger.info("Request: %s %s", request.method, request.url.path)

    try:
        response = await call_next(request)
    except Exception as exc:  # pragma: no cover - passthrough
        duration = time() - start_time
        logger.error(
            "Error: %s Duration: %.2fs Path: %s",
            str(exc),
            duration,
            request.url.path,
        )
        raise

    duration = time() - start_time
    logger.info(
        "Response: %s Duration: %.2fs Path: %s",
        response.status_code,
        duration,
        request.url.path,
    )
    response.headers["X-Process-Time"] = f"{duration:.4f}"
    return response
