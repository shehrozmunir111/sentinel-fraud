from sqlalchemy import Column, String, DateTime, Enum, Index
from sqlalchemy.sql import func
from app.db.base import BaseModel
import enum

class RiskProfile(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class User(BaseModel):
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(50))
    country = Column(String(2))
    risk_profile = Column(Enum(RiskProfile), default=RiskProfile.LOW)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(String(1), default="Y")
    role = Column(String(50), default="analyst")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_user_email_active', 'email', 'is_active'),
        Index('idx_user_risk_profile', 'risk_profile'),
    )