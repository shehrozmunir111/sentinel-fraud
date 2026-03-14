from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict
from decimal import Decimal
from datetime import datetime
from uuid import UUID
from enum import Enum

class Decision(str, Enum):
    APPROVE = "approve"
    DECLINE = "decline"
    REVIEW = "review"
    PENDING = "pending"

class TransactionBase(BaseModel):
    transaction_id: str = Field(..., min_length=1, max_length=100)
    card_id: str = Field(..., min_length=1, max_length=100)
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    merchant_id: str = Field(..., min_length=1, max_length=100)
    merchant_category: Optional[str] = Field(None, max_length=50)
    country_code: str = Field(..., min_length=2, max_length=2)
    city: Optional[str] = Field(None, max_length=100)
    ip_address: Optional[str] = Field(None, max_length=45)
    device_fingerprint: Optional[str] = Field(None, max_length=255)
    timestamp: datetime

class TransactionCreate(TransactionBase):
    user_id: UUID
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v > Decimal('999999999.99'):
            raise ValueError('Amount exceeds maximum limit')
        return v

class TransactionResponse(TransactionBase):
    id: UUID
    user_id: UUID
    risk_score: int
    decision: Decision
    is_fraud: bool
    ml_score: Optional[Decimal]
    created_at: datetime
    
    class Config:
        from_attributes = True

class RiskAssessmentResponse(BaseModel):
    transaction_id: str
    risk_score: int
    decision: Decision
    ml_score: float
    rule_contributions: Dict[str, int]
    processing_time_ms: float