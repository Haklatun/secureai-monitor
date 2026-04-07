from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_access_token
from app.db.session import get_db, tenant_session, AsyncSession
from sqlalchemy import select, text

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user_payload(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = verify_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return payload


async def get_current_tenant_id(
    payload: Annotated[dict, Depends(get_current_user_payload)],
) -> UUID:
    return UUID(payload["tenant_id"])


async def require_admin(
    payload: Annotated[dict, Depends(get_current_user_payload)],
) -> dict:
    if payload.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return payload


async def get_tenant_db(
    tenant_id: Annotated[UUID, Depends(get_current_tenant_id)],
):
    """Yields a session with RLS tenant_id set."""
    async with tenant_session(tenant_id) as db:
        yield db


CurrentPayload = Annotated[dict, Depends(get_current_user_payload)]
TenantID = Annotated[UUID, Depends(get_current_tenant_id)]
TenantDB = Annotated[AsyncSession, Depends(get_tenant_db)]
