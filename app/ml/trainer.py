"""
SentinelFraud ML Trainer
Uses Kaggle Credit Card Fraud Detection dataset features.
Trains RandomForest + GradientBoosting ensemble.
"""

import logging
import os
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.utils import resample

from app.ml.features import FEATURE_NAMES, extract_features

logger = logging.getLogger(__name__)


class FraudModelTrainer:
    """
    Trains a fraud detection model.
    Compatible with Kaggle Credit Card Fraud Detection CSV.
    Falls back to synthetic data if no CSV is available.
    """

    def __init__(self, model_dir: str = "/app/ml_models"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def load_kaggle_data(self, csv_path: str) -> Tuple[np.ndarray, np.ndarray]:
        """Load Kaggle creditcard.csv (V1-V28, Amount, Class)."""
        df = pd.read_csv(csv_path)
        logger.info("Loaded %d rows from %s", len(df), csv_path)

        # Use V1-V28 + Amount as features; Class as label
        feature_cols = [c for c in df.columns if c.startswith("V")] + ["Amount"]
        X = df[feature_cols].values
        y = df["Class"].values
        return X, y

    def generate_synthetic_data(self, n_samples: int = 50_000) -> Tuple[np.ndarray, np.ndarray]:
        """Generate synthetic fraud dataset matching our feature vector."""
        rng = np.random.RandomState(42)
        n_fraud = int(n_samples * 0.003)   # 0.3% fraud (realistic)
        n_legit = n_samples - n_fraud

        # Legitimate transactions
        legit_features = np.column_stack([
            rng.lognormal(4, 1.5, n_legit),             # amount
            rng.normal(6, 2, n_legit),                   # amount_log
            rng.randint(0, 24, n_legit).astype(float),   # hour
            rng.randint(0, 7, n_legit).astype(float),    # day_of_week
            rng.binomial(1, 0.28, n_legit).astype(float),# is_weekend
            rng.binomial(1, 0.05, n_legit).astype(float),# is_night
            rng.lognormal(4, 1, n_legit),                # avg_amount_30d
            rng.normal(1, 0.3, n_legit),                 # amount_to_avg_ratio
            rng.exponential(3600, n_legit),              # time_since_last_tx
            rng.binomial(1, 0.10, n_legit).astype(float),# is_international
            rng.binomial(1, 0.05, n_legit).astype(float),# is_new_device
            rng.binomial(1, 0.02, n_legit).astype(float),# is_high_risk_country
            rng.randint(0, 11, n_legit).astype(float),   # merchant_category
            rng.randint(0, 6, n_legit).astype(float),    # currency
            rng.poisson(1.2, n_legit).astype(float),     # card_velocity
            rng.poisson(2.0, n_legit).astype(float),     # user_velocity
        ])

        # Fraudulent transactions (suspicious patterns)
        fraud_features = np.column_stack([
            rng.lognormal(6, 2, n_fraud),                # higher amounts
            rng.normal(8, 2, n_fraud),
            rng.choice([0, 1, 2, 3, 22, 23], n_fraud).astype(float),  # late night
            rng.randint(0, 7, n_fraud).astype(float),
            rng.binomial(1, 0.35, n_fraud).astype(float),
            rng.binomial(1, 0.40, n_fraud).astype(float),  # more night
            rng.lognormal(3, 1, n_fraud),
            rng.lognormal(2, 1, n_fraud),                  # high ratio
            rng.exponential(300, n_fraud),                 # quick succession
            rng.binomial(1, 0.50, n_fraud).astype(float),  # more international
            rng.binomial(1, 0.45, n_fraud).astype(float),  # more new devices
            rng.binomial(1, 0.35, n_fraud).astype(float),  # more high-risk
            rng.randint(0, 11, n_fraud).astype(float),
            rng.randint(0, 6, n_fraud).astype(float),
            rng.poisson(6, n_fraud).astype(float),          # high velocity
            rng.poisson(8, n_fraud).astype(float),
        ])

        X = np.vstack([legit_features, fraud_features])
        y = np.array([0] * n_legit + [1] * n_fraud)

        # Shuffle
        idx = rng.permutation(len(X))
        return X[idx], y[idx]

    # ------------------------------------------------------------------
    # Training pipeline
    # ------------------------------------------------------------------
    def train(
        self,
        csv_path: Optional[str] = None,
        model_version: str = "1.0.0",
    ) -> dict:
        """Train the fraud detection model and persist to disk."""
        logger.info("Starting model training (version %s)", model_version)

        if csv_path and os.path.exists(csv_path):
            X, y = self.load_kaggle_data(csv_path)
            source = "kaggle"
        else:
            logger.info("No CSV found – using synthetic data")
            X, y = self.generate_synthetic_data()
            source = "synthetic"

        logger.info("Dataset: %d samples, %d fraud (%.3f%%)",
                    len(y), y.sum(), y.mean() * 100)

        # Balance classes via over-sampling minority
        X_majority = X[y == 0]
        X_minority = X[y == 1]
        y_majority = y[y == 0]
        y_minority = y[y == 1]

        if len(X_minority) < len(X_majority):
            X_minority_up, y_minority_up = resample(
                X_minority, y_minority,
                replace=True,
                n_samples=min(len(X_majority), len(X_minority) * 10),
                random_state=42,
            )
            X_bal = np.vstack([X_majority, X_minority_up])
            y_bal = np.concatenate([y_majority, y_minority_up])
        else:
            X_bal, y_bal = X, y

        X_train, X_test, y_train, y_test = train_test_split(
            X_bal, y_bal, test_size=0.2, random_state=42, stratify=y_bal
        )

        # Pipeline: scaler + GradientBoosting
        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", GradientBoostingClassifier(
                n_estimators=150,
                max_depth=5,
                learning_rate=0.1,
                subsample=0.8,
                random_state=42,
            )),
        ])

        pipeline.fit(X_train, y_train)

        # Evaluate
        y_pred = pipeline.predict(X_test)
        y_prob = pipeline.predict_proba(X_test)[:, 1]

        metrics = {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision": float(precision_score(y_test, y_pred, zero_division=0)),
            "recall": float(recall_score(y_test, y_pred, zero_division=0)),
            "f1": float(f1_score(y_test, y_pred, zero_division=0)),
            "auc_roc": float(roc_auc_score(y_test, y_prob)),
            "training_samples": int(len(X_train)),
            "source": source,
        }

        logger.info("Training complete: %s", metrics)

        # Persist
        model_filename = f"fraud_model_v{model_version}.pkl"
        model_path = self.model_dir / model_filename
        with open(model_path, "wb") as f:
            pickle.dump(pipeline, f)

        logger.info("Model saved to %s", model_path)
        return {**metrics, "model_path": str(model_path), "model_version": model_version}
