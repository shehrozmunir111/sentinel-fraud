from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import BaseModel
import enum

class AlertStatus(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"

class AlertSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Alert(BaseModel):
    __tablename__ = "alerts"
    
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)
    severity = Column(Enum(AlertSeverity), nullable=False)
    status = Column(Enum(AlertStatus), default=AlertStatus.OPEN)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    description = Column(String(1000))
    resolution_notes = Column(String(1000))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))
    
    __table_args__ = (
        Index('idx_alert_status_created', 'status', 'created_at'),
        Index('idx_alert_severity', 'severity'),
        Index('idx_alert_assigned', 'assigned_to', 'status'),
    )