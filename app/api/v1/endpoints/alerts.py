from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from uuid import UUID

from app.api.deps import DbDep, CurrentUser, require_analyst
from app.schemas.alert import AlertResponse, AlertUpdate
from app.schemas.base import PaginatedResponse
from app.repositories.alert import AlertRepository
from app.services.alert import AlertService
from app.models.alert import AlertStatus, AlertSeverity

router = APIRouter()

@router.get("/", response_model=PaginatedResponse[AlertResponse])
async def list_alerts(
    db: DbDep,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[AlertStatus] = None,
    severity: Optional[AlertSeverity] = None,
    assigned_to_me: bool = False
):
    repo = AlertRepository(db)
    
    if assigned_to_me:
        items = await repo.get_assigned_to_user(current_user["user_id"])
        total = len(items)
    elif status == AlertStatus.OPEN:
        items = await repo.get_open_alerts(severity)
        total = len(items)
    else:
        items = await repo.get_all(skip=(page-1)*limit, limit=limit)
        total = await repo.count()
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit
    )

@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: UUID,
    db: DbDep,
    current_user: CurrentUser
):
    repo = AlertRepository(db)
    alert = await repo.get_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert

@router.post("/{alert_id}/assign", response_model=AlertResponse, dependencies=[Depends(require_analyst)])
async def assign_alert(
    alert_id: UUID,
    user_id: UUID,
    db: DbDep
):
    service = AlertService(db)
    result = await service.assign_alert(alert_id, user_id)
    
    repo = AlertRepository(db)
    alert = await repo.get_by_id(alert_id)
    return alert

@router.post("/{alert_id}/resolve", response_model=AlertResponse, dependencies=[Depends(require_analyst)])
async def resolve_alert(
    alert_id: UUID,
    update_data: AlertUpdate,
    db: DbDep
):
    service = AlertService(db)
    
    is_fp = update_data.status == AlertStatus.FALSE_POSITIVE
    await service.resolve_alert(
        alert_id, 
        update_data.resolution_notes or "",
        is_false_positive=is_fp
    )
    
    repo = AlertRepository(db)
    alert = await repo.get_by_id(alert_id)
    return alert