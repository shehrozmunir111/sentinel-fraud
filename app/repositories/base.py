from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func

ModelType = TypeVar("ModelType")

class BaseRepository(ABC, Generic[ModelType]):
    def __init__(self, model: type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db
    
    async def get_by_id(self, id: Any) -> Optional[ModelType]:
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        result = await self.db.execute(select(self.model).offset(skip).limit(limit))
        return result.scalars().all()
    
    async def create(self, obj_in: dict) -> ModelType:
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj
    
    async def update(self, id: Any, obj_in: dict) -> Optional[ModelType]:
        await self.db.execute(
            update(self.model).where(self.model.id == id).values(**obj_in)
        )
        await self.db.commit()
        return await self.get_by_id(id)
    
    async def delete(self, id: Any) -> bool:
        result = await self.db.execute(delete(self.model).where(self.model.id == id))
        await self.db.commit()
        return result.rowcount > 0

    async def count(self, **filters) -> int:
        query = select(func.count(self.model.id))
        for key, value in filters.items():
            query = query.where(getattr(self.model, key) == value)
        result = await self.db.execute(query)
        return result.scalar()