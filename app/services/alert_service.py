"""
SentinelFraud Alert Service
Stage 2: Service layer pattern
Creates alerts, notifies dashboard via WebSocket
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import AlertRepository
from app.services.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)


class AlertService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AlertRepository(db)

    @staticmethod
    def _determine_alert_type(risk_score: int, rule_triggers: list[str]) -> str:
        if any("impossible_travel" in t for t in rule_triggers):
            return "impossible_travel"
        if any("velocity" in t for t in rule_triggers):
            return "velocity_breach"
        if any("amount" in t for t in rule_triggers):
            return "high_amount"
        if risk_score >= 70:
            return "fraud_detected"
        return "high_risk"

    @staticmethod
    def _determine_severity(risk_score: int) -> str:
        if risk_score >= 85:
            return "critical"
        if risk_score >= 70:
            return "high"
        if risk_score >= 50:
            return "medium"
        return "low"

    async def create_if_needed(
        self,
        transaction_id: uuid.UUID,
        risk_score: int,
        decision: str,
        amount: float,
        currency: str,
        card_id: str,
        country_code: Optional[str],
        rule_triggers: list[str],
        transaction_id_str: str,
    ) -> Optional[dict]:
        """
        Creates alert for review/decline transactions.
        Broadcasts via WebSocket.
        """
        if decision not in ("review", "decline"):
            return None

        alert_type = self._determine_alert_type(risk_score, rule_triggers)
        severity = self._determine_severity(risk_score)

        alert_data = {
            "transaction_id": transaction_id,
            "alert_type": alert_type,
            "severity": severity,
            "status": "open",
        }

        alert = await self.repo.create(alert_data)
        logger.info("Alert created: %s (severity=%s)", alert.id, severity)

        # WebSocket notification
        ws_payload = {
            "alert_id": str(alert.id),
            "transaction_id": transaction_id_str,
            "risk_score": risk_score,
            "decision": decision,
            "amount": amount,
            "currency": currency,
            "card_id": card_id,
            "country_code": country_code,
            "alert_type": alert_type,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        await websocket_manager.broadcast_fraud_alert(ws_payload)

        return {"alert_id": str(alert.id), "severity": severity, "alert_type": alert_type}

    async def resolve_alert(
        self,
        alert_id: uuid.UUID,
        status: str,
        notes: Optional[str] = None,
        assigned_to: Optional[uuid.UUID] = None,
    ):
        data = {
            "status": status,
            "resolved_at": datetime.now(timezone.utc) if status == "resolved" else None,
        }
        if notes:
            data["notes"] = notes
        if assigned_to:
            data["assigned_to"] = assigned_to
        return await self.repo.update(alert_id, data)
