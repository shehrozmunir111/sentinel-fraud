"""SentinelFraud Users API"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_permission
from app.core.security import hash_password
from app.database import get_db
from app.repositories import UserRepository
from app.schemas import PagedResponse, UserCreate, UserResponse, UserUpdate

router = APIRouter()


@router.get("/", response_model=PagedResponse[UserResponse], dependencies=[require_permission("users:read")])
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    offset = (page - 1) * page_size
    users, total = await repo.get_list(offset=offset, limit=page_size)
    return PagedResponse.build(data=users, total=total, page=page, page_size=page_size)


@router.get("/{user_id}", response_model=UserResponse, dependencies=[require_permission("users:read")])
async def get_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserResponse, dependencies=[require_permission("users:write")])
async def update_user(user_id: uuid.UUID, payload: UserUpdate, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    data = payload.model_dump(exclude_none=True)
    if "risk_profile" in data:
        data["risk_profile"] = data["risk_profile"].value
    user = await repo.update(user_id, data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
