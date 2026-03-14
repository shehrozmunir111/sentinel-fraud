from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import async_session

async def get_db_session() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()