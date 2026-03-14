import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime

class FeatureExtractor:
    def __init__(self):
        self.feature_names = [
            'amount', 'hour', 'day_of_week', 'amount_ratio_30d',
            'is_international', 'has_device_fp', 'is_high_amount',
            'velocity_1h', 'merchant_risk_score'
        ]
    
    def extract_features(self, transaction: Dict, historical: List[Dict]) -> np.ndarray:
        tx_time = transaction['timestamp']
        if isinstance(tx_time, str):
            tx_time = datetime.fromisoformat(tx_time.replace('Z', '+00:00'))
        
        hour = tx_time.hour
        day_of_week = tx_time.weekday()
        
        amount = float(transaction['amount'])
        avg_30d = np.mean([float(h['amount']) for h in historical[-30:]]) if historical else amount
        amount_ratio = amount / avg_30d if avg_30d > 0 else 1.0
        
        is_international = 1 if transaction.get('country_code') != 'US' else 0
        has_device = 1 if transaction.get('device_fingerprint') else 0
        is_high = 1 if amount > 10000 else 0
        
        one_hour_ago = tx_time - pd.Timedelta(hours=1)
        velocity = sum(1 for h in historical if isinstance(h['timestamp'], datetime) and h['timestamp'] > one_hour_ago)
        
        merchant_risk = 0.5
        
        return np.array([
            amount, hour, day_of_week, amount_ratio,
            is_international, has_device, is_high,
            velocity, merchant_risk
        ])