from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import os

class Settings(BaseSettings):
    # Professional Configuration Base
    PROJECT_NAME: str = "SentinelFraud"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development" # Default to development for local use
    
    # Auth & Security Configuration
    SECRET_KEY: str = "9e64e10696a1a1f9e80a068019e3498064560a66d55d2898953112104523dd0f"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 11520 # 8 days
    
    # PostgreSQL Configuration (Matching user local DB)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "admin"
    POSTGRES_DB: str = "sentinelfraud"
    DATABASE_URI: Optional[str] = None
    
    # Redis Configuration (Local stack)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # Celery & Background Processing
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # Machine Learning Logic
    MODEL_PATH: str = "./ml/models"
    ML_THRESHOLD: float = 0.7
    
    # System Runtime Constants
    RATE_LIMIT: str = "100/minute"
    WS_HEARTBEAT_INTERVAL: int = 30
    
    # Pydantic Settings Configuration (v2)
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Dynamically constructing Database URI
        self.DATABASE_URI = (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

# Final Settings Object
settings = Settings()