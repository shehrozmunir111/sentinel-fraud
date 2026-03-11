"""
SentinelFraud Velocity Check Service
Stage 7: Redis sliding-window velocity counters
Rules: Card >5/h (+30), User >10/h (+20), Device >20/h (+40)
"""

import logging
from dataclasses import dataclass, field

from app.config import settings
from app.core.cache import get_velocity_counter, increment_velocity_counter

logger = logging.getLogger(__name__)


@dataclass
class VelocityResult:
    card_count: int = 0
    user_count: int = 0
    device_count: int = 0
    risk_addition: int = 0
    triggers: list[str] = field(default_factory=list)


class VelocityCheckService:
    """
    Uses Redis TTL-based counters for 1-hour sliding window velocity checks.
    All operations are async and non-blocking.
    """

    CARD_KEY = "card:{card_id}:tx_count"
    USER_KEY = "user:{user_id}:tx_count"
    DEVICE_KEY = "device:{device_id}:tx_count"
    TTL = 3600  # 1 hour

    # Risk weights
    CARD_LIMIT = 5
    CARD_WEIGHT = 30
    USER_LIMIT = 10
    USER_WEIGHT = 20
    DEVICE_LIMIT = 20
    DEVICE_WEIGHT = 40

    async def check_and_increment(
        self,
        card_id: str,
        user_id: str | None,
        device_fingerprint: str | None,
    ) -> VelocityResult:
        result = VelocityResult()

        # Card velocity
        if card_id:
            card_key = self.CARD_KEY.format(card_id=card_id)
            count = await increment_velocity_counter(card_key, self.TTL)
            result.card_count = count
            if count > self.CARD_LIMIT:
                result.risk_addition += self.CARD_WEIGHT
                result.triggers.append(
                    f"card_velocity:{count}_tx_per_hour(limit={self.CARD_LIMIT},weight=+{self.CARD_WEIGHT})"
                )

        # User velocity
        if user_id:
            user_key = self.USER_KEY.format(user_id=user_id)
            count = await increment_velocity_counter(user_key, self.TTL)
            result.user_count = count
            if count > self.USER_LIMIT:
                result.risk_addition += self.USER_WEIGHT
                result.triggers.append(
                    f"user_velocity:{count}_tx_per_hour(limit={self.USER_LIMIT},weight=+{self.USER_WEIGHT})"
                )

        # Device velocity
        if device_fingerprint:
            device_key = self.DEVICE_KEY.format(device_id=device_fingerprint)
            count = await increment_velocity_counter(device_key, self.TTL)
            result.device_count = count
            if count > self.DEVICE_LIMIT:
                result.risk_addition += self.DEVICE_WEIGHT
                result.triggers.append(
                    f"device_velocity:{count}_tx_per_hour(limit={self.DEVICE_LIMIT},weight=+{self.DEVICE_WEIGHT})"
                )

        return result

    async def get_current_velocity(
        self,
        card_id: str | None = None,
        user_id: str | None = None,
        device_fingerprint: str | None = None,
    ) -> dict:
        result = {}
        if card_id:
            result["card"] = await get_velocity_counter(
                self.CARD_KEY.format(card_id=card_id)
            )
        if user_id:
            result["user"] = await get_velocity_counter(
                self.USER_KEY.format(user_id=user_id)
            )
        if device_fingerprint:
            result["device"] = await get_velocity_counter(
                self.DEVICE_KEY.format(device_id=device_fingerprint)
            )
        return result
