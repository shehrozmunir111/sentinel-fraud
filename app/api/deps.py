from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import get_db
from app.core.security import get_current_user
from typing import Annotated

DbDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_user)]