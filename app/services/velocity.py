import redis.asyncio as redis
from app.core.config import settings
from typing import Optional
import json
from datetime import datetime, timedelta

class VelocityCheckService:
    def __init__(self):
        self.redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
    
    async def _get_key(self, prefix: str, id: str) -> str:
        return f"{prefix}:{id}:count"
    
    async def increment_and_check(
        self, 
        prefix: str, 
        id: str, 
        window_hours: int = 1,
        threshold: int = 5
    ) -> tuple[int, bool]:
        key = await self._get_key(prefix, id)
        window_seconds = window_hours * 3600
        
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds)
        results = await pipe.execute()
        count = results[0]
        
        return count, count > threshold
    
    async def check_card_velocity(self, card_id: str) -> tuple[int, int]:
        count, violated = await self.increment_and_check("card", card_id, 1, 5)
        score = 30 if violated else 0
        return count, score
    
    async def check_user_velocity(self, user_id: str) -> tuple[int, int]:
        count, violated = await self.increment_and_check("user", str(user_id), 1, 10)
        score = 20 if violated else 0
        return count, score
    
    async def check_device_velocity(self, device_fingerprint: str) -> tuple[int, int]:
        if not device_fingerprint:
            return 0, 0
        count, violated = await self.increment_and_check("device", device_fingerprint, 1, 20)
        score = 40 if violated else 0
        return count, score
    
    async def cache_risk_score(self, transaction_id: str, score_data: dict, ttl: int = 86400):
        key = f"risk_score:{transaction_id}"
        await self.redis.setex(key, ttl, json.dumps(score_data))
    
    async def get_cached_risk_score(self, transaction_id: str) -> Optional[dict]:
        key = f"risk_score:{transaction_id}"
        data = await self.redis.get(key)
        return json.loads(data) if data else None
    
    async def get_last_transaction_location(self, user_id: str) -> Optional[dict]:
        key = f"last_tx_location:{user_id}"
        data = await self.redis.get(key)
        return json.loads(data) if data else None
    
    async def set_last_transaction_location(self, user_id: str, location: dict, ttl: int = 86400):
        key = f"last_tx_location:{user_id}"
        await self.redis.setex(key, ttl, json.dumps(location))