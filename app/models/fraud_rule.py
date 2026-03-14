from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, Enum
from sqlalchemy.sql import func
from app.db.base import BaseModel
import enum

class RuleType(str, enum.Enum):
    VELOCITY = "velocity"
    AMOUNT = "amount"
    GEOLOCATION = "geolocation"
    DEVICE = "device"

class FraudRule(BaseModel):
    __tablename__ = "fraud_rules"
    
    rule_name = Column(String(100), nullable=False, unique=True)
    rule_type = Column(Enum(RuleType), nullable=False)
    conditions = Column(JSON, nullable=False)
    risk_weight = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    description = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())