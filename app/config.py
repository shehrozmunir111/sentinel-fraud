"""
SentinelFraud Configuration
Stage 9: Environment config, production hardening
"""

from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # App
    # ------------------------------------------------------------------
    APP_NAME: str = "SentinelFraud"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_use_32+_chars"
    API_VERSION: str = "v1"

    # ------------------------------------------------------------------
    # Server
    # ------------------------------------------------------------------
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    RELOAD: bool = False
    ALLOWED_HOSTS: List[str] = ["*"]
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    # ------------------------------------------------------------------
    # PostgreSQL
    # ------------------------------------------------------------------
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "sentinel_fraud"
    POSTGRES_USER: str = "sentinel"
    POSTGRES_PASSWORD: str = "sentinel_secret"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_TIMEOUT: int = 30
    DB_ECHO: bool = False

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ------------------------------------------------------------------
    # Redis
    # ------------------------------------------------------------------
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_MAX_CONNECTIONS: int = 50
    CACHE_TTL_SECONDS: int = 3600  # 1 hour
    RISK_SCORE_TTL: int = 86400    # 24 hours

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ------------------------------------------------------------------
    # JWT / Auth  (Stage 4)
    # ------------------------------------------------------------------
    JWT_SECRET_KEY: str = "JWT_SECRET_CHANGE_ME_IN_PROD"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ------------------------------------------------------------------
    # Rate Limiting  (Stage 5)
    # ------------------------------------------------------------------
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60   # seconds

    # ------------------------------------------------------------------
    # Celery  (Stage 6)
    # ------------------------------------------------------------------
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: List[str] = ["json"]
    CELERY_TIMEZONE: str = "UTC"

    # ------------------------------------------------------------------
    # ML / Risk Engine
    # ------------------------------------------------------------------
    ML_MODEL_PATH: str = "/app/ml_models"
    ML_MODEL_THRESHOLD: float = 0.5
    RISK_SCORE_FRAUD_THRESHOLD: int = 70
    RISK_SCORE_REVIEW_THRESHOLD: int = 40

    # Velocity thresholds
    CARD_VELOCITY_LIMIT: int = 5     # tx per hour
    USER_VELOCITY_LIMIT: int = 10    # tx per hour
    DEVICE_VELOCITY_LIMIT: int = 20  # tx per hour

    # Amount thresholds
    HIGH_AMOUNT_THRESHOLD: float = 10_000.0
    VERY_HIGH_AMOUNT_THRESHOLD: float = 50_000.0
    AMOUNT_SPIKE_MULTIPLIER: float = 10.0

    # High-risk countries (ISO 3166-1 alpha-2)
    HIGH_RISK_COUNTRIES: List[str] = [
        "KP", "IR", "SY", "CU", "VE", "MM", "AF", "YE", "SO", "LY",
    ]

    # ------------------------------------------------------------------
    # Pagination defaults  (Stage 5)
    # ------------------------------------------------------------------
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
