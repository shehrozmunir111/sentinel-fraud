#!/usr/bin/env python3
"""
SentinelFraud Sample Data Generator
Generates realistic transaction data for testing & demos.
Usage: python scripts/generate_sample_data.py
"""

import asyncio
import json
import random
import uuid
from datetime import datetime, timedelta, timezone

import httpx

BASE_URL = "http://localhost:8000/api/v1"

CARDS = [f"CARD_{i:04d}" for i in range(1, 21)]
COUNTRIES = ["US", "GB", "DE", "FR", "CA", "AU", "JP", "BR", "IN", "MX"]
HIGH_RISK = ["KP", "IR", "SY"]
MERCHANTS = ["grocery", "gas_station", "restaurant", "travel", "online", "atm", "entertainment"]
CURRENCIES = ["USD", "EUR", "GBP", "CAD", "JPY"]

rng = random.Random(42)


def random_transaction(fraud_probability: float = 0.01) -> dict:
    is_fraud = rng.random() < fraud_probability
    card_id = rng.choice(CARDS)
    country = rng.choice(HIGH_RISK if is_fraud and rng.random() < 0.3 else COUNTRIES)

    if is_fraud:
        amount = rng.uniform(5000, 50000)
    else:
        amount = rng.lognormvariate(4, 1.5)
        amount = max(1.0, min(amount, 5000))

    return {
        "transaction_id": str(uuid.uuid4()),
        "card_id": card_id,
        "amount": round(amount, 2),
        "currency": rng.choice(CURRENCIES),
        "merchant_id": f"MERCH_{rng.randint(1, 100):03d}",
        "merchant_category": rng.choice(MERCHANTS),
        "country_code": country,
        "city": "Auto",
        "device_fingerprint": f"DEV_{rng.randint(1, 30):03d}",
    }


async def register_and_login(client: httpx.AsyncClient) -> str:
    """Get or create admin user and return JWT token."""
    try:
        resp = await client.post(
            f"{BASE_URL}/auth/register",
            json={
                "email": "demo@sentinel.local",
                "password": "Demo1234!",
                "full_name": "Demo Admin",
                "role": "admin",
            },
        )
    except Exception:
        pass

    resp = await client.post(
        f"{BASE_URL}/auth/login",
        json={"email": "demo@sentinel.local", "password": "Demo1234!"},
    )
    if resp.status_code == 200:
        return resp.json()["access_token"]
    return ""


async def main():
    print("🚀 SentinelFraud Data Generator")
    print("=" * 50)

    async with httpx.AsyncClient(timeout=30) as client:
        token = await register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        total = 100
        fraud_count = 0
        errors = 0

        print(f"Sending {total} transactions...")
        for i in range(total):
            tx = random_transaction(fraud_probability=0.05)
            try:
                resp = await client.post(
                    f"{BASE_URL}/transactions/",
                    json=tx,
                    headers=headers,
                )
                if resp.status_code == 201:
                    result = resp.json()
                    if result["is_fraud"]:
                        fraud_count += 1
                    if (i + 1) % 10 == 0:
                        print(f"  {i+1}/{total} | fraud: {fraud_count} | last_risk: {result['risk_score']} | {result['decision']}")
                else:
                    errors += 1
            except Exception as exc:
                errors += 1

            await asyncio.sleep(0.05)

        print("\n✅ Generation complete!")
        print(f"   Total:  {total}")
        print(f"   Fraud:  {fraud_count}")
        print(f"   Errors: {errors}")


if __name__ == "__main__":
    asyncio.run(main())
