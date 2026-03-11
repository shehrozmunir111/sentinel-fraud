"""
SentinelFraud Celery Workers
Stage 6: Async background tasks, event-driven architecture
Tasks: model training, batch scoring, cleanup, metrics aggregation
"""

import logging
import os
from celery import Celery
from celery.schedules import crontab
from kombu import Queue

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Celery app factory
# ---------------------------------------------------------------------------
celery_app = Celery(
    "sentinel_fraud",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.config_from_object({
    "task_serializer": settings.CELERY_TASK_SERIALIZER,
    "result_serializer": settings.CELERY_RESULT_SERIALIZER,
    "accept_content": settings.CELERY_ACCEPT_CONTENT,
    "timezone": settings.CELERY_TIMEZONE,
    "enable_utc": True,
    "task_track_started": True,
    "task_acks_late": True,
    "worker_prefetch_multiplier": 1,  # fair distribution
    "task_queues": (
        Queue("high_priority"),
        Queue("default"),
        Queue("low_priority"),
    ),
    "task_default_queue": "default",
    "task_routes": {
        "app.workers.celery_app.train_fraud_model": {"queue": "low_priority"},
        "app.workers.celery_app.send_alert_notifications": {"queue": "high_priority"},
        "app.workers.celery_app.aggregate_metrics": {"queue": "low_priority"},
        "app.workers.celery_app.cleanup_expired_cache": {"queue": "low_priority"},
    },
    # Beat scheduler for periodic tasks
    "beat_schedule": {
        "aggregate-metrics-every-minute": {
            "task": "app.workers.celery_app.aggregate_metrics",
            "schedule": 60.0,
        },
        "cleanup-expired-cache-hourly": {
            "task": "app.workers.celery_app.cleanup_expired_cache",
            "schedule": crontab(minute=0),
        },
        "retrain-model-weekly": {
            "task": "app.workers.celery_app.train_fraud_model",
            "schedule": crontab(hour=2, minute=0, day_of_week=0),
        },
    },
})


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------
@celery_app.task(
    bind=True,
    max_retries=3,
    name="app.workers.celery_app.train_fraud_model",
    queue="low_priority",
)
def train_fraud_model(self, csv_path: str = None, version: str = None):
    """
    Background ML model training task.
    Stage 6: Event-driven — triggered via API or on schedule.
    """
    try:
        logger.info("Starting background model training")
        from app.services.ml_model import ml_model_service
        metrics = ml_model_service.train_and_reload(csv_path=csv_path)

        # Persist to DB
        _save_model_to_db(metrics)

        logger.info("Model training complete: %s", metrics)
        return metrics
    except Exception as exc:
        logger.error("Model training failed: %s", exc)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


def _save_model_to_db(metrics: dict):
    """Synchronous DB write from Celery worker."""
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from app.repositories import MLModelRepository

    async def _inner():
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with Session() as session:
            repo = MLModelRepository(session)
            await repo.deactivate_all()
            await repo.create({
                "model_name": "fraud_detector",
                "model_version": metrics["model_version"],
                "model_path": metrics["model_path"],
                "algorithm": "GradientBoosting",
                "accuracy": metrics.get("accuracy"),
                "precision_score": metrics.get("precision"),
                "recall_score": metrics.get("recall"),
                "f1_score": metrics.get("f1"),
                "auc_roc": metrics.get("auc_roc"),
                "training_samples": metrics.get("training_samples"),
                "is_active": True,
            })
            await session.commit()
        await engine.dispose()

    loop = asyncio.new_event_loop()
    loop.run_until_complete(_inner())
    loop.close()


@celery_app.task(
    name="app.workers.celery_app.send_alert_notifications",
    queue="high_priority",
)
def send_alert_notifications(alert_id: str, email_recipients: list[str] = None):
    """
    Send email/webhook notifications for high-severity alerts.
    Stage 6: Event-driven alert dispatch.
    """
    logger.info("Sending notifications for alert %s to %s", alert_id, email_recipients)
    # In production: integrate with SendGrid, Twilio, PagerDuty, etc.
    return {"alert_id": alert_id, "notified": email_recipients or []}


@celery_app.task(
    name="app.workers.celery_app.aggregate_metrics",
    queue="low_priority",
)
def aggregate_metrics():
    """
    Aggregate fraud metrics and push to dashboard via WebSocket.
    Runs every 60 seconds.
    """
    import asyncio

    async def _inner():
        from app.database import AsyncSessionLocal
        from app.repositories.transaction_repo import TransactionRepository
        from app.repositories import AlertRepository
        from app.services.websocket_manager import websocket_manager

        async with AsyncSessionLocal() as session:
            tx_repo = TransactionRepository(session)
            alert_repo = AlertRepository(session)
            stats = await tx_repo.get_stats_24h()
            stats["open_alerts"] = await alert_repo.count_open()
            stats["critical_alerts"] = await alert_repo.count_critical()
            await websocket_manager.broadcast_metrics_update(stats)

    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_inner())
        loop.close()
        return "metrics_pushed"
    except Exception as exc:
        logger.error("Metrics aggregation failed: %s", exc)
        return "error"


@celery_app.task(
    name="app.workers.celery_app.cleanup_expired_cache",
    queue="low_priority",
)
def cleanup_expired_cache():
    """
    Redis TTL handles expiry; this task cleans up orphan keys.
    Stage 7: Cache invalidation.
    """
    import asyncio

    async def _inner():
        from app.core.cache import redis_client
        # Example: delete old risk score keys (TTL 24h handles this automatically)
        # Additional cleanup logic can go here
        info = await redis_client.info("keyspace")
        logger.info("Redis keyspace info: %s", info)
        return info

    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(_inner())
    loop.close()
    return result
