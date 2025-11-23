"""Token-based rate limiter for LLM API calls."""

import asyncio
import time
import tiktoken
from typing import Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter for managing TPM (tokens per minute) limits.

    Tracks token usage over a sliding window and ensures we stay within
    the configured TPM limit.
    """

    def __init__(self, tpm_limit: int):
        """
        Initialize rate limiter.

        Args:
            tpm_limit: Tokens per minute limit
        """
        self.tpm_limit = tpm_limit
        self.tokens_used = 0
        self.window_start = time.time()
        self.lock = asyncio.Lock()

    async def acquire(self, estimated_tokens: int) -> None:
        """
        Wait until we can proceed with a request that uses estimated_tokens.

        This implements a sliding window approach:
        - If we're in a new minute window, reset the counter
        - If we would exceed the limit, wait until the next window
        - Track the tokens we're about to use

        Args:
            estimated_tokens: Estimated tokens for the request
        """
        async with self.lock:
            current_time = time.time()
            elapsed = current_time - self.window_start

            # If more than 60 seconds elapsed, start a new window
            if elapsed >= 60:
                self.tokens_used = 0
                self.window_start = current_time
                elapsed = 0

            # If adding this request would exceed limit, wait
            if self.tokens_used + estimated_tokens > self.tpm_limit:
                sleep_time = 60 - elapsed
                logger.info(
                    f"Rate limit: {self.tokens_used}/{self.tpm_limit} tokens used. "
                    f"Waiting {sleep_time:.1f}s for new window..."
                )
                await asyncio.sleep(sleep_time)

                # Reset for new window
                self.tokens_used = 0
                self.window_start = time.time()

            # Reserve tokens for this request
            self.tokens_used += estimated_tokens
            logger.debug(
                f"Rate limiter: reserved {estimated_tokens} tokens. "
                f"Total: {self.tokens_used}/{self.tpm_limit}"
            )

    def report_actual_usage(self, actual_tokens: int, estimated_tokens: int) -> None:
        """
        Update token count with actual usage.

        This adjusts our tracking based on the actual tokens used vs estimated.

        Args:
            actual_tokens: Actual tokens used from API response
            estimated_tokens: Our estimated tokens
        """
        difference = actual_tokens - estimated_tokens
        self.tokens_used += difference

        if abs(difference) > 100:
            logger.debug(
                f"Token estimation off by {difference}. "
                f"Estimated: {estimated_tokens}, Actual: {actual_tokens}"
            )


def estimate_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Estimate the number of tokens in a text string.

    Uses tiktoken library for accurate token counting.

    Args:
        text: The text to count tokens for
        model: The model name (for encoder selection)

    Returns:
        Estimated token count
    """
    try:
        # Try to get encoding for the specific model
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fall back to cl100k_base (used by GPT-4, GPT-3.5-turbo, etc.)
        encoding = tiktoken.get_encoding("cl100k_base")

    return len(encoding.encode(text))


def estimate_request_tokens(
    system_prompt: str,
    user_prompt: str,
    model: str = "gpt-4",
    response_buffer: int = 500,
) -> int:
    """
    Estimate total tokens for a chat completion request.

    Includes system prompt, user prompt, and estimated response tokens.

    Args:
        system_prompt: The system prompt
        user_prompt: The user prompt
        model: The model name
        response_buffer: Estimated tokens for the response (conservative estimate)

    Returns:
        Total estimated tokens (input + output)
    """
    input_tokens = estimate_tokens(system_prompt, model) + estimate_tokens(
        user_prompt, model
    )
    # Add overhead for message structure (~4 tokens per message)
    overhead = 8
    total = input_tokens + overhead + response_buffer

    return total
