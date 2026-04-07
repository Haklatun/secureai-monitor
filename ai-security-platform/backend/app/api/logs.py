from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException

from app.api.deps import TenantDB, TenantID, CurrentPayload, require_admin
from app.models.schemas import (
    LogIngest, LogOut, LogListResponse,
    StatsResponse, TimeseriesPoint, AlertOut,
)
from app.services import log_service, ai_engine
from app.core.websocket import manager

router = APIRouter(prefix="/logs", tags=["logs"])


@router.post("", response_model=LogOut, status_code=201)
async def ingest_log(
    body: LogIngest,
    db: TenantDB,
    tenant_id: TenantID,
):
    # Run AI pipeline
    ai_result = await ai_engine.process_log(
        event_type=body.event_type,
        payload=body.payload,
        source_ip=body.source_ip,
        status_code=body.status_code,
    )

    log = await log_service.ingest_log(db, tenant_id, body, ai_result)

    # Broadcast anomalies over WebSocket
    if ai_result["is_anomaly"]:
        alert = {
            "type": "alert",
            "log_id": str(log.id),
            "severity": ai_result["severity"],
            "anomaly_score": ai_result["anomaly_score"],
            "source_ip": body.source_ip,
            "event_type": body.event_type,
        }
        await manager.broadcast(str(tenant_id), alert)

    return log


@router.get("", response_model=LogListResponse)
async def list_logs(
    db: TenantDB,
    tenant_id: TenantID,
    severity: str | None = Query(default=None, pattern="^(low|medium|high|critical)$"),
    is_anomaly: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    return await log_service.get_logs(db, tenant_id, severity, is_anomaly, page, page_size)


@router.get("/stats", response_model=StatsResponse)
async def stats(db: TenantDB, tenant_id: TenantID):
    data = await log_service.get_stats(db, tenant_id)
    return StatsResponse(**data)


@router.get("/timeseries", response_model=list[TimeseriesPoint])
async def timeseries(
    db: TenantDB,
    tenant_id: TenantID,
    hours: int = Query(default=12, ge=1, le=72),
):
    rows = await log_service.get_timeseries(db, tenant_id, hours)
    return [TimeseriesPoint(**r) for r in rows]


@router.patch("/{log_id}/resolve", response_model=LogOut)
async def resolve_log(
    log_id: UUID,
    db: TenantDB,
    tenant_id: TenantID,
    payload: CurrentPayload,
):
    from sqlalchemy import select, update
    from app.db.models import SecurityLog
    from uuid import UUID as _UUID
    from datetime import datetime, timezone

    row = (
        await db.execute(
            select(SecurityLog).where(
                SecurityLog.id == log_id,
                SecurityLog.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Log not found")

    row.resolved = True
    row.resolved_by = _UUID(payload["sub"])
    row.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(row)
    return row
