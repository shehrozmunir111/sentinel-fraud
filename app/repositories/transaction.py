from app.repositories.base import BaseRepository
from app.models.transaction import Transaction
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from datetime import datetime, timedelta
from typing import List, Optional

class TransactionRepository(BaseRepository[Transaction]):
    def __init__(self, db: AsyncSession):
        super().__init__(Transaction, db)
    
    async def get_by_transaction_id(self, tx_id: str) -> Optional[Transaction]:
        result = await self.db.execute(
            select(Transaction).where(Transaction.transaction_id == tx_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_transactions_last_hours(
        self, user_id: str, hours: int = 1
    ) -> List[Transaction]:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        result = await self.db.execute(
            select(Transaction)
            .where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.timestamp >= cutoff
                )
            )
            .order_by(Transaction.timestamp.desc())
        )
        return result.scalars().all()
    
    async def get_card_transactions_last_hours(
        self, card_id: str, hours: int = 1
    ) -> List[Transaction]:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        result = await self.db.execute(
            select(Transaction)
            .where(
                and_(
                    Transaction.card_id == card_id,
                    Transaction.timestamp >= cutoff
                )
            )
        )
        return result.scalars().all()
    
    async def get_user_average_amount_30d(self, user_id: str) -> float:
        cutoff = datetime.utcnow() - timedelta(days=30)
        result = await self.db.execute(
            select(func.avg(Transaction.amount))
            .where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.timestamp >= cutoff
                )
            )
        )
        avg = result.scalar()
        return float(avg) if avg else 0.0