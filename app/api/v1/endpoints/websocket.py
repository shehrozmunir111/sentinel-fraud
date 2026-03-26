from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from app.core.config import settings
from app.services.websocket import websocket_manager
import json

router = APIRouter()

@router.websocket("/alerts")
async def fraud_alerts_websocket(websocket: WebSocket, token: str):
    role = None
    user_id = None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        role = payload.get("role", "analyst")

        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
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
    except JWTError:
        await websocket.close(code=4001, reason="Invalid token")
    except Exception as e:
        await websocket.close(code=4001, reason=str(e))
    finally:
        if role and user_id:
            await websocket_manager.disconnect(websocket, role, user_id)
