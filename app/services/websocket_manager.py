"""
SentinelFraud WebSocket Manager
Stage 10: Real-time WebSocket, horizontal scaling design
Supports room-based broadcasting for fraud alerts and dashboard updates.
"""

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages WebSocket connections with room-based broadcasting.
    For horizontal scaling: replace in-memory store with Redis Pub/Sub.

    Rooms:
      "alerts"     - fraud alert stream (all detected frauds)
      "dashboard"  - aggregated metrics updates
      "admin"      - all events (admin users)
    """

    def __init__(self):
        # room -> set of websockets
        self._rooms: Dict[str, Set[WebSocket]] = defaultdict(set)
        # ws -> set of rooms
        self._ws_rooms: Dict[WebSocket, Set[str]] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------
    async def connect(self, ws: WebSocket, rooms: list[str] = None) -> None:
        await ws.accept()
        rooms = rooms or ["alerts", "dashboard"]
        async with self._lock:
            self._ws_rooms[ws] = set(rooms)
            for room in rooms:
                self._rooms[room].add(ws)
        logger.info("WS connected. Rooms: %s. Total connections: %d", rooms, self.connection_count())

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            rooms = self._ws_rooms.pop(ws, set())
            for room in rooms:
                self._rooms[room].discard(ws)
        logger.info("WS disconnected. Total connections: %d", self.connection_count())

    # ------------------------------------------------------------------
    # Broadcast helpers
    # ------------------------------------------------------------------
    async def broadcast_to_room(self, room: str, message: dict) -> None:
        payload = json.dumps(message, default=str)
        dead: list[WebSocket] = []
        async with self._lock:
            connections = list(self._rooms.get(room, set()))

        for ws in connections:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)

        for ws in dead:
            await self.disconnect(ws)

    async def broadcast_fraud_alert(self, transaction_data: dict) -> None:
        """Broadcast to 'alerts' and 'admin' rooms."""
        message = {
            "event": "fraud_alert",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": transaction_data,
        }
        await self.broadcast_to_room("alerts", message)
        await self.broadcast_to_room("admin", message)

    async def broadcast_transaction_update(self, transaction_data: dict) -> None:
        """Broadcast real-time transaction scoring result."""
        message = {
            "event": "transaction_scored",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": transaction_data,
        }
        await self.broadcast_to_room("dashboard", message)
        await self.broadcast_to_room("admin", message)

    async def broadcast_metrics_update(self, metrics: dict) -> None:
        message = {
            "event": "metrics_update",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": metrics,
        }
        await self.broadcast_to_room("dashboard", message)

    async def send_personal(self, ws: WebSocket, message: dict) -> None:
        try:
            await ws.send_text(json.dumps(message, default=str))
        except Exception:
            await self.disconnect(ws)

    # ------------------------------------------------------------------
    # Connection info
    # ------------------------------------------------------------------
    def connection_count(self) -> int:
        return len(self._ws_rooms)

    def room_count(self, room: str) -> int:
        return len(self._rooms.get(room, set()))

    def stats(self) -> dict:
        return {
            "total_connections": self.connection_count(),
            "rooms": {room: len(conns) for room, conns in self._rooms.items()},
        }

    # ------------------------------------------------------------------
    # Horizontal scaling note
    # ------------------------------------------------------------------
    # For multi-process / multi-node deployments:
    # Replace broadcast_to_room() with:
    #   await redis_client.publish(f"ws:{room}", json.dumps(message))
    # And run a subscriber per process that forwards to local WS connections.
    # This follows the Redis Pub/Sub CAP theorem tradeoff (AP system):
    #   - Availability: messages always published even if subscriber down
    #   - Partition Tolerance: Redis handles network partitions gracefully
    #   - Consistency: eventual (subscriber may miss messages during restart)


# Module-level singleton
websocket_manager = WebSocketManager()
