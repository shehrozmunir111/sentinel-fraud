from sqlalchemy import Column, String, Numeric, Boolean, DateTime
from sqlalchemy.sql import func
from app.db.base import BaseModel

class MLModel(BaseModel):
    __tablename__ = "ml_models"
    
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(20), nullable=False)
    model_path = Column(String(500), nullable=False)
    accuracy = Column(Numeric(5, 4))
    precision_score = Column(Numeric(5, 4))
    recall_score = Column(Numeric(5, 4))
    f1_score = Column(Numeric(5, 4))
    is_active = Column(Boolean, default=False)
    feature_schema = Column(String(1000))
    trained_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())