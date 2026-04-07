"""
WebSocket connection manager for real-time alerts.
Tenants are isolated — each connection is scoped to a tenant_id.
"""
import json
import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # tenant_id → list of active WebSocket connections
        self._connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, tenant_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections[tenant_id].append(ws)
        logger.info("WS connected tenant=%s total=%d", tenant_id, len(self._connections[tenant_id]))

    def disconnect(self, tenant_id: str, ws: WebSocket) -> None:
        self._connections[tenant_id].discard(ws) if hasattr(
            self._connections[tenant_id], "discard"
        ) else None
        try:
            self._connections[tenant_id].remove(ws)
        except ValueError:
            pass

    async def broadcast(self, tenant_id: str, message: dict) -> None:
        dead = []
        for ws in list(self._connections.get(tenant_id, [])):
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(tenant_id, ws)


manager = ConnectionManager()
