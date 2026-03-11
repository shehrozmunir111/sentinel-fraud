"""
SentinelFraud Auth API
Stage 4: JWT auth, bcrypt, audit logging
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user_payload
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models import AuditLog
from app.repositories import UserRepository
from app.schemas import LoginRequest, RefreshTokenRequest, TokenResponse, UserCreate, UserResponse
from app.config import settings

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    existing = await repo.get_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = await repo.create({
        "email": payload.email,
        "hashed_password": hash_password(payload.password),
        "full_name": payload.full_name,
        "phone": payload.phone,
        "country": payload.country,
        "role": payload.role.value,
    })
    return user


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    user = await repo.get_by_email(payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    access_token = create_access_token(str(user.id), user.role)
    refresh_token = create_refresh_token(str(user.id))

    # Update last login
    await repo.update(user.id, {"last_login": datetime.now(timezone.utc)})

    # Audit log
    db.add(AuditLog(
        user_id=user.id,
        action="user_login",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    ))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    try:
        decoded = decode_token(payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    if decoded.get("type") != "refresh":
        raise HTTPException(status_code=400, detail="Invalid token type")

    repo = UserRepository(db)
    user = await repo.get_by_id(uuid.UUID(decoded["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role),
        refresh_token=create_refresh_token(str(user.id)),
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
async def me(payload: dict = Depends(get_current_user_payload), db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    user = await repo.get_by_id(uuid.UUID(payload["sub"]))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
