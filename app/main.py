from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import structlog
from contextlib import asynccontextmanager
import redis.asyncio as redis

from app.core.config import settings
from app.core.exceptions import SentinelException, sentinel_exception_handler
from app.core.logging import configure_logging
from app.core.middleware import SecurityHeadersMiddleware, AuditLogMiddleware
from app.api.v1 import api_router
from app.db.base import engine

# Professional Logging Initialization
configure_logging()
logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing SentinelFraud", environment=settings.ENVIRONMENT)
    async with engine.begin() as conn:
        await conn.exec_driver_sql("SELECT 1")
    yield
    logger.info("Shutting down SentinelFraud")
    await engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="SentinelFraud: Advanced Real-time Fraud Detection System",
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_DOCS else None,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS if not settings.DEBUG else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AuditLogMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.exception_handler(SentinelException)
async def custom_exception_handler(request: Request, exc: SentinelException):
    return await sentinel_exception_handler(request, exc)

@app.get("/health", tags=["System"])
async def health_check():
    dependencies = {"database": "down", "redis": "down"}

    try:
        async with engine.begin() as conn:
            await conn.exec_driver_sql("SELECT 1")
        dependencies["database"] = "up"
    except Exception:
        logger.exception("database_health_check_failed")

    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
    )
    try:
        await redis_client.ping()
        dependencies["redis"] = "up"
    except Exception:
        logger.exception("redis_health_check_failed")
    finally:
        await redis_client.aclose()

    overall_status = "healthy" if all(status == "up" for status in dependencies.values()) else "degraded"
    return {
        "status": overall_status,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "dependencies": dependencies,
    }

@app.get("/", include_in_schema=False)
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "operational",
        "documentation": "/docs",
        "capabilities": [
            "real_time_scoring",
            "ml_detection",
            "velocity_checks",
            "websocket_alerting",
        ],
    }

app.include_router(api_router, prefix="/api/v1")
