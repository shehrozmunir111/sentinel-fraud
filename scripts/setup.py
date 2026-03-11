#!/usr/bin/env python3
"""
SentinelFraud Startup Script
Seeds default fraud rules and trains initial ML model.
Run once after first deployment.

Usage: python scripts/setup.py
"""

import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("setup")

DEFAULT_RULES = [
    {
        "rule_name": "card_velocity_check",
        "rule_type": "velocity",
        "description": "Card used more than 5 times in 1 hour",
        "conditions": {"entity": "card", "window": "1h", "limit": 5},
        "risk_weight": 30,
        "is_active": True,
    },
    {
        "rule_name": "user_velocity_check",
        "rule_type": "velocity",
        "description": "User made more than 10 transactions in 1 hour",
        "conditions": {"entity": "user", "window": "1h", "limit": 10},
        "risk_weight": 20,
        "is_active": True,
    },
    {
        "rule_name": "device_velocity_check",
        "rule_type": "velocity",
        "description": "Device used more than 20 times in 1 hour",
        "conditions": {"entity": "device", "window": "1h", "limit": 20},
        "risk_weight": 40,
        "is_active": True,
    },
    {
        "rule_name": "high_amount",
        "rule_type": "amount",
        "description": "Transaction amount exceeds $10,000",
        "conditions": {"threshold": 10000, "currency": "USD"},
        "risk_weight": 25,
        "is_active": True,
    },
    {
        "rule_name": "very_high_amount",
        "rule_type": "amount",
        "description": "Transaction amount exceeds $50,000",
        "conditions": {"threshold": 50000, "currency": "USD"},
        "risk_weight": 50,
        "is_active": True,
    },
    {
        "rule_name": "amount_spike",
        "rule_type": "amount",
        "description": "Transaction is 10x the 30-day average",
        "conditions": {"multiplier": 10, "window": "30d"},
        "risk_weight": 35,
        "is_active": True,
    },
    {
        "rule_name": "high_risk_country",
        "rule_type": "geolocation",
        "description": "Transaction from a sanctioned/high-risk country",
        "conditions": {"countries": ["KP", "IR", "SY", "CU", "VE", "MM"]},
        "risk_weight": 30,
        "is_active": True,
    },
    {
        "rule_name": "impossible_travel",
        "rule_type": "geolocation",
        "description": "Different countries within 2 hours",
        "conditions": {"window": "2h", "different_country": True},
        "risk_weight": 60,
        "is_active": True,
    },
    {
        "rule_name": "new_country",
        "rule_type": "geolocation",
        "description": "First transaction in a new country",
        "conditions": {"check": "first_in_country"},
        "risk_weight": 15,
        "is_active": True,
    },
    {
        "rule_name": "new_device",
        "rule_type": "device",
        "description": "Transaction from unrecognized device",
        "conditions": {"check": "new_device_fingerprint"},
        "risk_weight": 20,
        "is_active": True,
    },
]


async def seed_rules():
    from app.database import AsyncSessionLocal, init_db
    from app.repositories import FraudRuleRepository

    await init_db()
    async with AsyncSessionLocal() as session:
        repo = FraudRuleRepository(session)
        existing, _ = await repo.get_list(limit=100)
        existing_names = {r.rule_name for r in existing}

        seeded = 0
        for rule in DEFAULT_RULES:
            if rule["rule_name"] not in existing_names:
                await repo.create(rule)
                seeded += 1
        await session.commit()
        logger.info("Seeded %d fraud rules", seeded)


async def train_initial_model():
    from app.ml.trainer import FraudModelTrainer
    from app.services.ml_model import ml_model_service
    from datetime import datetime, timezone

    version = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    trainer = FraudModelTrainer()
    
    logger.info("Training initial ML model (synthetic data)...")
    metrics = trainer.train(model_version=version)
    logger.info("Training complete: accuracy=%.4f, auc=%.4f", 
                metrics["accuracy"], metrics["auc_roc"])

    await ml_model_service.load_model(metrics["model_path"], version)
    logger.info("Model loaded into memory: v%s", version)
    return metrics


async def main():
    logger.info("=== SentinelFraud Setup ===")
    
    try:
        logger.info("Seeding fraud rules...")
        await seed_rules()
    except Exception as exc:
        logger.error("Failed to seed rules: %s", exc)

    try:
        logger.info("Training initial ML model...")
        await train_initial_model()
    except Exception as exc:
        logger.error("Failed to train model: %s", exc)

    logger.info("✅ Setup complete!")


if __name__ == "__main__":
    asyncio.run(main())
