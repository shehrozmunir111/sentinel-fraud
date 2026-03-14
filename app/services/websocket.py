from typing import List, Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
import json
import asyncio
from datetime import datetime
from app.core.config import settings

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "admin": set(),
            "analyst": set(),
            "system": set()
        }
        self.user_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, role: str = "analyst", user_id: str = None):
        await websocket.accept()
        if role in self.active_connections:
            self.active_connections[role].add(websocket)
        if user_id:
            self.user_connections[user_id] = websocket
        
        asyncio.create_task(self._heartbeat(websocket))
    
    async def disconnect(self, websocket: WebSocket, role: str = "analyst", user_id: str = None):
        if role in self.active_connections:
            self.active_connections[role].discard(websocket)
        if user_id and user_id in self.user_connections:
            del self.user_connections[user_id]
    
    async def broadcast_fraud_alert(self, alert_data: dict):
        message = {
            "type": "fraud_alert",
            "timestamp": datetime.utcnow().isoformat(),
            "data": alert_data
        }
        
        disconnected = []
        for role in ["admin", "analyst"]:
            for connection in self.active_connections[role]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append((role, connection))
        
        for role, conn in disconnected:
            self.active_connections[role].discard(conn)
    
    async def send_transaction_update(self, user_id: str, transaction_data: dict):
        if user_id in self.user_connections:
            try:
                await self.user_connections[user_id].send_json({
                    "type": "transaction_update",
                    "data": transaction_data
                })
            except Exception:
                pass
    
    async def _heartbeat(self, websocket: WebSocket):
        try:
            while True:
                await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
                await websocket.send_json({"type": "ping"})
        except Exception:
            pass

websocket_manager = WebSocketManager()