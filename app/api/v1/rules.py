"""SentinelFraud Fraud Rules API"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_permission
from app.database import get_db
from app.repositories import FraudRuleRepository
from app.schemas import FraudRuleCreate, FraudRuleResponse, FraudRuleUpdate, PagedResponse

router = APIRouter()


@router.get("/", response_model=PagedResponse[FraudRuleResponse], dependencies=[require_permission("rules:read")])
async def list_rules(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    repo = FraudRuleRepository(db)
    offset = (page - 1) * page_size
    rules, total = await repo.get_list(offset=offset, limit=page_size)
    return PagedResponse.build(data=rules, total=total, page=page, page_size=page_size)


@router.post("/", response_model=FraudRuleResponse, status_code=201, dependencies=[require_permission("rules:write")])
async def create_rule(payload: FraudRuleCreate, db: AsyncSession = Depends(get_db)):
    repo = FraudRuleRepository(db)
    data = payload.model_dump()
    data["rule_type"] = data["rule_type"].value
    return await repo.create(data)


@router.get("/{rule_id}", response_model=FraudRuleResponse, dependencies=[require_permission("rules:read")])
async def get_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    repo = FraudRuleRepository(db)
    rule = await repo.get_by_id(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.patch("/{rule_id}", response_model=FraudRuleResponse, dependencies=[require_permission("rules:write")])
async def update_rule(rule_id: int, payload: FraudRuleUpdate, db: AsyncSession = Depends(get_db)):
    repo = FraudRuleRepository(db)
    rule = await repo.update(rule_id, payload.model_dump(exclude_none=True))
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.delete("/{rule_id}", status_code=204, dependencies=[require_permission("rules:write")])
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    repo = FraudRuleRepository(db)
    await repo.update(rule_id, {"is_active": False})
