"""
SentinelFraud - Real-Time Fraud Detection System
Main FastAPI Application Entry Point
Stages: 1 (Async, CORS, Error Handling) + 8 (Docker/Health) + 10 (WebSocket)
"""

import time
import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import init_db, close_db
from app.core.cache import init_redis, close_redis
from app.api.v1.router import api_router
from app.services.websocket_manager import websocket_manager

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("sentinel")


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 SentinelFraud starting up…")
    await init_db()
    await init_redis()
    logger.info("✅ Database and Redis connections established")
    yield
    logger.info("🛑 SentinelFraud shutting down…")
    await close_db()
    await close_redis()


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
def create_app() -> FastAPI:
    app = FastAPI(
        title="SentinelFraud API",
        description="Production-Grade Real-Time Fraud Detection System for Fintech/Payments",
        version="1.0.0",
        docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/api/redoc" if settings.ENVIRONMENT != "production" else None,
        openapi_url="/api/openapi.json" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # -----------------------------------------------------------------------
    # Security middleware
    # -----------------------------------------------------------------------
    if settings.ENVIRONMENT == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS,
        )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )

    # -----------------------------------------------------------------------
    # Request-ID + timing middleware
    # -----------------------------------------------------------------------
    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start = time.perf_counter()
        request.state.request_id = request_id

        response = await call_next(request)

        process_time = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response

    # -----------------------------------------------------------------------
    # Exception handlers
    # -----------------------------------------------------------------------
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "message": exc.detail,
                "request_id": getattr(request.state, "request_id", None),
                "status_code": exc.status_code,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = []
        for err in exc.errors():
            errors.append({
                "field": " -> ".join(str(loc) for loc in err["loc"]),
                "message": err["msg"],
                "type": err["type"],
            })
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": True,
                "message": "Validation failed",
                "errors": errors,
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": True,
                "message": "Internal server error",
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    # -----------------------------------------------------------------------
    # Routers
    # -----------------------------------------------------------------------
    app.include_router(api_router, prefix="/api/v1")

    # -----------------------------------------------------------------------
    # Health / readiness probes  (Stage 8)
    # -----------------------------------------------------------------------
    @app.get("/health", tags=["ops"], summary="Liveness probe")
    async def health():
        return {"status": "ok", "service": "sentinel-fraud", "version": "1.0.0"}

    @app.get("/ready", tags=["ops"], summary="Readiness probe")
    async def readiness():
        from app.database import engine
        from app.core.cache import redis_client

        db_ok = False
        redis_ok = False
        try:
            async with engine.connect() as conn:
                await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            db_ok = True
        except Exception:
            pass

        try:
            await redis_client.ping()
            redis_ok = True
        except Exception:
            pass

        all_ok = db_ok and redis_ok
        return JSONResponse(
            status_code=200 if all_ok else 503,
            content={
                "status": "ready" if all_ok else "degraded",
                "checks": {"database": db_ok, "redis": redis_ok},
            },
        )

    @app.get("/metrics", tags=["ops"], summary="Basic metrics")
    async def metrics():
        return {
            "service": "sentinel-fraud",
            "ws_connections": websocket_manager.connection_count(),
        }

    return app


app = create_app()
