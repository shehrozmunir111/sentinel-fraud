from app.repositories.base import BaseRepository
from app.models.fraud_rule import FraudRule, RuleType
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

class FraudRuleRepository(BaseRepository[FraudRule]):
    def __init__(self, db: AsyncSession):
        super().__init__(FraudRule, db)
    
    async def get_active_rules(self) -> List[FraudRule]:
        result = await self.db.execute(
            select(FraudRule).where(FraudRule.is_active == True)
        )
        return result.scalars().all()
    
    async def get_by_type(self, rule_type: RuleType) -> List[FraudRule]:
        result = await self.db.execute(
            select(FraudRule).where(
                FraudRule.rule_type == rule_type,
                FraudRule.is_active == True
            )
        )
        return result.scalars().all()
    
    async def get_by_name(self, name: str) -> Optional[FraudRule]:
        result = await self.db.execute(
            select(FraudRule).where(FraudRule.rule_name == name)
        )
        return result.scalar_one_or_none()