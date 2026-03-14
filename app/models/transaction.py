from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Integer, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db.base import BaseModel
import enum

class Decision(str, enum.Enum):
    APPROVE = "approve"
    DECLINE = "decline"
    REVIEW = "review"
    PENDING = "pending"

class Transaction(BaseModel):
    __tablename__ = "transactions"
    
    transaction_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    card_id = Column(String(100), nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), default="USD")
    merchant_id = Column(String(100), nullable=False, index=True)
    merchant_category = Column(String(50))
    country_code = Column(String(2), nullable=False, index=True)
    city = Column(String(100))
    ip_address = Column(String(45))
    device_fingerprint = Column(String(255), index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    risk_score = Column(Integer, default=0)
    decision = Column(String(20), default="pending")
    is_fraud = Column(Boolean, default=False)
    ml_score = Column(Numeric(5, 4))
    rule_scores = Column(JSONB, default=dict)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_tx_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_tx_card_timestamp', 'card_id', 'timestamp'),
        Index('idx_tx_device_timestamp', 'device_fingerprint', 'timestamp'),
        Index('idx_tx_merchant_amount', 'merchant_id', 'amount'),
        Index('idx_tx_decision_created', 'decision', 'created_at'),
        Index('idx_tx_fraud_created', 'is_fraud', 'created_at'),
    )