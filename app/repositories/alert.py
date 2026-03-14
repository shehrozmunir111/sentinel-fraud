from app.repositories.base import BaseRepository
from app.models.alert import Alert, AlertStatus, AlertSeverity
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from uuid import UUID

class AlertRepository(BaseRepository[Alert]):
    def __init__(self, db: AsyncSession):
        super().__init__(Alert, db)
    
    async def get_by_transaction(self, transaction_id: UUID) -> List[Alert]:
        result = await self.db.execute(
            select(Alert).where(Alert.transaction_id == transaction_id)
        )
        return result.scalars().all()
    
    async def get_open_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        query = select(Alert).where(Alert.status == AlertStatus.OPEN)
        if severity:
            query = query.where(Alert.severity == severity)
        query = query.order_by(desc(Alert.created_at))
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_assigned_to_user(self, user_id: UUID) -> List[Alert]:
        result = await self.db.execute(
            select(Alert)
            .where(Alert.assigned_to == user_id)
            .order_by(desc(Alert.created_at))
        )
        return result.scalars().all()
    
    async def resolve_alert(self, alert_id: UUID, notes: str) -> Optional[Alert]:
        from datetime import datetime
        return await self.update(alert_id, {
            "status": AlertStatus.RESOLVED,
            "resolution_notes": notes,
            "resolved_at": datetime.utcnow()
        })