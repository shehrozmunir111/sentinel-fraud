from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket import websocket_manager
import json

router = APIRouter()

@router.websocket("/alerts")
async def fraud_alerts_websocket(websocket: WebSocket, token: str):
    try:
        role = "analyst"
        user_id = "user_123"
        
        await websocket_manager.connect(websocket, role, user_id)
        
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("action") == "subscribe":
                    pass
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                await websocket.send_json({"error": str(e)})
                
    except Exception as e:
        await websocket.close(code=4001, reason=str(e))
    finally:
        await websocket_manager.disconnect(websocket, role, user_id)