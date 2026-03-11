"""SentinelFraud API v1 Router"""

from fastapi import APIRouter

from app.api.v1 import auth, transactions, alerts, users, rules, ml, websocket

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(rules.router, prefix="/rules", tags=["Fraud Rules"])
api_router.include_router(ml.router, prefix="/ml", tags=["ML Models"])
api_router.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
