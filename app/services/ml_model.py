"""
SentinelFraud ML Model Service
Loads trained model, runs inference, supports versioning
"""

import logging
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.config import settings
from app.ml.features import extract_features

logger = logging.getLogger(__name__)


class MLModelService:
    """
    Singleton-style service that loads the active model from disk
    and provides predict() for real-time inference.
    """

    def __init__(self):
        self._pipeline = None
        self._model_version: str = "none"
        self._model_path: str = ""

    async def load_model(self, model_path: str, version: str = "unknown") -> bool:
        try:
            with open(model_path, "rb") as f:
                self._pipeline = pickle.load(f)
            self._model_version = version
            self._model_path = model_path
            logger.info("Loaded ML model v%s from %s", version, model_path)
            return True
        except Exception as exc:
            logger.error("Failed to load model from %s: %s", model_path, exc)
            self._pipeline = None
            return False

    @property
    def is_loaded(self) -> bool:
        return self._pipeline is not None

    @property
    def version(self) -> str:
        return self._model_version

    def predict(
        self,
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
    ) -> Optional[float]:
        """
        Returns fraud probability [0, 1] or None if model not loaded.
        Target: <10ms inference.
        """
        if not self.is_loaded:
            return None

        try:
            features = extract_features(
                amount=amount,
                timestamp=timestamp,
                avg_amount_30d=avg_amount_30d,
                time_since_last_tx_seconds=time_since_last_tx_seconds,
                is_international=is_international,
                is_new_device=is_new_device,
                is_high_risk_country=is_high_risk_country,
                merchant_category=merchant_category,
                currency=currency,
                card_velocity_1h=card_velocity_1h,
                user_velocity_1h=user_velocity_1h,
            )
            # Shape: (1, n_features)
            import numpy as np
            X = np.array([features])
            prob = self._pipeline.predict_proba(X)[0][1]
            return float(prob)
        except Exception as exc:
            logger.error("ML prediction failed: %s", exc)
            return None

    def train_and_reload(self, csv_path: Optional[str] = None) -> dict:
        """Synchronous training (called from Celery worker)."""
        from app.ml.trainer import FraudModelTrainer
        import time

        version = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        trainer = FraudModelTrainer(model_dir=settings.ML_MODEL_PATH)
        metrics = trainer.train(csv_path=csv_path, model_version=version)

        # Reload in-process
        import asyncio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.load_model(metrics["model_path"], version))
        loop.close()

        return metrics


# Module-level singleton
ml_model_service = MLModelService()
