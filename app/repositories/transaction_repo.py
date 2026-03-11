"""
SentinelFraud Transaction Repository
Stage 2: Repository pattern | Stage 3: SQLAlchemy async queries
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction
from app.schemas import TransactionFilter


class TransactionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> Transaction:
        tx = Transaction(**data)
        self.db.add(tx)
        await self.db.flush()
        await self.db.refresh(tx)
        return tx

    async def get_by_id(self, tx_id: uuid.UUID) -> Optional[Transaction]:
        result = await self.db.execute(select(Transaction).where(Transaction.id == tx_id))
        return result.scalar_one_or_none()

    async def get_by_transaction_id(self, transaction_id: str) -> Optional[Transaction]:
        result = await self.db.execute(
            select(Transaction).where(Transaction.transaction_id == transaction_id)
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        filters: TransactionFilter,
        offset: int = 0,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[list[Transaction], int]:
        q = select(Transaction)
        count_q = select(func.count(Transaction.id))

        if filters.decision:
            q = q.where(Transaction.decision == filters.decision.value)
            count_q = count_q.where(Transaction.decision == filters.decision.value)
        if filters.is_fraud is not None:
            q = q.where(Transaction.is_fraud == filters.is_fraud)
            count_q = count_q.where(Transaction.is_fraud == filters.is_fraud)
        if filters.min_risk_score is not None:
            q = q.where(Transaction.risk_score >= filters.min_risk_score)
            count_q = count_q.where(Transaction.risk_score >= filters.min_risk_score)
        if filters.max_risk_score is not None:
            q = q.where(Transaction.risk_score <= filters.max_risk_score)
            count_q = count_q.where(Transaction.risk_score <= filters.max_risk_score)
        if filters.card_id:
            q = q.where(Transaction.card_id == filters.card_id)
            count_q = count_q.where(Transaction.card_id == filters.card_id)
        if filters.country_code:
            q = q.where(Transaction.country_code == filters.country_code)
            count_q = count_q.where(Transaction.country_code == filters.country_code)
        if filters.date_from:
            q = q.where(Transaction.timestamp >= filters.date_from)
            count_q = count_q.where(Transaction.timestamp >= filters.date_from)
        if filters.date_to:
            q = q.where(Transaction.timestamp <= filters.date_to)
            count_q = count_q.where(Transaction.timestamp <= filters.date_to)

        col = getattr(Transaction, sort_by, Transaction.created_at)
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())
        q = q.offset(offset).limit(limit)

        rows = await self.db.execute(q)
        total = await self.db.execute(count_q)
        return list(rows.scalars()), total.scalar_one()

    async def get_card_transactions_last_hour(self, card_id: str) -> int:
        since = datetime.now(timezone.utc) - timedelta(hours=1)
        result = await self.db.execute(
            select(func.count(Transaction.id)).where(
                Transaction.card_id == card_id,
                Transaction.timestamp >= since,
            )
        )
        return result.scalar_one()

    async def get_avg_amount_30d(self, card_id: str) -> float:
        since = datetime.now(timezone.utc) - timedelta(days=30)
        result = await self.db.execute(
            select(func.avg(Transaction.amount)).where(
                Transaction.card_id == card_id,
                Transaction.timestamp >= since,
            )
        )
        avg = result.scalar_one()
        return float(avg) if avg else 0.0

    async def get_last_transaction(self, card_id: str) -> Optional[Transaction]:
        result = await self.db.execute(
            select(Transaction)
            .where(Transaction.card_id == card_id)
            .order_by(Transaction.timestamp.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_risk_score(
        self,
        tx_id: uuid.UUID,
        risk_score: int,
        decision: str,
        is_fraud: bool,
        ml_score: Optional[float],
        rule_score: int,
        processing_time_ms: float,
        raw_features: Optional[dict] = None,
    ) -> None:
        await self.db.execute(
            update(Transaction)
            .where(Transaction.id == tx_id)
            .values(
                risk_score=risk_score,
                decision=decision,
                is_fraud=is_fraud,
                ml_score=ml_score,
                rule_score=rule_score,
                processing_time_ms=processing_time_ms,
                raw_features=raw_features,
            )
        )

    async def get_stats_24h(self) -> dict:
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        rows = await self.db.execute(
            select(
                func.count(Transaction.id).label("total"),
                func.sum(Transaction.amount.cast(float)).label("total_amount"),
                func.avg(Transaction.risk_score).label("avg_risk"),
                func.sum(Transaction.is_fraud.cast(int)).label("fraud_count"),
            ).where(Transaction.timestamp >= since)
        )
        row = rows.one()
        total = row.total or 0
        fraud = row.fraud_count or 0
        return {
            "total_transactions_24h": total,
            "fraud_transactions_24h": fraud,
            "fraud_rate_24h": round(fraud / total * 100, 2) if total else 0.0,
            "total_amount_24h": float(row.total_amount or 0),
            "avg_risk_score_24h": round(float(row.avg_risk or 0), 2),
        }
