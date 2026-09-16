import asyncio
import time
import random
import httpx
import structlog
from typing import Sequence, Literal

from .config import Settings
from .models import FetchResult, FetchStats
from .limiter import TokenBucket

logger = structlog.get_logger()

RETRIABLE_STATUS_CODES = {429, 500, 502, 503, 504}

def calculate_backoff(attempt: int) -> float:
    base = (2 ** attempt)
    jitter = base * 0.5 * random.random()
    return base + jitter

async def fetch_one(
    url: str,
    client: httpx.AsyncClient,
    settings: Settings,
    bucket: TokenBucket,
    semaphore: asyncio.Semaphore,
) -> FetchResult:
    start_time = time.monotonic()
    attempts = 0
    last_error_msg: str | None = None
    last_error_type: Literal["timeout", "http_error", "connection", "unknown"] | None = None

    for attempt in range(1, settings.max_retries + 2):
        attempts = attempt
        log = logger.bind(url=url, attempt=attempt)
        log.debug("fetch_started")
        
        wait_seconds = 0.0

        try:
            async with bucket:
                async with semaphore:
                    response = await client.get(url)
                    
                    if response.status_code in RETRIABLE_STATUS_CODES:
                        # Обновляем ошибку ПЕРЕД тем, как ретраить
                        last_error_msg = f"HTTP {response.status_code}"
                        last_error_type = "http_error"
                        
                        if response.status_code == 429 and "retry-after" in response.headers:
                            wait_seconds = float(response.headers["retry-after"])
                            reason = "retry_after"
                        else:
                            wait_seconds = calculate_backoff(attempt)
                            reason = "backoff"
                        
                        log.warning(
                            "fetch_retry",
                            status_code=response.status_code,
                            wait_seconds=round(wait_seconds, 2),
                            reason=reason
                        )
                    
                    else:
                        # Успех или неретраиваемая ошибка (например, 404)
                        duration = time.monotonic() - start_time
                        if response.status_code >= 400:
                            return FetchResult(
                                url=url, status="error", status_code=response.status_code,
                                response_size=len(response.content),
                                error_message=f"HTTP {response.status_code}",
                                error_type="http_error", attempts=attempts, duration=duration
                            )
                        
                        return FetchResult(
                            url=url, status="ok", status_code=response.status_code,
                            response_size=len(response.content),
                            attempts=attempts, duration=duration
                        )
                        

        except httpx.TimeoutException as e:
            last_error_msg, last_error_type = str(e), "timeout"
            wait_seconds, reason = calculate_backoff(attempt), "exception"
        except httpx.ConnectError as e:
            last_error_msg, last_error_type = str(e), "connection"
            wait_seconds, reason = calculate_backoff(attempt), "exception"
        except Exception as e:
            last_error_msg, last_error_type = str(e), "unknown"
            wait_seconds, reason = calculate_backoff(attempt), "exception"

        # единственное место, где принимается решение ждать
        is_last_attempt = attempt > settings.max_retries
        if wait_seconds > 0 and not is_last_attempt:
            log.warning(
                "fetch_retry",
                wait_seconds=round(wait_seconds, 2),
                reason=reason,
            )
            await asyncio.sleep(wait_seconds)

    # Если вышли из цикла, значит все попытки исчерпаны
    duration = time.monotonic() - start_time
    logger.error(
        "fetch_failed",
        url=url,
        error_type=last_error_type,
        attempts=attempts,
        duration=round(duration, 2)
    )
    
    return FetchResult(
        url=url, status="error", status_code=None, response_size=None,
        error_message=last_error_msg, error_type=last_error_type,
        attempts=attempts, duration=duration
    )

async def fetch_all(urls: Sequence[str], settings: Settings) -> list[FetchResult]:
    bucket = TokenBucket(rate=settings.rate_limit_per_second, capacity=settings.rate_limit_per_second)
    semaphore = asyncio.Semaphore(settings.max_concurrent)
    timeout = httpx.Timeout(
        connect=5.0,
        read=settings.timeout_seconds,
        write=settings.timeout_seconds,
        pool=5.0,
    )
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        tasks = [fetch_one(url, client, settings, bucket, semaphore) for url in urls]
        results = await asyncio.gather(*tasks)
        
    return list(results)

async def fetch_all_strict(urls: Sequence[str], settings: Settings) -> list[FetchResult]:
    bucket = TokenBucket(rate=settings.rate_limit_per_second, capacity=settings.rate_limit_per_second)
    semaphore = asyncio.Semaphore(settings.max_concurrent)
    timeout = httpx.Timeout(
        connect=5.0,
        read=settings.timeout_seconds,
        write=settings.timeout_seconds,
        pool=5.0,
    )
    
    results = []
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with asyncio.TaskGroup() as tg:
                tasks = [
                    tg.create_task(fetch_one(url, client, settings, bucket, semaphore)) 
                    for url in urls
                ]
            results = [task.result() for task in tasks]
            
    except* Exception as eg:
        logger.error("strict_fetch_failed", error_group=str(eg))
        
    return results