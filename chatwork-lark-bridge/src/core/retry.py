"""Retry logic with exponential backoff."""

import asyncio
import logging
from typing import Callable, TypeVar, ParamSpec
from functools import wraps

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
)

from .config import settings
from .exceptions import RetryableError, RateLimitError
from .logging import get_logger

logger = get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def create_retry_decorator(
    max_attempts: int | None = None,
    min_wait: int | None = None,
    max_wait: int | None = None,
):
    """Create a retry decorator with custom settings."""
    return retry(
        stop=stop_after_attempt(max_attempts or settings.max_retry_attempts),
        wait=wait_exponential(
            multiplier=1,
            min=min_wait or settings.retry_min_wait_seconds,
            max=max_wait or settings.retry_max_wait_seconds,
        ),
        retry=retry_if_exception_type((RetryableError, RateLimitError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO),
        reraise=True,
    )


# Default retry decorator
retry_on_error = create_retry_decorator()


def async_retry(
    max_attempts: int | None = None,
    min_wait: int | None = None,
    max_wait: int | None = None,
):
    """Async retry decorator with exponential backoff."""

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            retry_decorator = create_retry_decorator(max_attempts, min_wait, max_wait)
            decorated_func = retry_decorator(func)
            return await decorated_func(*args, **kwargs)

        return wrapper

    return decorator


async def retry_with_rate_limit_handling(
    func: Callable[P, T],
    *args: P.args,
    **kwargs: P.kwargs,
) -> T:
    """
    Retry a function with special handling for rate limit errors.

    If RateLimitError is raised with retry_after, wait for that duration
    before retrying.
    """
    attempt = 0
    max_attempts = settings.max_retry_attempts

    while attempt < max_attempts:
        try:
            return await func(*args, **kwargs)
        except RateLimitError as e:
            attempt += 1
            if attempt >= max_attempts:
                logger.error(
                    "max_retries_exceeded_rate_limit",
                    platform=e.platform,
                    attempt=attempt,
                )
                raise

            wait_time = e.retry_after or (2 ** attempt)
            logger.warning(
                "rate_limit_hit_retrying",
                platform=e.platform,
                attempt=attempt,
                wait_time=wait_time,
            )
            await asyncio.sleep(wait_time)
        except RetryableError as e:
            attempt += 1
            if attempt >= max_attempts:
                logger.error(
                    "max_retries_exceeded",
                    error=str(e),
                    attempt=attempt,
                )
                raise

            wait_time = min(
                settings.retry_max_wait_seconds,
                settings.retry_min_wait_seconds * (2 ** attempt),
            )
            logger.warning(
                "retryable_error_retrying",
                error=str(e),
                attempt=attempt,
                wait_time=wait_time,
            )
            await asyncio.sleep(wait_time)
