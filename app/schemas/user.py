from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.models.user import RiskProfile

class UserBase(BaseModel):
    email: EmailStr
    phone: Optional[str] = None
    country: Optional[str] = Field(None, min_length=2, max_length=2)
    risk_profile: RiskProfile = RiskProfile.LOW

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserResponse(UserBase):
    id: UUID
    is_active: str
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"