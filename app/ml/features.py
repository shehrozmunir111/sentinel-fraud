"""
SentinelFraud ML Feature Engineering
Dataset: Kaggle Credit Card Fraud Detection compatible features
"""

import math
from datetime import datetime, timezone
from typing import Optional


FEATURE_NAMES = [
    "tx_amount",
    "tx_amount_log",
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    "is_night",            # 00-06
    "avg_amount_30d",
    "amount_to_avg_ratio",
    "time_since_last_tx",  # seconds
    "is_international",
    "is_new_device",
    "is_high_risk_country",
    "merchant_category_encoded",
    "currency_encoded",
    "card_velocity_1h",
    "user_velocity_1h",
]


def extract_features(
    amount: float,
    timestamp: datetime,
    avg_amount_30d: float,
    time_since_last_tx_seconds: float,
    is_international: bool,
    is_new_device: bool,
    is_high_risk_country: bool,
    merchant_category: Optional[str],
    currency: str,
    card_velocity_1h: int,
    user_velocity_1h: int,
) -> list[float]:
    """
    Extract a fixed-length feature vector for ML inference.
    """
    hour = timestamp.hour
    dow = timestamp.weekday()
    is_weekend = 1.0 if dow >= 5 else 0.0
    is_night = 1.0 if hour < 6 else 0.0

    amount_to_avg = (amount / avg_amount_30d) if avg_amount_30d > 0 else 1.0
    amount_log = math.log1p(amount)

    # Simple ordinal encoding for merchant category
    category_map = {
        "grocery": 1, "gas_station": 2, "restaurant": 3, "travel": 4,
        "online": 5, "atm": 6, "entertainment": 7, "retail": 8,
        "healthcare": 9, "utilities": 10,
    }
    cat_encoded = float(category_map.get((merchant_category or "").lower(), 0))

    currency_map = {"USD": 1, "EUR": 2, "GBP": 3, "JPY": 4, "CAD": 5}
    curr_encoded = float(currency_map.get(currency.upper(), 0))

    # Cap time_since_last_tx to 7 days (604800 seconds)
    tslt = min(time_since_last_tx_seconds, 604800)

    return [
        float(amount),
        amount_log,
        float(hour),
        float(dow),
        is_weekend,
        is_night,
        float(avg_amount_30d),
        float(amount_to_avg),
        float(tslt),
        1.0 if is_international else 0.0,
        1.0 if is_new_device else 0.0,
        1.0 if is_high_risk_country else 0.0,
        cat_encoded,
        curr_encoded,
        float(card_velocity_1h),
        float(user_velocity_1h),
    ]
