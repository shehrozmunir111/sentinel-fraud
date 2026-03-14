CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

CREATE INDEX IF NOT EXISTS idx_transactions_amount ON transactions(amount) WHERE amount > 10000;
CREATE INDEX IF NOT EXISTS idx_transactions_country ON transactions(country_code) WHERE country_code != 'US';

INSERT INTO users (id, email, hashed_password, role, is_active, risk_profile)
VALUES 
    (uuid_generate_v4(), 'admin@sentinelfraud.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYA.qGZvKG6G', 'admin', 'Y', 'low')
ON CONFLICT (email) DO NOTHING;

INSERT INTO fraud_rules (rule_name, rule_type, conditions, risk_weight, is_active, description)
VALUES 
    ('High Velocity Card', 'velocity', '{"window_hours": 1, "max_count": 5}', 30, true, 'More than 5 transactions per hour on same card'),
    ('High Velocity User', 'velocity', '{"window_hours": 1, "max_count": 10}', 20, true, 'More than 10 transactions per hour per user'),
    ('High Velocity Device', 'velocity', '{"window_hours": 1, "max_count": 20}', 40, true, 'More than 20 transactions per hour per device'),
    ('High Amount 10K', 'amount', '{"min_amount": 10000}', 25, true, 'Transaction amount exceeds $10,000'),
    ('High Amount 50K', 'amount', '{"min_amount": 50000}', 50, true, 'Transaction amount exceeds $50,000'),
    ('Amount Spike', 'amount', '{"multiplier": 10}', 35, true, 'Amount 10x higher than 30-day average'),
    ('High Risk Country', 'geolocation', '{"countries": ["XX", "YY", "ZZ"]}', 30, true, 'Transaction from high-risk country'),
    ('Impossible Travel', 'geolocation', '{"max_hours": 2}', 60, true, 'Transactions from different countries within 2 hours'),
    ('New Country', 'geolocation', '{}', 15, true, 'First transaction from new country')
ON CONFLICT (rule_name) DO NOTHING;