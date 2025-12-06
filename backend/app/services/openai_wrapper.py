"""
OpenAI Wrapper - Rate-Limit-Aware Client with Custom Retry Logic

Wraps OpenAI client to prevent webhook timeouts from 429 errors:
1. Checks rate-limit quota BEFORE making calls
2. Custom retry logic with exponential backoff + jitter
3. Max retry time < 10 seconds (never blocks webhook)
4. Async-friendly with asyncio.to_thread

This module REPLACES direct OpenAI client usage throughout the codebase.
"""
import os
import asyncio
import logging
import random
import time
from typing import Dict, Any, List, Optional
from openai import OpenAI, RateLimitError, APIError

from .rate_limit_manager import get_rate_limit_manager, RateLimitManager

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Raised when rate-limit quota is exhausted"""

    pass


class OpenAIWrapper:
    """
    Rate-limit-aware OpenAI client wrapper.

    Key Features:
    - Pre-flight rate-limit checks
    - Custom retry logic (max 10s total)
    - Exponential backoff + jitter
    - Non-blocking (uses asyncio.to_thread)
    - Automatic model fallback
    """

    # Retry configuration
    MAX_RETRIES = 3
    BASE_DELAY = 1.0  # seconds
    MAX_TOTAL_RETRY_TIME = 10.0  # CRITICAL: Never exceed 10s total
    JITTER_FACTOR = 0.1  # 10% jitter

    def __init__(self, rate_limit_manager: Optional[RateLimitManager] = None):
        """
        Initialize OpenAI wrapper.

        Args:
            rate_limit_manager: Optional rate-limit manager (uses singleton if not provided)
        """
        self.rate_limiter = rate_limit_manager or get_rate_limit_manager()

        # Initialize OpenAI client with disabled retries
        # We handle retries ourselves
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(
            api_key=api_key,
            max_retries=0,  # CRITICAL: Disable built-in retries
            timeout=20.0,  # Single request timeout
        )

        logger.info("✅ OpenAI wrapper initialized (custom retry logic)")

    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Any:
        """
        Rate-limit-aware chat completion with custom retry logic.

        Args:
            model: OpenAI model name
            messages: Chat messages
            temperature: Temperature (0-2)
            max_tokens: Max tokens to generate
            tools: Optional tool definitions
            **kwargs: Additional OpenAI parameters

        Returns:
            OpenAI completion response

        Raises:
            RateLimitExceeded: If rate-limit quota exhausted
            APIError: If OpenAI API error occurs
        """
        # Estimate tokens (rough heuristic: ~4 chars per token)
        estimated_tokens = self._estimate_tokens(messages, max_tokens)

        # Check if we should recommend a different model
        recommended_model = self.rate_limiter.recommend_model(model)
        if recommended_model != model:
            logger.warning(
                f"⚠️ Rate-limit fallback: {model} → {recommended_model}"
            )
            model = recommended_model

        # Pre-flight check: Do we have quota?
        can_proceed, reason = self.rate_limiter.check_and_reserve(
            model, estimated_tokens
        )

        if not can_proceed:
            logger.error(
                f"⛔ Rate-limit PRE-FLIGHT BLOCK: {reason} for {model} ({estimated_tokens} tokens)"
            )
            raise RateLimitExceeded(
                f"Rate limit exceeded: {reason} (model={model}, tokens={estimated_tokens})"
            )

        # Execute with custom retry logic
        start_time = time.time()

        for attempt in range(self.MAX_RETRIES):
            try:
                logger.debug(
                    f"OpenAI call attempt {attempt + 1}/{self.MAX_RETRIES}: model={model}, tokens≈{estimated_tokens}"
                )

                # Make async call (non-blocking)
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools if tools else None,
                    **kwargs,
                )

                # Success! Record actual token usage
                actual_tokens = (
                    response.usage.total_tokens
                    if hasattr(response, "usage")
                    else estimated_tokens
                )
                self.rate_limiter.record_success(model, actual_tokens)

                elapsed = time.time() - start_time
                logger.info(
                    f"✅ OpenAI success: model={model}, tokens={actual_tokens}, time={elapsed:.2f}s"
                )

                return response

            except RateLimitError as e:
                # 429 error from OpenAI - retry with backoff
                elapsed = time.time() - start_time

                if elapsed >= self.MAX_TOTAL_RETRY_TIME:
                    logger.error(
                        f"⛔ Max retry time exceeded ({self.MAX_TOTAL_RETRY_TIME}s) after {attempt + 1} attempts"
                    )
                    raise RateLimitExceeded(
                        f"Rate limit exceeded after {attempt + 1} attempts ({elapsed:.2f}s)"
                    )

                # Calculate backoff delay with jitter
                delay = min(
                    self.BASE_DELAY * (2**attempt),
                    self.MAX_TOTAL_RETRY_TIME - elapsed,
                )
                jitter = random.uniform(0, delay * self.JITTER_FACTOR)
                total_delay = delay + jitter

                # Check if we have time for this retry
                if elapsed + total_delay >= self.MAX_TOTAL_RETRY_TIME:
                    logger.error(
                        f"⛔ No time left for retry (elapsed={elapsed:.2f}s, delay={total_delay:.2f}s)"
                    )
                    raise RateLimitExceeded(
                        f"Rate limit exceeded, no time for retry (elapsed={elapsed:.2f}s)"
                    )

                logger.warning(
                    f"⚠️ 429 Rate Limit hit (attempt {attempt + 1}/{self.MAX_RETRIES}), retrying in {total_delay:.2f}s..."
                )

                await asyncio.sleep(total_delay)

            except APIError as e:
                # Other OpenAI API errors (not rate-limit)
                logger.error(f"❌ OpenAI API error: {e}", exc_info=True)
                raise

            except Exception as e:
                # Unexpected errors
                logger.error(f"❌ Unexpected error calling OpenAI: {e}", exc_info=True)
                raise

        # Exhausted all retries
        logger.error(
            f"⛔ Exhausted all {self.MAX_RETRIES} retries for {model}"
        )
        raise RateLimitExceeded(
            f"Rate limit exceeded after {self.MAX_RETRIES} attempts"
        )

    def _estimate_tokens(
        self, messages: List[Dict[str, str]], max_tokens: int
    ) -> int:
        """
        🚨 CRITICAL FIX: More accurate token estimation to prevent TPM overruns.

        Heuristic: ~4 characters per token for English text.
        Response usage: Assume 80% of max_tokens (was 50%, caused underestimation).
        """
        # Estimate input tokens
        total_chars = sum(len(str(msg.get("content", ""))) for msg in messages)
        input_tokens = total_chars // 4

        # 🚨 CRITICAL FIX: Assume 80% of max_tokens will be used (more realistic)
        # Previous 50% assumption caused 2x underestimation
        estimated_response_tokens = int(max_tokens * 0.8)

        estimated_total = input_tokens + estimated_response_tokens

        logger.debug(
            f"📊 Token estimate: {input_tokens} input + {estimated_response_tokens} output "
            f"= {estimated_total} total"
        )

        return estimated_total

    async def embeddings(
        self,
        model: str,
        input_text: str,
        **kwargs,
    ) -> Any:
        """
        Rate-limit-aware embeddings generation.

        Args:
            model: Embedding model name (e.g., "text-embedding-ada-002")
            input_text: Text to embed
            **kwargs: Additional OpenAI parameters

        Returns:
            OpenAI embedding response
        """
        # Estimate tokens
        estimated_tokens = len(input_text) // 4

        # Check quota
        can_proceed, reason = self.rate_limiter.check_and_reserve(
            model, estimated_tokens
        )

        if not can_proceed:
            logger.error(f"⛔ Rate-limit block for embeddings: {reason}")
            raise RateLimitExceeded(
                f"Rate limit exceeded for embeddings: {reason}"
            )

        # Execute with retry logic
        start_time = time.time()

        for attempt in range(self.MAX_RETRIES):
            try:
                response = await asyncio.to_thread(
                    self.client.embeddings.create,
                    model=model,
                    input=input_text,
                    **kwargs,
                )

                # Record success
                actual_tokens = (
                    response.usage.total_tokens
                    if hasattr(response, "usage")
                    else estimated_tokens
                )
                self.rate_limiter.record_success(model, actual_tokens)

                elapsed = time.time() - start_time
                logger.info(
                    f"✅ Embeddings success: model={model}, tokens={actual_tokens}, time={elapsed:.2f}s"
                )

                return response

            except RateLimitError as e:
                elapsed = time.time() - start_time

                if elapsed >= self.MAX_TOTAL_RETRY_TIME:
                    raise RateLimitExceeded(
                        f"Embeddings rate limit exceeded after {attempt + 1} attempts"
                    )

                delay = min(
                    self.BASE_DELAY * (2**attempt),
                    self.MAX_TOTAL_RETRY_TIME - elapsed,
                )
                jitter = random.uniform(0, delay * self.JITTER_FACTOR)

                if elapsed + delay + jitter >= self.MAX_TOTAL_RETRY_TIME:
                    raise RateLimitExceeded("No time left for embeddings retry")

                logger.warning(
                    f"⚠️ Embeddings 429 (attempt {attempt + 1}/{self.MAX_RETRIES}), retrying in {delay + jitter:.2f}s..."
                )

                await asyncio.sleep(delay + jitter)

            except Exception as e:
                logger.error(f"❌ Embeddings error: {e}", exc_info=True)
                raise

        raise RateLimitExceeded(
            f"Embeddings rate limit exceeded after {self.MAX_RETRIES} attempts"
        )


# Singleton instance
_openai_wrapper: Optional[OpenAIWrapper] = None


def get_openai_wrapper() -> OpenAIWrapper:
    """Get singleton instance of OpenAIWrapper"""
    global _openai_wrapper
    if _openai_wrapper is None:
        _openai_wrapper = OpenAIWrapper()
    return _openai_wrapper
