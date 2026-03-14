from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional

from app.api.deps import DbDep, CurrentUser, require_admin
from app.schemas.fraud_rule import FraudRuleCreate, FraudRuleResponse
from app.schemas.base import PaginatedResponse
from app.repositories.fraud_rule import FraudRuleRepository
from app.models.fraud_rule import RuleType

router = APIRouter()

@router.post("/", response_model=FraudRuleResponse, dependencies=[Depends(require_admin)])
async def create_rule(
    rule_in: FraudRuleCreate,
    db: DbDep
):
    repo = FraudRuleRepository(db)
    
    existing = await repo.get_by_name(rule_in.rule_name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rule name already exists"
        )
    
    rule = await repo.create(rule_in.model_dump())
    return rule

@router.get("/", response_model=PaginatedResponse[FraudRuleResponse])
async def list_rules(
    db: DbDep,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    rule_type: Optional[RuleType] = None,
    is_active: Optional[bool] = None
):
    repo = FraudRuleRepository(db)
    
    if rule_type:
        items = await repo.get_by_type(rule_type)
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

@router.get("/active", response_model=List[FraudRuleResponse])
async def get_active_rules(db: DbDep):
    repo = FraudRuleRepository(db)
    rules = await repo.get_active_rules()
    return rules

@router.put("/{rule_id}", response_model=FraudRuleResponse, dependencies=[Depends(require_admin)])
async def update_rule(
    rule_id: int,
    rule_in: FraudRuleCreate,
    db: DbDep
):
    repo = FraudRuleRepository(db)
    updated = await repo.update(rule_id, rule_in.model_dump())
    if not updated:
        raise HTTPException(status_code=404, detail="Rule not found")
    return updated

@router.delete("/{rule_id}", dependencies=[Depends(require_admin)])
async def delete_rule(rule_id: int, db: DbDep):
    repo = FraudRuleRepository(db)
    deleted = await repo.delete(rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"message": "Rule deleted successfully"}