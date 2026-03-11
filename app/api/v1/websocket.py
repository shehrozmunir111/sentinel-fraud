"""
SentinelFraud WebSocket API
Stage 10: Real-time WebSocket, horizontal scaling design
"""

import json
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.services.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/fraud-alerts")
async def ws_fraud_alerts(
    websocket: WebSocket,
    rooms: str = Query(default="alerts,dashboard"),
):
    """
    WebSocket endpoint for real-time fraud alerts.
    
    Connect: ws://host/api/v1/ws/fraud-alerts?rooms=alerts,dashboard
    
    Rooms:
      - alerts:    Real-time fraud alert stream
      - dashboard: Aggregated metrics + all transaction scores
      - admin:     All events (requires admin token in production)
    
    Events:
      - fraud_alert:        Triggered when risk_score >= threshold
      - transaction_scored: Every scored transaction
      - metrics_update:     Periodic dashboard stats (every 60s)
    
    Horizontal Scaling (Stage 10 / CAP Theorem):
      - Replace in-memory dict with Redis Pub/Sub
      - CAP trade-off: choose AP (Availability + Partition Tolerance)
      - Accept eventual consistency for metrics delivery
      - Use sticky sessions or Redis adapter for session affinity
    """
    room_list = [r.strip() for r in rooms.split(",") if r.strip()]

    await websocket_manager.connect(websocket, room_list)

    # Send welcome message
    await websocket_manager.send_personal(websocket, {
        "event": "connected",
        "data": {
            "message": "Connected to SentinelFraud real-time stream",
            "rooms": room_list,
            "stats": websocket_manager.stats(),
        },
    })

    try:
        while True:
            # Keep connection alive; handle client messages (ping/subscribe)
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("event") == "ping":
                    await websocket_manager.send_personal(websocket, {"event": "pong"})
                elif msg.get("event") == "subscribe":
                    new_rooms = msg.get("rooms", [])
                    # Re-connect with updated rooms
                    await websocket_manager.disconnect(websocket)
                    await websocket_manager.connect(websocket, new_rooms)
                    await websocket_manager.send_personal(websocket, {
                        "event": "subscribed",
                        "data": {"rooms": new_rooms},
                    })
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
