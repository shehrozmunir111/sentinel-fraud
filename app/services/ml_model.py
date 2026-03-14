import joblib
import numpy as np
from typing import List, Dict, Optional
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
import pandas as pd
from datetime import datetime
from app.core.config import settings
from app.repositories.transaction import TransactionRepository
from sqlalchemy.ext.asyncio import AsyncSession

class MLModelService:
    def __init__(self):
        self.model = None
        self.model_path = Path(settings.MODEL_PATH)
        self.model_path.mkdir(parents=True, exist_ok=True)
        self.load_active_model()
    
    def load_active_model(self):
        try:
            model_file = self.model_path / "fraud_model_v1.pkl"
            if model_file.exists():
                self.model = joblib.load(model_file)
        except Exception as e:
            self.model = None
    
    async def extract_features(
        self, 
        transaction: dict,
        db: AsyncSession
    ) -> np.ndarray:
        tx_time = transaction['timestamp']
        if isinstance(tx_time, str):
            tx_time = datetime.fromisoformat(tx_time.replace('Z', '+00:00'))
        
        hour = tx_time.hour
        day_of_week = tx_time.weekday()
        
        tx_repo = TransactionRepository(db)
        user_id = transaction['user_id']
        
        avg_amount_30d = await tx_repo.get_user_average_amount_30d(str(user_id))
        current_amount = float(transaction['amount'])
        
        amount_ratio = current_amount / avg_amount_30d if avg_amount_30d > 0 else 1.0
        
        features = [
            current_amount,
            hour,
            day_of_week,
            amount_ratio,
            1 if transaction['country_code'] != 'US' else 0,
            len(transaction.get('device_fingerprint', '')) > 0,
            1 if current_amount > 10000 else 0,
        ]
        
        return np.array(features).reshape(1, -1)
    
    async def predict(self, features: np.ndarray) -> float:
        if self.model is None:
            amount = features[0][0]
            if amount > 50000:
                return 0.9
            elif amount > 10000:
                return 0.5
            return 0.1
        
        try:
            if hasattr(self.model, 'predict_proba'):
                prob = self.model.predict_proba(features)[0][1]
            else:
                pred = self.model.predict(features)[0]
                prob = 0.9 if pred == -1 else 0.1
            return float(prob)
        except Exception:
            return 0.5
    
    def train_model(self, X: np.ndarray, y: np.ndarray) -> Dict:
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
        model.fit(X, y)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"fraud_model_{timestamp}.pkl"
        filepath = self.model_path / filename
        joblib.dump(model, filepath)
        
        joblib.dump(model, self.model_path / "fraud_model_v1.pkl")
        
        return {
            "model_path": str(filepath),
            "accuracy": model.score(X, y),
            "feature_importances": model.feature_importances_.tolist()
        }