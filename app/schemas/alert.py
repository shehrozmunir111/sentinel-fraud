from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.models.alert import AlertStatus, AlertSeverity

class AlertBase(BaseModel):
    transaction_id: UUID
    alert_type: str = Field(..., max_length=50)
    severity: AlertSeverity
    description: Optional[str] = Field(None, max_length=1000)

class AlertCreate(AlertBase):
    assigned_to: Optional[UUID] = None

class AlertUpdate(BaseModel):
    status: AlertStatus
    resolution_notes: Optional[str] = None

class AlertResponse(AlertBase):
    id: UUID
    status: AlertStatus
    assigned_to: Optional[UUID]
    resolution_notes: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]
    
    class Config:
        from_attributes = True