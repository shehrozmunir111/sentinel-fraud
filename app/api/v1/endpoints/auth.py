from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbDep, CurrentUser
from app.schemas.user import UserCreate, UserResponse, Token
from app.repositories.user import UserRepository
from app.core.security import verify_password, create_access_token, get_password_hash
from app.core.config import settings

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(user_in: UserCreate, db: DbDep):
    repo = UserRepository(db)
    
    existing = await repo.get_by_email(user_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    user_data = user_in.model_dump()
    user_data["hashed_password"] = get_password_hash(user_data.pop("password"))
    user_data["is_active"] = "Y"
    user_data["role"] = "analyst"
    
    user = await repo.create(user_data)
    return user

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: DbDep = None
):
    repo = UserRepository(db)
    user = await repo.get_by_email(form_data.username)
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role, "email": user.email}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

from uuid import UUID

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser, db: DbDep = None):
    repo = UserRepository(db)
    user = await repo.get_by_id(UUID(str(current_user["user_id"])))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user