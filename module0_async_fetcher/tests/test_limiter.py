import pytest
import asyncio
import time
from src.fetcher.limiter import TokenBucket

@pytest.mark.asyncio
async def test_token_bucket_rate_limiting():
    bucket = TokenBucket(rate=2.0, capacity=1.0)
    
    start = time.monotonic()
    # 5 вызовов при rate=2 и capacity=1:
    # 1-й: мгновенно (осталось 0)
    # 2-й: ждет 0.5с
    # 3-й: ждет 0.5с
    # 4-й: ждет 0.5с
    # 5-й: ждет 0.5с
    # Итого минимум 2.0 секунды
    
    tasks = [bucket.acquire() for _ in range(5)]
    await asyncio.gather(*tasks)
    
    elapsed = time.monotonic() - start
    assert elapsed >= 1.9, f"Ожидалось >= 1.9s, прошло {elapsed:.2f}s"