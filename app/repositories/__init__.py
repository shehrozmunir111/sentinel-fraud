"""
SentinelFraud User + Alert Repositories
Stage 2: Repository pattern, SOLID principles
"""

import uuid
from typing import Optional, Tuple

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Alert, FraudRule, MLModelRecord, User


# ---------------------------------------------------------------------------
# User Repository
# ---------------------------------------------------------------------------
class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> User:
        user = User(**data)
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_list(self, offset: int = 0, limit: int = 20) -> Tuple[list[User], int]:
        q = select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
        count_q = select(func.count(User.id))
        rows = await self.db.execute(q)
        total = await self.db.execute(count_q)
        return list(rows.scalars()), total.scalar_one()

    async def update(self, user_id: uuid.UUID, data: dict) -> Optional[User]:
        await self.db.execute(update(User).where(User.id == user_id).values(**data))
        return await self.get_by_id(user_id)


# ---------------------------------------------------------------------------
# Alert Repository
# ---------------------------------------------------------------------------
class AlertRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> Alert:
        alert = Alert(**data)
        self.db.add(alert)
        await self.db.flush()
        await self.db.refresh(alert)
        return alert

    async def get_by_id(self, alert_id: uuid.UUID) -> Optional[Alert]:
        result = await self.db.execute(select(Alert).where(Alert.id == alert_id))
        return result.scalar_one_or_none()

    async def get_list(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Tuple[list[Alert], int]:
        q = select(Alert)
        count_q = select(func.count(Alert.id))
        if status:
            q = q.where(Alert.status == status)
            count_q = count_q.where(Alert.status == status)
        if severity:
            q = q.where(Alert.severity == severity)
            count_q = count_q.where(Alert.severity == severity)
        q = q.order_by(Alert.created_at.desc()).offset(offset).limit(limit)
        rows = await self.db.execute(q)
        total = await self.db.execute(count_q)
        return list(rows.scalars()), total.scalar_one()

    async def update(self, alert_id: uuid.UUID, data: dict) -> Optional[Alert]:
        await self.db.execute(update(Alert).where(Alert.id == alert_id).values(**data))
        return await self.get_by_id(alert_id)

    async def count_open(self) -> int:
        result = await self.db.execute(
            select(func.count(Alert.id)).where(Alert.status == "open")
        )
        return result.scalar_one()

    async def count_critical(self) -> int:
        result = await self.db.execute(
            select(func.count(Alert.id)).where(
                Alert.status == "open", Alert.severity == "critical"
            )
        )
        return result.scalar_one()


# ---------------------------------------------------------------------------
# Fraud Rule Repository
# ---------------------------------------------------------------------------
class FraudRuleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> FraudRule:
        rule = FraudRule(**data)
        self.db.add(rule)
        await self.db.flush()
        await self.db.refresh(rule)
        return rule

    async def get_by_id(self, rule_id: int) -> Optional[FraudRule]:
        result = await self.db.execute(select(FraudRule).where(FraudRule.id == rule_id))
        return result.scalar_one_or_none()

    async def get_active_rules(self) -> list[FraudRule]:
        result = await self.db.execute(
            select(FraudRule).where(FraudRule.is_active == True).order_by(FraudRule.rule_type)  # noqa
        )
        return list(result.scalars())

    async def get_list(self, offset: int = 0, limit: int = 50) -> Tuple[list[FraudRule], int]:
        q = select(FraudRule).order_by(FraudRule.id).offset(offset).limit(limit)
        count_q = select(func.count(FraudRule.id))
        rows = await self.db.execute(q)
        total = await self.db.execute(count_q)
        return list(rows.scalars()), total.scalar_one()

    async def update(self, rule_id: int, data: dict) -> Optional[FraudRule]:
        await self.db.execute(update(FraudRule).where(FraudRule.id == rule_id).values(**data))
        return await self.get_by_id(rule_id)


# ---------------------------------------------------------------------------
# ML Model Repository
# ---------------------------------------------------------------------------
class MLModelRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> MLModelRecord:
        model = MLModelRecord(**data)
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        return model

    async def get_active(self) -> Optional[MLModelRecord]:
        result = await self.db.execute(
            select(MLModelRecord).where(MLModelRecord.is_active == True).limit(1)  # noqa
        )
        return result.scalar_one_or_none()

    async def deactivate_all(self) -> None:
        await self.db.execute(update(MLModelRecord).values(is_active=False))

    async def get_list(self, offset: int = 0, limit: int = 20) -> Tuple[list[MLModelRecord], int]:
        q = select(MLModelRecord).order_by(MLModelRecord.trained_at.desc()).offset(offset).limit(limit)
        count_q = select(func.count(MLModelRecord.id))
        rows = await self.db.execute(q)
        total = await self.db.execute(count_q)
        return list(rows.scalars()), total.scalar_one()
