from app.repositories.alert import AlertRepository
from app.repositories.transaction import TransactionRepository
from app.models.alert import AlertSeverity, AlertStatus
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from app.services.websocket import websocket_manager

class AlertService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.alert_repo = AlertRepository(db)
        self.tx_repo = TransactionRepository(db)
    
    async def create_alert(
        self,
        transaction_id: str,
        alert_type: str,
        severity: str,
        description: str = "",
        assigned_to: Optional[UUID] = None
    ) -> dict:
        tx = await self.tx_repo.get_by_transaction_id(transaction_id)
        if not tx:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        alert_data = {
            "transaction_id": tx.id,
            "alert_type": alert_type,
            "severity": AlertSeverity(severity),
            "description": description,
            "status": AlertStatus.OPEN,
            "assigned_to": assigned_to
        }
        
        alert = await self.alert_repo.create(alert_data)
        
        await websocket_manager.broadcast_fraud_alert({
            "alert_id": str(alert.id),
            "transaction_id": transaction_id,
            "type": alert_type,
            "severity": severity,
            "amount": str(tx.amount),
            "merchant": tx.merchant_id,
            "timestamp": tx.timestamp.isoformat() if tx.timestamp else None
        })
        
        return {
            "id": str(alert.id),
            "transaction_id": transaction_id,
            "status": "created",
            "severity": severity
        }
    
    async def assign_alert(self, alert_id: UUID, user_id: UUID) -> dict:
        updated = await self.alert_repo.update(alert_id, {
            "assigned_to": user_id
        })
        return {"id": str(alert_id), "assigned_to": str(user_id), "status": "assigned"}
    
    async def resolve_alert(self, alert_id: UUID, notes: str, is_false_positive: bool = False) -> dict:
        status = AlertStatus.FALSE_POSITIVE if is_false_positive else AlertStatus.RESOLVED
        updated = await self.alert_repo.update(alert_id, {
            "status": status,
            "resolution_notes": notes
        })
        return {"id": str(alert_id), "status": status.value, "resolved": True}
    
    async def notify_dashboard(self, message: dict):
        await websocket_manager.broadcast_fraud_alert(message)