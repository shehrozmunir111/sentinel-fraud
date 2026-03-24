from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
from sqlalchemy import select, desc, asc, func
from datetime import datetime

from app.api.deps import DbDep, CurrentUser
from app.schemas.transaction import TransactionCreate, TransactionResponse, RiskAssessmentResponse
from app.schemas.base import PaginatedResponse
from app.services.risk_engine import RiskEngineService
from app.services.alert import AlertService
from app.services.websocket import websocket_manager
from app.models.transaction import Transaction
from app.repositories.transaction import TransactionRepository

router = APIRouter()

@router.post("/assess", response_model=RiskAssessmentResponse)
async def assess_transaction(
    transaction: TransactionCreate,
    db: DbDep,
    current_user: CurrentUser
):
    risk_engine = RiskEngineService(db)
    
    tx_data = transaction.model_dump()
    tx_data['user_id'] = transaction.user_id
    
    repo = TransactionRepository(db)
    
    risk_score, decision, details = await risk_engine.calculate_risk_score(tx_data)
    
    # Persist the transaction
    tx_record = tx_data.copy()
    tx_record.update({
        "risk_score": risk_score,
        "decision": decision,
        "is_fraud": decision == "decline",
        "ml_score": details['ml_score'],
        "rule_scores": details['rule_contributions']
    })
    await repo.create(tx_record)
    
    if decision in ["decline", "review"]:
        alert_service = AlertService(db)
        await alert_service.create_alert(
            transaction_id=transaction.transaction_id,
            alert_type="high_risk_transaction",
            severity="high" if decision == "decline" else "medium",
            description=f"Risk score: {risk_score}, ML: {details['ml_score']:.2f}"
        )
        
        await websocket_manager.broadcast_fraud_alert({
            "transaction_id": transaction.transaction_id,
            "risk_score": risk_score,
            "decision": decision,
            "amount": str(transaction.amount),
            "merchant": transaction.merchant_id
        })
    
    return RiskAssessmentResponse(
        transaction_id=transaction.transaction_id,
        risk_score=risk_score,
        decision=decision,
        ml_score=details['ml_score'],
        rule_contributions=details['rule_contributions'],
        processing_time_ms=details['processing_time_ms']
    )

@router.get("/", response_model=PaginatedResponse[TransactionResponse])
async def list_transactions(
    db: DbDep,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    decision: Optional[str] = None,
    min_amount: Optional[float] = None,
    user_id: Optional[str] = None
):
    query = select(Transaction)
    
    if decision:
        query = query.where(Transaction.decision == decision)
    if min_amount:
        query = query.where(Transaction.amount >= min_amount)
    if user_id:
        query = query.where(Transaction.user_id == user_id)
    
    sort_column = getattr(Transaction, sort_by, Transaction.created_at)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))
    
    total = await db.scalar(select(func.count(Transaction.id)))
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    return PaginatedResponse(
        items=[TransactionResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit
    )