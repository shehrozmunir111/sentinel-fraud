"""
SentinelFraud Pydantic Schemas
Stage 1: Validation | Stage 5: Pagination, filtering, sorting
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

DataT = TypeVar("DataT")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class RiskProfile(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Decision(str, Enum):
    approve = "approve"
    decline = "decline"
    review = "review"


class AlertSeverity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class AlertStatus(str, Enum):
    open = "open"
    resolved = "resolved"
    false_positive = "false_positive"


class RuleType(str, Enum):
    velocity = "velocity"
    amount = "amount"
    geolocation = "geolocation"
    device = "device"


class UserRole(str, Enum):
    admin = "admin"
    analyst = "analyst"
    viewer = "viewer"


# ---------------------------------------------------------------------------
# Pagination  (Stage 5)
# ---------------------------------------------------------------------------
class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = None
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PagedResponse(BaseModel, Generic[DataT]):
    data: List[DataT]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def build(cls, data: list, total: int, page: int, page_size: int):
        total_pages = max(1, (total + page_size - 1) // page_size)
        return cls(
            data=data,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )


# ---------------------------------------------------------------------------
# Auth schemas  (Stage 4)
# ---------------------------------------------------------------------------
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# ---------------------------------------------------------------------------
# User schemas
# ---------------------------------------------------------------------------
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    full_name: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = Field(None, max_length=3)
    role: UserRole = UserRole.analyst


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = Field(None, max_length=3)
    risk_profile: Optional[RiskProfile] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: Optional[str]
    phone: Optional[str]
    country: Optional[str]
    risk_profile: str
    role: str
    is_active: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Transaction schemas
# ---------------------------------------------------------------------------
class TransactionCreate(BaseModel):
    transaction_id: str = Field(min_length=1, max_length=100)
    user_id: Optional[uuid.UUID] = None
    card_id: str = Field(min_length=1, max_length=50)
    amount: float = Field(gt=0, le=1_000_000)
    currency: str = Field(default="USD", max_length=3)
    merchant_id: Optional[str] = Field(None, max_length=100)
    merchant_category: Optional[str] = Field(None, max_length=100)
    country_code: Optional[str] = Field(None, max_length=3)
    city: Optional[str] = Field(None, max_length=100)
    ip_address: Optional[str] = Field(None, max_length=45)
    device_fingerprint: Optional[str] = Field(None, max_length=255)
    timestamp: Optional[datetime] = None

    @field_validator("currency")
    @classmethod
    def currency_upper(cls, v: str) -> str:
        return v.upper()

    @field_validator("country_code")
    @classmethod
    def country_upper(cls, v: Optional[str]) -> Optional[str]:
        return v.upper() if v else v


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: str
    user_id: Optional[uuid.UUID]
    card_id: str
    amount: float
    currency: str
    merchant_id: Optional[str]
    merchant_category: Optional[str]
    country_code: Optional[str]
    city: Optional[str]
    risk_score: int
    decision: str
    is_fraud: bool
    ml_score: Optional[float]
    rule_score: int
    processing_time_ms: Optional[float]
    timestamp: datetime
    created_at: datetime


class TransactionFilter(BaseModel):
    decision: Optional[Decision] = None
    is_fraud: Optional[bool] = None
    min_risk_score: Optional[int] = Field(None, ge=0, le=100)
    max_risk_score: Optional[int] = Field(None, ge=0, le=100)
    card_id: Optional[str] = None
    country_code: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Risk scoring schemas
# ---------------------------------------------------------------------------
class RiskScoreResult(BaseModel):
    transaction_id: str
    risk_score: int = Field(ge=0, le=100)
    decision: Decision
    ml_score: Optional[float] = None
    rule_score: int = 0
    rule_triggers: List[str] = []
    processing_time_ms: float
    is_fraud: bool


# ---------------------------------------------------------------------------
# Alert schemas
# ---------------------------------------------------------------------------
class AlertCreate(BaseModel):
    transaction_id: uuid.UUID
    alert_type: str = Field(max_length=50)
    severity: AlertSeverity
    notes: Optional[str] = None


class AlertUpdate(BaseModel):
    status: Optional[AlertStatus] = None
    assigned_to: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    alert_type: str
    severity: str
    status: str
    assigned_to: Optional[uuid.UUID]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Fraud Rule schemas
# ---------------------------------------------------------------------------
class FraudRuleCreate(BaseModel):
    rule_name: str = Field(min_length=1, max_length=100)
    rule_type: RuleType
    description: Optional[str] = None
    conditions: dict[str, Any]
    risk_weight: int = Field(default=10, ge=1, le=100)
    is_active: bool = True


class FraudRuleUpdate(BaseModel):
    description: Optional[str] = None
    conditions: Optional[dict[str, Any]] = None
    risk_weight: Optional[int] = Field(None, ge=1, le=100)
    is_active: Optional[bool] = None


class FraudRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rule_name: str
    rule_type: str
    description: Optional[str]
    conditions: dict
    risk_weight: int
    is_active: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# WebSocket message schemas  (Stage 10)
# ---------------------------------------------------------------------------
class WSMessage(BaseModel):
    event: str
    data: Any
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FraudAlertWSPayload(BaseModel):
    alert_id: str
    transaction_id: str
    risk_score: int
    decision: str
    amount: float
    currency: str
    card_id: str
    country_code: Optional[str]
    alert_type: Optional[str]
    severity: Optional[str]
    timestamp: datetime


# ---------------------------------------------------------------------------
# ML Model registry schemas
# ---------------------------------------------------------------------------
class MLModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_name: str
    model_version: str
    algorithm: Optional[str]
    accuracy: Optional[float]
    precision_score: Optional[float]
    recall_score: Optional[float]
    f1_score: Optional[float]
    auc_roc: Optional[float]
    training_samples: Optional[int]
    is_active: bool
    trained_at: datetime


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------
class DashboardStats(BaseModel):
    total_transactions_24h: int
    fraud_transactions_24h: int
    fraud_rate_24h: float
    total_amount_24h: float
    avg_risk_score_24h: float
    open_alerts: int
    critical_alerts: int
    transactions_per_second: float
