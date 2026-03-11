"""
SentinelFraud ORM Models
Stage 3: PostgreSQL, SQLAlchemy, relationships, indexing
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    full_name: Mapped[str | None] = mapped_column(String(200))
    country: Mapped[str | None] = mapped_column(String(3))
    risk_profile: Mapped[str] = mapped_column(String(10), default="low")  # low|medium|high
    role: Mapped[str] = mapped_column(String(20), default="analyst")      # admin|analyst|viewer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="user", lazy="select")
    assigned_alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="assignee", lazy="select")

    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_risk_profile", "risk_profile"),
    )


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------
class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    card_id: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    merchant_id: Mapped[str | None] = mapped_column(String(100))
    merchant_category: Mapped[str | None] = mapped_column(String(100))
    country_code: Mapped[str | None] = mapped_column(String(3))
    city: Mapped[str | None] = mapped_column(String(100))
    ip_address: Mapped[str | None] = mapped_column(String(45))
    device_fingerprint: Mapped[str | None] = mapped_column(String(255))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    decision: Mapped[str] = mapped_column(String(10), default="approve")  # approve|decline|review
    is_fraud: Mapped[bool] = mapped_column(Boolean, default=False)
    ml_score: Mapped[float | None] = mapped_column(Float)
    rule_score: Mapped[int] = mapped_column(Integer, default=0)
    processing_time_ms: Mapped[float | None] = mapped_column(Float)
    raw_features: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped[User | None] = relationship("User", back_populates="transactions")
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="transaction", lazy="select")

    __table_args__ = (
        Index("ix_transactions_transaction_id", "transaction_id"),
        Index("ix_transactions_card_id", "card_id"),
        Index("ix_transactions_user_id", "user_id"),
        Index("ix_transactions_timestamp", "timestamp"),
        Index("ix_transactions_decision", "decision"),
        Index("ix_transactions_is_fraud", "is_fraud"),
        Index("ix_transactions_risk_score", "risk_score"),
        Index("ix_transactions_card_id_timestamp", "card_id", "timestamp"),
    )


# ---------------------------------------------------------------------------
# Fraud Rule
# ---------------------------------------------------------------------------
class FraudRule(Base):
    __tablename__ = "fraud_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    rule_type: Mapped[str] = mapped_column(String(30), nullable=False)  # velocity|amount|geolocation|device
    description: Mapped[str | None] = mapped_column(Text)
    conditions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    risk_weight: Mapped[int] = mapped_column(Integer, default=10)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_fraud_rules_rule_type", "rule_type"),
        Index("ix_fraud_rules_is_active", "is_active"),
    )


# ---------------------------------------------------------------------------
# ML Model Registry
# ---------------------------------------------------------------------------
class MLModelRecord(Base):
    __tablename__ = "ml_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(20), nullable=False)
    model_path: Mapped[str] = mapped_column(String(500), nullable=False)
    algorithm: Mapped[str | None] = mapped_column(String(50))
    accuracy: Mapped[float | None] = mapped_column(Float)
    precision_score: Mapped[float | None] = mapped_column(Float)
    recall_score: Mapped[float | None] = mapped_column(Float)
    f1_score: Mapped[float | None] = mapped_column(Float)
    auc_roc: Mapped[float | None] = mapped_column(Float)
    training_samples: Mapped[int | None] = mapped_column(Integer)
    feature_names: Mapped[list | None] = mapped_column(JSONB)
    hyperparameters: Mapped[dict | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("model_name", "model_version", name="uq_ml_models_name_version"),
        Index("ix_ml_models_is_active", "is_active"),
    )


# ---------------------------------------------------------------------------
# Alert
# ---------------------------------------------------------------------------
class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)  # fraud_detected|high_risk|velocity_breach|etc.
    severity: Mapped[str] = mapped_column(String(10), nullable=False)    # critical|high|medium|low
    status: Mapped[str] = mapped_column(String(20), default="open")      # open|resolved|false_positive
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    transaction: Mapped[Transaction] = relationship("Transaction", back_populates="alerts")
    assignee: Mapped[User | None] = relationship("User", back_populates="assigned_alerts")

    __table_args__ = (
        Index("ix_alerts_transaction_id", "transaction_id"),
        Index("ix_alerts_status", "status"),
        Index("ix_alerts_severity", "severity"),
        Index("ix_alerts_created_at", "created_at"),
    )


# ---------------------------------------------------------------------------
# Audit Log  (Stage 4)
# ---------------------------------------------------------------------------
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(50))
    resource_id: Mapped[str | None] = mapped_column(String(100))
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    payload: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_created_at", "created_at"),
    )
