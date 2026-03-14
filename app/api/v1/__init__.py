from fastapi import APIRouter
from app.api.v1.endpoints import auth, transactions, rules, alerts, websocket

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
api_router.include_router(rules.router, prefix="/rules", tags=["rules"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"])