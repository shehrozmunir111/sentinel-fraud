from app.tasks.celery_app import celery_app
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import asyncio

engine = create_async_engine(settings.DATABASE_URI)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@celery_app.task(bind=True, max_retries=3)
def process_transaction_async(self, transaction_id: str):
    try:
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(_async_process(transaction_id))
        return result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

async def _async_process(transaction_id: str):
    async with async_session() as db:
        await asyncio.sleep(0.1)
        return {"status": "processed", "tx_id": transaction_id}

@celery_app.task
def batch_model_retraining():
    return {"status": "retraining_completed"}