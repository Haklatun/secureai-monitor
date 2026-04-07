from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.security import verify_access_token
from app.core.websocket import manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/alerts")
async def alerts_ws(
    websocket: WebSocket,
    token: str = Query(...),
):
    payload = verify_access_token(token)
    if not payload:
        await websocket.close(code=4001)
        return

    tenant_id = payload["tenant_id"]
    await manager.connect(tenant_id, websocket)
    try:
        while True:
            # Keep-alive: client can send pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(tenant_id, websocket)
