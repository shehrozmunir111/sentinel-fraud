"""Initial schema - SentinelFraud

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(30)),
        sa.Column("full_name", sa.String(200)),
        sa.Column("country", sa.String(3)),
        sa.Column("risk_profile", sa.String(10), default="low"),
        sa.Column("role", sa.String(20), default="analyst"),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("last_login", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_risk_profile", "users", ["risk_profile"])

    # Transactions
    op.create_table(
        "transactions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("transaction_id", sa.String(100), unique=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("card_id", sa.String(50), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("currency", sa.String(3), default="USD"),
        sa.Column("merchant_id", sa.String(100)),
        sa.Column("merchant_category", sa.String(100)),
        sa.Column("country_code", sa.String(3)),
        sa.Column("city", sa.String(100)),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("device_fingerprint", sa.String(255)),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("risk_score", sa.Integer, default=0),
        sa.Column("decision", sa.String(10), default="approve"),
        sa.Column("is_fraud", sa.Boolean, default=False),
        sa.Column("ml_score", sa.Float),
        sa.Column("rule_score", sa.Integer, default=0),
        sa.Column("processing_time_ms", sa.Float),
        sa.Column("raw_features", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_transactions_transaction_id", "transactions", ["transaction_id"])
    op.create_index("ix_transactions_card_id", "transactions", ["card_id"])
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])
    op.create_index("ix_transactions_timestamp", "transactions", ["timestamp"])
    op.create_index("ix_transactions_decision", "transactions", ["decision"])
    op.create_index("ix_transactions_is_fraud", "transactions", ["is_fraud"])
    op.create_index("ix_transactions_card_id_timestamp", "transactions", ["card_id", "timestamp"])
    op.create_index("ix_transactions_risk_score", "transactions", ["risk_score"])

    # Fraud Rules
    op.create_table(
        "fraud_rules",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("rule_name", sa.String(100), unique=True, nullable=False),
        sa.Column("rule_type", sa.String(30), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("conditions", JSONB, nullable=False),
        sa.Column("risk_weight", sa.Integer, default=10),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_fraud_rules_rule_type", "fraud_rules", ["rule_type"])
    op.create_index("ix_fraud_rules_is_active", "fraud_rules", ["is_active"])

    # ML Models
    op.create_table(
        "ml_models",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("model_version", sa.String(20), nullable=False),
        sa.Column("model_path", sa.String(500), nullable=False),
        sa.Column("algorithm", sa.String(50)),
        sa.Column("accuracy", sa.Float),
        sa.Column("precision_score", sa.Float),
        sa.Column("recall_score", sa.Float),
        sa.Column("f1_score", sa.Float),
        sa.Column("auc_roc", sa.Float),
        sa.Column("training_samples", sa.Integer),
        sa.Column("feature_names", JSONB),
        sa.Column("hyperparameters", JSONB),
        sa.Column("is_active", sa.Boolean, default=False),
        sa.Column("trained_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("model_name", "model_version", name="uq_ml_models_name_version"),
    )
    op.create_index("ix_ml_models_is_active", "ml_models", ["is_active"])

    # Alerts
    op.create_table(
        "alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("transaction_id", UUID(as_uuid=True), sa.ForeignKey("transactions.id"), nullable=False),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), default="open"),
        sa.Column("assigned_to", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("notes", sa.Text),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_alerts_transaction_id", "alerts", ["transaction_id"])
    op.create_index("ix_alerts_status", "alerts", ["status"])
    op.create_index("ix_alerts_severity", "alerts", ["severity"])
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"])

    # Audit Logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", UUID(as_uuid=True)),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50)),
        sa.Column("resource_id", sa.String(100)),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.String(500)),
        sa.Column("payload", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("alerts")
    op.drop_table("ml_models")
    op.drop_table("fraud_rules")
    op.drop_table("transactions")
    op.drop_table("users")
