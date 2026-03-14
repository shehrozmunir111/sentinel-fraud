from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.fraud_rule import RuleType

class FraudRuleBase(BaseModel):
    rule_name: str = Field(..., min_length=1, max_length=100)
    rule_type: RuleType
    conditions: Dict[str, Any]
    risk_weight: int = Field(default=0, ge=0, le=100)
    is_active: bool = True
    description: Optional[str] = Field(None, max_length=500)

class FraudRuleCreate(FraudRuleBase):
    pass

class FraudRuleResponse(FraudRuleBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True