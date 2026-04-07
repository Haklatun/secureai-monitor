import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, LargeBinary, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.db.session import Base


def utcnow():
    return datetime.now(timezone.utc)


class Tenant(Base):
    __tablename__ = "tenants"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name       = Column(Text, nullable=False)
    slug       = Column(Text, nullable=False, unique=True)
    plan       = Column(String(20), nullable=False, default="free")
    is_active  = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    logs  = relationship("SecurityLog", back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "email"),)

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id     = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    email         = Column(Text, nullable=False)
    password_hash = Column(Text, nullable=False)
    role          = Column(String(20), nullable=False, default="analyst")
    is_active     = Column(Boolean, nullable=False, default=True)
    last_login_at = Column(DateTime(timezone=True))
    created_at    = Column(DateTime(timezone=True), default=utcnow)
    updated_at    = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant         = relationship("Tenant", back_populates="users")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class SecurityLog(Base):
    __tablename__ = "security_logs"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id     = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    event_type    = Column(Text, nullable=False)
    severity      = Column(String(20), nullable=False, default="low")
    source_ip     = Column(Text)
    raw_payload   = Column(LargeBinary)          # encrypted via pgcrypto
    user_agent    = Column(Text)
    endpoint      = Column(Text)
    status_code   = Column(Integer)
    anomaly_score = Column(Float)
    is_anomaly    = Column(Boolean, nullable=False, default=False)
    embedding     = Column(Vector(384))
    metadata_     = Column("metadata", JSONB, default=dict)
    resolved      = Column(Boolean, nullable=False, default=False)
    resolved_by   = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolved_at   = Column(DateTime(timezone=True))
    created_at    = Column(DateTime(timezone=True), default=utcnow)

    tenant = relationship("Tenant", back_populates="logs")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(Text, nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked    = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="refresh_tokens")


class BlockedIP(Base):
    __tablename__ = "blocked_ips"
    __table_args__ = (UniqueConstraint("tenant_id", "ip_address"),)

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id  = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    ip_address = Column(Text, nullable=False)
    reason     = Column(Text)
    blocked_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow)
