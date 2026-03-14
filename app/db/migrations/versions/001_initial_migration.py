"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('fraud_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rule_name', sa.String(length=100), nullable=False),
        sa.Column('rule_type', sa.Enum('VELOCITY', 'AMOUNT', 'GEOLOCATION', 'DEVICE', name='ruletype'), nullable=False),
        sa.Column('conditions', sa.JSON(), nullable=False),
        sa.Column('risk_weight', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rule_name')
    )
    
    op.create_table('ml_models',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('model_version', sa.String(length=20), nullable=False),
        sa.Column('model_path', sa.String(length=500), nullable=False),
        sa.Column('accuracy', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('precision_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('recall_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('f1_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('feature_schema', sa.String(length=1000), nullable=True),
        sa.Column('trained_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('country', sa.String(length=2), nullable=True),
        sa.Column('risk_profile', sa.Enum('LOW', 'MEDIUM', 'HIGH', name='riskprofile'), nullable=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.String(length=1), nullable=True),
        sa.Column('role', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    
    op.create_index('idx_user_email_active', 'users', ['email', 'is_active'], unique=False)
    op.create_index('idx_user_risk_profile', 'users', ['risk_profile'], unique=False)
    
    op.create_table('transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_id', sa.String(length=100), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('card_id', sa.String(length=100), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('merchant_id', sa.String(length=100), nullable=False),
        sa.Column('merchant_category', sa.String(length=50), nullable=True),
        sa.Column('country_code', sa.String(length=2), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('device_fingerprint', sa.String(length=255), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('risk_score', sa.Integer(), nullable=True),
        sa.Column('decision', sa.String(length=20), nullable=True),
        sa.Column('is_fraud', sa.Boolean(), nullable=True),
        sa.Column('ml_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('rule_scores', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('transaction_id')
    )
    
    op.create_index('idx_tx_card_timestamp', 'transactions', ['card_id', 'timestamp'], unique=False)
    op.create_index('idx_tx_decision_created', 'transactions', ['decision', 'created_at'], unique=False)
    op.create_index('idx_tx_device_timestamp', 'transactions', ['device_fingerprint', 'timestamp'], unique=False)
    op.create_index('idx_tx_fraud_created', 'transactions', ['is_fraud', 'created_at'], unique=False)
    op.create_index('idx_tx_merchant_amount', 'transactions', ['merchant_id', 'amount'], unique=False)
    op.create_index('idx_tx_merchant_id', 'transactions', ['merchant_id'], unique=False)
    op.create_index('idx_tx_transaction_id', 'transactions', ['transaction_id'], unique=False)
    op.create_index('idx_tx_user_id', 'transactions', ['user_id'], unique=False)
    op.create_index('idx_tx_user_timestamp', 'transactions', ['user_id', 'timestamp'], unique=False)
    op.create_index('idx_tx_timestamp', 'transactions', ['timestamp'], unique=False)
    
    op.create_table('alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='alertseverity'), nullable=False),
        sa.Column('status', sa.Enum('OPEN', 'RESOLVED', 'FALSE_POSITIVE', name='alertstatus'), nullable=True),
        sa.Column('assigned_to', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('resolution_notes', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], ),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_alert_assigned', 'alerts', ['assigned_to', 'status'], unique=False)
    op.create_index('idx_alert_severity', 'alerts', ['severity'], unique=False)
    op.create_index('idx_alert_status_created', 'alerts', ['status', 'created_at'], unique=False)
    op.create_index('idx_alert_transaction_id', 'alerts', ['transaction_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_alert_transaction_id', table_name='alerts')
    op.drop_index('idx_alert_status_created', table_name='alerts')
    op.drop_index('idx_alert_severity', table_name='alerts')
    op.drop_index('idx_alert_assigned', table_name='alerts')
    op.drop_table('alerts')
    
    op.drop_index('idx_tx_timestamp', table_name='transactions')
    op.drop_index('idx_tx_user_timestamp', table_name='transactions')
    op.drop_index('idx_tx_user_id', table_name='transactions')
    op.drop_index('idx_tx_transaction_id', table_name='transactions')
    op.drop_index('idx_tx_merchant_id', table_name='transactions')
    op.drop_index('idx_tx_merchant_amount', table_name='transactions')
    op.drop_index('idx_tx_fraud_created', table_name='transactions')
    op.drop_index('idx_tx_decision_created', table_name='transactions')
    op.drop_index('idx_tx_device_timestamp', table_name='transactions')
    op.drop_index('idx_tx_card_timestamp', table_name='transactions')
    op.drop_table('transactions')
    
    op.drop_index('idx_user_risk_profile', table_name='users')
    op.drop_index('idx_user_email_active', table_name='users')
    op.drop_table('users')
    
    op.drop_table('ml_models')
    op.drop_table('fraud_rules')