import joblib
from pathlib import Path
from typing import Optional
import numpy as np

class FraudModel:
    def __init__(self, model_path: str):
        self.model_path = Path(model_path)
        self.model = None
        self.load()
    
    def load(self):
        if self.model_path.exists():
            self.model = joblib.load(self.model_path)
    
    def predict(self, features: np.ndarray) -> float:
        if self.model is None:
            return 0.0
        return float(self.model.predict_proba(features.reshape(1, -1))[0][1])
    
    def save(self, path: str):
        joblib.dump(self.model, path)