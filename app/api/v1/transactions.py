"""
SentinelFraud Transactions API
Stage 1: Async endpoints, Pydantic validation
Stage 2: Service/Repository pattern
Stage 5: Pagination, filtering, sorting, rate limiting
Core: Real-time fraud scoring <100ms
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import get_current_user_id, require_permission
from app.core.cache import check_rate_limit, get_cached_risk_score
from app.database import get_db
from app.repositories.transaction_repo import TransactionRepository
from app.repositories import AlertRepository
from app.schemas import (
    DashboardStats,
    Decision,
    PagedResponse,
    RiskScoreResult,
    TransactionCreate,
    TransactionFilter,
    TransactionResponse,
)
from app.services.alert_service import AlertService
from app.services.risk_engine import RiskEngineService
from app.services.websocket_manager import websocket_manager

router = APIRouter()


# ---------------------------------------------------------------------------
# Rate limiting middleware
# ---------------------------------------------------------------------------
async def rate_limit_check(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    allowed, count = await check_rate_limit(
        f"api:{client_ip}", settings.RATE_LIMIT_REQUESTS, settings.RATE_LIMIT_WINDOW
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {count}/{settings.RATE_LIMIT_REQUESTS} per {settings.RATE_LIMIT_WINDOW}s",
        )


# ---------------------------------------------------------------------------
# POST /transactions  —  Real-time fraud scoring
# ---------------------------------------------------------------------------
@router.post(
    "/",
    response_model=RiskScoreResult,
    status_code=status.HTTP_201_CREATED,
    summary="Submit transaction for real-time fraud scoring (<100ms)",
    dependencies=[require_permission("transactions:write")],
)
async def score_transaction(
    payload: TransactionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    await rate_limit_check(request)

    # Check cache (idempotency)
    cached = await get_cached_risk_score(payload.transaction_id)
    if cached:
        return RiskScoreResult(
            transaction_id=payload.transaction_id,
            risk_score=cached["risk_score"],
            decision=cached["decision"],
            ml_score=cached.get("ml_score"),
            rule_score=cached.get("rule_score", 0),
            processing_time_ms=0.0,
            is_fraud=cached["risk_score"] >= settings.RISK_SCORE_FRAUD_THRESHOLD,
        )

    tx_repo = TransactionRepository(db)
    risk_engine = RiskEngineService(db)
    alert_service = AlertService(db)

    # Persist transaction record first (minimal data)
    ts = payload.timestamp or datetime.now(timezone.utc)
    tx = await tx_repo.create({
        "transaction_id": payload.transaction_id,
        "user_id": payload.user_id,
        "card_id": payload.card_id,
        "amount": payload.amount,
        "currency": payload.currency,
        "merchant_id": payload.merchant_id,
        "merchant_category": payload.merchant_category,
        "country_code": payload.country_code,
        "city": payload.city,
        "ip_address": payload.ip_address or (request.client.host if request.client else None),
        "device_fingerprint": payload.device_fingerprint,
        "timestamp": ts,
    })

    # Run risk scoring
    result = await risk_engine.calculate_risk_score(
        transaction_id=payload.transaction_id,
        card_id=payload.card_id,
        amount=payload.amount,
        currency=payload.currency,
        country_code=payload.country_code,
        ip_address=payload.ip_address,
        device_fingerprint=payload.device_fingerprint,
        merchant_category=payload.merchant_category,
        user_id=str(payload.user_id) if payload.user_id else None,
        timestamp=ts,
    )

    # Update transaction with scores
    await tx_repo.update_risk_score(
        tx_id=tx.id,
        risk_score=result.risk_score,
        decision=result.decision,
        is_fraud=result.is_fraud,
        ml_score=result.ml_score,
        rule_score=result.rule_score,
        processing_time_ms=result.processing_time_ms,
        raw_features={"rule_triggers": result.rule_triggers},
    )

    # Create alert if needed
    await alert_service.create_if_needed(
        transaction_id=tx.id,
        risk_score=result.risk_score,
        decision=result.decision,
        amount=payload.amount,
        currency=payload.currency,
        card_id=payload.card_id,
        country_code=payload.country_code,
        rule_triggers=result.rule_triggers,
        transaction_id_str=payload.transaction_id,
    )

    # WebSocket: broadcast to dashboard
    await websocket_manager.broadcast_transaction_update({
        "transaction_id": payload.transaction_id,
        "risk_score": result.risk_score,
        "decision": result.decision,
        "amount": payload.amount,
        "currency": payload.currency,
        "is_fraud": result.is_fraud,
        "processing_time_ms": result.processing_time_ms,
    })

    return RiskScoreResult(
        transaction_id=payload.transaction_id,
        risk_score=result.risk_score,
        decision=result.decision,
        ml_score=result.ml_score,
        rule_score=result.rule_score,
        rule_triggers=result.rule_triggers,
        processing_time_ms=result.processing_time_ms,
        is_fraud=result.is_fraud,
    )


# ---------------------------------------------------------------------------
# GET /transactions  —  Paginated list with filters
# ---------------------------------------------------------------------------
@router.get(
    "/",
    response_model=PagedResponse[TransactionResponse],
    summary="List transactions with pagination, filtering, sorting",
    dependencies=[require_permission("transactions:read")],
)
async def list_transactions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    decision: Optional[Decision] = None,
    is_fraud: Optional[bool] = None,
    min_risk_score: Optional[int] = Query(default=None, ge=0, le=100),
    max_risk_score: Optional[int] = Query(default=None, ge=0, le=100),
    card_id: Optional[str] = None,
    country_code: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
):
    repo = TransactionRepository(db)
    filters = TransactionFilter(
        decision=decision,
        is_fraud=is_fraud,
        min_risk_score=min_risk_score,
        max_risk_score=max_risk_score,
        card_id=card_id,
        country_code=country_code,
        date_from=date_from,
        date_to=date_to,
    )
    offset = (page - 1) * page_size
    txs, total = await repo.get_list(filters, offset=offset, limit=page_size, sort_by=sort_by, sort_order=sort_order)
    return PagedResponse.build(data=txs, total=total, page=page, page_size=page_size)


# ---------------------------------------------------------------------------
# GET /transactions/{id}
# ---------------------------------------------------------------------------
@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    dependencies=[require_permission("transactions:read")],
)
async def get_transaction(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
):
    repo = TransactionRepository(db)
    tx = await repo.get_by_transaction_id(transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail=f"Transaction '{transaction_id}' not found")
    return tx


# ---------------------------------------------------------------------------
# GET /transactions/stats/dashboard
# ---------------------------------------------------------------------------
@router.get(
    "/stats/dashboard",
    response_model=DashboardStats,
    summary="24h fraud statistics",
    dependencies=[require_permission("transactions:read")],
)
async def dashboard_stats(db: AsyncSession = Depends(get_db)):
    tx_repo = TransactionRepository(db)
    alert_repo = AlertRepository(db)
    stats = await tx_repo.get_stats_24h()
    stats["open_alerts"] = await alert_repo.count_open()
    stats["critical_alerts"] = await alert_repo.count_critical()
    stats["transactions_per_second"] = round(stats["total_transactions_24h"] / 86400, 2)
    return DashboardStats(**stats)
