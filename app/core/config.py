from typing import List, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Professional Configuration Base
    PROJECT_NAME: str = "SentinelFraud"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # Auth & Security Configuration
    SECRET_KEY: str = "change-me-in-env"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 11520
    
    # PostgreSQL Configuration
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""
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
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 0
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1", "testserver"]
    ENABLE_DOCS: bool = True
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @field_validator("BACKEND_CORS_ORIGINS", "ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_list_env(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def finalize_settings(self):
        if not self.DATABASE_URI:
            auth = self.POSTGRES_USER
            if self.POSTGRES_PASSWORD:
                auth = f"{auth}:{self.POSTGRES_PASSWORD}"
            self.DATABASE_URI = (
                f"postgresql+asyncpg://{auth}"
                f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )

        if self.ENVIRONMENT.lower() == "production" and self.SECRET_KEY == "change-me-in-env":
            raise ValueError("SECRET_KEY must be set explicitly in production")

        if self.ENVIRONMENT.lower() == "production" and not self.BACKEND_CORS_ORIGINS:
            raise ValueError("BACKEND_CORS_ORIGINS must be configured in production")

        return self

settings = Settings()
