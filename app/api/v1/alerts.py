"""SentinelFraud Alerts API"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_permission
from app.database import get_db
from app.repositories import AlertRepository
from app.schemas import AlertResponse, AlertUpdate, PagedResponse
from app.services.alert_service import AlertService

router = APIRouter()


@router.get("/", response_model=PagedResponse[AlertResponse], dependencies=[require_permission("alerts:read")])
async def list_alerts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = None,
    severity: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    repo = AlertRepository(db)
    offset = (page - 1) * page_size
    alerts, total = await repo.get_list(status=status, severity=severity, offset=offset, limit=page_size)
    return PagedResponse.build(data=alerts, total=total, page=page, page_size=page_size)


@router.get("/{alert_id}", response_model=AlertResponse, dependencies=[require_permission("alerts:read")])
async def get_alert(alert_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    repo = AlertRepository(db)
    alert = await repo.get_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.patch("/{alert_id}", response_model=AlertResponse, dependencies=[require_permission("alerts:write")])
async def update_alert(alert_id: uuid.UUID, payload: AlertUpdate, db: AsyncSession = Depends(get_db)):
    service = AlertService(db)
    alert = await service.resolve_alert(
        alert_id=alert_id,
        status=payload.status.value if payload.status else None,
        notes=payload.notes,
        assigned_to=payload.assigned_to,
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert
