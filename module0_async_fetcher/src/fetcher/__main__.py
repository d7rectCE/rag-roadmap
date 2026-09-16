import asyncio
import time
import structlog
from .config import Settings
from .client import fetch_all, fetch_all_strict
from .models import FetchStats

def setup_logging(log_level: str):
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
    )

async def main():
    settings = Settings()
    setup_logging(settings.log_level)
    
    base_url = "https://httpbin.org"
    urls = [
        f"{base_url}/delay/1",
        f"{base_url}/delay/2",
        f"{base_url}/status/500",
        f"{base_url}/status/503",
        f"{base_url}/status/404",
        f"{base_url}/status/429",
        f"{base_url}/delay/10",
        f"{base_url}/get",
        f"{base_url}/get",
        f"{base_url}/get",
        f"{base_url}/get",
        f"{base_url}/get",
    ]

    logger = structlog.get_logger()
    logger.info("run_started", mode="gather", total_urls=len(urls))
    
    start_time = time.monotonic()
    results = await fetch_all(urls, settings)
    total_duration = time.monotonic() - start_time

    ok_count = sum(1 for r in results if r.status == "ok")
    failed_count = len(results) - ok_count
    total_attempts = sum(r.attempts for r in results)
    
    error_counts = {}
    for r in results:
        if r.status == "error" and r.error_type:
            error_counts[r.error_type] = error_counts.get(r.error_type, 0) + 1

    stats = FetchStats(
        total=len(results),
        ok=ok_count,
        failed=failed_count,
        total_duration=round(total_duration, 2),
        avg_duration=round(sum(r.duration for r in results) / len(results), 2) if results else 0.0,
        total_attempts=total_attempts,
        by_error_type=error_counts
    )

    logger.info("run_complete", **stats.model_dump())

if __name__ == "__main__":
    asyncio.run(main())