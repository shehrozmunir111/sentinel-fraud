"""SentinelFraud ML Model API"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_permission
from app.database import get_db
from app.repositories import MLModelRepository
from app.schemas import MLModelResponse, PagedResponse
from app.services.ml_model import ml_model_service

router = APIRouter()


@router.get("/", response_model=PagedResponse[MLModelResponse], dependencies=[require_permission("ml:read")])
async def list_models(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    repo = MLModelRepository(db)
    offset = (page - 1) * page_size
    models, total = await repo.get_list(offset=offset, limit=page_size)
    return PagedResponse.build(data=models, total=total, page=page, page_size=page_size)


@router.get("/status", dependencies=[require_permission("ml:read")])
async def model_status():
    return {
        "loaded": ml_model_service.is_loaded,
        "version": ml_model_service.version,
        "model_path": ml_model_service._model_path,
    }


@router.post("/train", dependencies=[require_permission("ml:train")])
async def trigger_training(csv_path: str = None):
    """Trigger background model training via Celery."""
    try:
        from app.workers.celery_app import train_fraud_model
        task = train_fraud_model.delay(csv_path=csv_path)
        return {"task_id": task.id, "status": "queued", "message": "Model training started"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to queue training: {exc}")


@router.post("/train/sync", dependencies=[require_permission("ml:train")])
async def train_sync(csv_path: str = None):
    """Synchronous training for testing/development."""
    import asyncio
    from app.ml.trainer import FraudModelTrainer
    from datetime import datetime, timezone

    version = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    trainer = FraudModelTrainer()

    loop = asyncio.get_event_loop()
    metrics = await loop.run_in_executor(
        None,
        lambda: trainer.train(csv_path=csv_path, model_version=version)
    )

    # Load into memory
    loaded = await ml_model_service.load_model(metrics["model_path"], version)

    return {
        "status": "complete" if loaded else "trained_not_loaded",
        "metrics": metrics,
    }
