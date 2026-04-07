from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    verify_password, hash_password,
    create_access_token, create_refresh_token, hash_token,
)
from app.core.config import get_settings
from app.db.models import User, RefreshToken, Tenant
from app.models.schemas import LoginRequest, TokenResponse, UserCreate

settings = get_settings()


async def authenticate_user(db: AsyncSession, login: LoginRequest) -> User | None:
    q = select(User).where(User.email == login.email, User.is_active == True)
    user = (await db.execute(q)).scalar_one_or_none()
    if not user or not verify_password(login.password, user.password_hash):
        return None
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    return user


async def create_tokens(db: AsyncSession, user: User) -> TokenResponse:
    payload = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "role": user.role,
        "email": user.email,
    }
    access = create_access_token(payload)
    refresh, refresh_hash = create_refresh_token(payload)

    from datetime import timedelta
    expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

    token_row = RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=expires,
    )
    db.add(token_row)
    await db.commit()

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


async def rotate_refresh_token(
    db: AsyncSession, old_refresh: str
) -> TokenResponse | None:
    token_hash = hash_token(old_refresh)
    q = select(RefreshToken).where(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked == False,
        RefreshToken.expires_at > datetime.now(timezone.utc),
    )
    row = (await db.execute(q)).scalar_one_or_none()
    if not row:
        return None

    # Revoke old token (rotation)
    row.revoked = True
    await db.flush()

    user = (await db.execute(select(User).where(User.id == row.user_id))).scalar_one()
    return await create_tokens(db, user)


async def revoke_all_tokens(db: AsyncSession, user_id: UUID) -> None:
    from sqlalchemy import update
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id)
        .values(revoked=True)
    )
    await db.commit()


async def create_user(
    db: AsyncSession, tenant_id: UUID, data: UserCreate
) -> User:
    user = User(
        tenant_id=tenant_id,
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
