from __future__ import annotations
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import UUID

from cryptography.fernet import Fernet
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SecurityLog
from app.models.schemas import LogIngest, LogOut, LogListResponse


# Encryption key — in production store in vault/env
_FERNET_KEY = os.getenv("FERNET_KEY", Fernet.generate_key().decode()).encode()
_fernet = Fernet(_FERNET_KEY)


def encrypt_payload(data: dict) -> bytes:
    return _fernet.encrypt(json.dumps(data).encode())


def decrypt_payload(data: bytes) -> dict:
    return json.loads(_fernet.decrypt(data))


async def ingest_log(
    db: AsyncSession,
    tenant_id: UUID,
    ingest: LogIngest,
    ai_result: dict[str, Any],
) -> SecurityLog:
    encrypted = encrypt_payload(ingest.payload)
    embedding = ai_result.get("embedding")

    log = SecurityLog(
        tenant_id=tenant_id,
        event_type=ingest.event_type,
        severity=ai_result["severity"],
        source_ip=ingest.source_ip,
        raw_payload=encrypted,
        user_agent=ingest.user_agent,
        endpoint=ingest.endpoint,
        status_code=ingest.status_code,
        anomaly_score=ai_result["anomaly_score"],
        is_anomaly=ai_result["is_anomaly"],
        embedding=embedding,
        metadata_={"event_type": ingest.event_type},
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def get_logs(
    db: AsyncSession,
    tenant_id: UUID,
    severity: str | None = None,
    is_anomaly: bool | None = None,
    page: int = 1,
    page_size: int = 50,
) -> LogListResponse:
    conditions = [SecurityLog.tenant_id == tenant_id]
    if severity:
        conditions.append(SecurityLog.severity == severity)
    if is_anomaly is not None:
        conditions.append(SecurityLog.is_anomaly == is_anomaly)

    count_q = select(func.count()).select_from(SecurityLog).where(and_(*conditions))
    total = (await db.execute(count_q)).scalar_one()

    q = (
        select(SecurityLog)
        .where(and_(*conditions))
        .order_by(SecurityLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(q)).scalars().all()

    return LogListResponse(
        items=[LogOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_stats(db: AsyncSession, tenant_id: UUID) -> dict:
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total_q = select(func.count()).select_from(SecurityLog).where(
        SecurityLog.tenant_id == tenant_id,
        SecurityLog.created_at >= today_start,
    )
    total = (await db.execute(total_q)).scalar_one()

    high_q = select(func.count()).select_from(SecurityLog).where(
        SecurityLog.tenant_id == tenant_id,
        SecurityLog.severity.in_(["high", "critical"]),
        SecurityLog.created_at >= today_start,
    )
    high = (await db.execute(high_q)).scalar_one()

    med_q = select(func.count()).select_from(SecurityLog).where(
        SecurityLog.tenant_id == tenant_id,
        SecurityLog.severity == "medium",
        SecurityLog.created_at >= today_start,
    )
    medium = (await db.execute(med_q)).scalar_one()

    avg_q = select(func.avg(SecurityLog.anomaly_score)).where(
        SecurityLog.tenant_id == tenant_id,
        SecurityLog.created_at >= today_start,
    )
    avg_score = (await db.execute(avg_q)).scalar_one() or 0.0

    return {
        "total_today": total,
        "high_severity": high,
        "medium_severity": medium,
        "anomaly_score_avg": round(float(avg_score), 4),
        "active_tenants": 1,
    }


async def get_timeseries(db: AsyncSession, tenant_id: UUID, hours: int = 12) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    q = (
        select(
            func.date_trunc("hour", SecurityLog.created_at).label("hour"),
            func.count().label("total"),
            func.sum(
                func.cast(SecurityLog.severity.in_(["high", "critical"]), type_=None)
            ).label("high"),
        )
        .where(
            SecurityLog.tenant_id == tenant_id,
            SecurityLog.created_at >= since,
        )
        .group_by("hour")
        .order_by("hour")
    )
    rows = (await db.execute(q)).all()
    return [
        {"hour": r.hour.strftime("%H:00"), "total": r.total, "high": int(r.high or 0)}
        for r in rows
    ]
