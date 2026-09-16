import time
import asyncio

class TokenBucket:
    def __init__(self, rate: float, capacity: float):
        self.rate = rate 
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()
        
    async def acquire(self):
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self.last_update
                
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                self.last_update = now
                
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return
                
                wait_time = (1.0 - self.tokens) / self.rate
                
            await asyncio.sleep(wait_time)
            
    async def __aenter__(self):
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        pass