from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_payload, CurrentPayload
from app.db.session import get_db
from app.models.schemas import LoginRequest, TokenResponse, RefreshRequest, UserCreate, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await auth_service.authenticate_user(db, body)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return await auth_service.create_tokens(db, user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    result = await auth_service.rotate_refresh_token(db, body.refresh_token)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    return result


@router.post("/logout", status_code=204)
async def logout(
    payload: CurrentPayload,
    db: AsyncSession = Depends(get_db),
):
    from uuid import UUID
    await auth_service.revoke_all_tokens(db, UUID(payload["sub"]))


@router.get("/me", response_model=UserOut)
async def me(
    payload: CurrentPayload,
    db: AsyncSession = Depends(get_db),
):
    from uuid import UUID
    from sqlalchemy import select
    from app.db.models import User
    user = (
        await db.execute(select(User).where(User.id == UUID(payload["sub"])))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
