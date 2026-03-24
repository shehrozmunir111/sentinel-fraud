from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import structlog
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.exceptions import SentinelException, sentinel_exception_handler
from app.core.logging import configure_logging
from app.core.middleware import SecurityHeadersMiddleware, AuditLogMiddleware
from app.api.v1 import api_router
from app.db.base import engine, Base

# Professional Logging Initialization
configure_logging()
logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Database Initialization
    logger.info("Initializing SentinelFraud", environment=settings.ENVIRONMENT)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown: Cleanup
    logger.info("Shutting down SentinelFraud")
    await engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="SentinelFraud: Advanced Real-time Fraud Detection System",
    docs_url="/docs", # Standard path
    redoc_url="/redoc",
    lifespan=lifespan
)

# ─── Professional Middlewares ───
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AuditLogMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ─── Centralized Exception Handling ───
@app.exception_handler(SentinelException)
async def custom_exception_handler(request: Request, exc: SentinelException):
    return await sentinel_exception_handler(request, exc)

# ─── Core Health & Info Endpoints ───
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "operational",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }

@app.get("/", include_in_schema=False)
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "documentation": "/docs"
    }

app.include_router(api_router, prefix="/api/v1")