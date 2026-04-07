-- ============================================================
-- SecureAI Monitor — Database Initialization
-- PostgreSQL 16 + pgvector + pgcrypto
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- ============================================================
-- TENANTS
-- ============================================================
CREATE TABLE IF NOT EXISTS tenants (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT NOT NULL,
    slug        TEXT NOT NULL UNIQUE,
    plan        TEXT NOT NULL DEFAULT 'free' CHECK (plan IN ('free','pro','enterprise')),
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email           TEXT NOT NULL,
    -- bcrypt hash stored via pgcrypto
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'analyst' CHECK (role IN ('admin','analyst','viewer')),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, email)
);

CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_email  ON users(email);

-- ============================================================
-- SECURITY LOGS
-- ============================================================
CREATE TABLE IF NOT EXISTS security_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL,
    severity        TEXT NOT NULL DEFAULT 'low' CHECK (severity IN ('low','medium','high','critical')),
    source_ip       TEXT,
    -- Encrypted sensitive payload (pgcrypto symmetric)
    raw_payload     BYTEA,
    user_agent      TEXT,
    endpoint        TEXT,
    status_code     INT,
    anomaly_score   FLOAT CHECK (anomaly_score BETWEEN 0 AND 1),
    is_anomaly      BOOLEAN NOT NULL DEFAULT FALSE,
    -- pgvector embedding (384-dim all-MiniLM default)
    embedding       vector(384),
    metadata        JSONB DEFAULT '{}',
    resolved        BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_by     UUID REFERENCES users(id),
    resolved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_logs_tenant     ON security_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_logs_severity   ON security_logs(severity);
CREATE INDEX IF NOT EXISTS idx_logs_created    ON security_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_logs_anomaly    ON security_logs(is_anomaly) WHERE is_anomaly = TRUE;
CREATE INDEX IF NOT EXISTS idx_logs_source_ip  ON security_logs(source_ip);
-- Vector index for similarity search
CREATE INDEX IF NOT EXISTS idx_logs_embedding  ON security_logs USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ============================================================
-- REFRESH TOKENS
-- ============================================================
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  TEXT NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_refresh_user ON refresh_tokens(user_id);

-- ============================================================
-- AUDIT LOG (immutable, no RLS — admins only)
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   UUID,
    user_id     UUID,
    action      TEXT NOT NULL,
    resource    TEXT,
    ip_address  TEXT,
    details     JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_tenant  ON audit_log(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at DESC);

-- ============================================================
-- BLOCKED IPS (auto-response)
-- ============================================================
CREATE TABLE IF NOT EXISTS blocked_ips (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    ip_address  TEXT NOT NULL,
    reason      TEXT,
    blocked_by  UUID REFERENCES users(id),
    expires_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, ip_address)
);

-- ============================================================
-- ROW-LEVEL SECURITY
-- ============================================================
ALTER TABLE security_logs  ENABLE ROW LEVEL SECURITY;
ALTER TABLE users           ENABLE ROW LEVEL SECURITY;
ALTER TABLE blocked_ips     ENABLE ROW LEVEL SECURITY;
ALTER TABLE refresh_tokens  ENABLE ROW LEVEL SECURITY;

-- App role used by the backend connection pool
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'secureai_app') THEN
    CREATE ROLE secureai_app LOGIN PASSWORD 'app_role_password_change_me';
  END IF;
END $$;

GRANT CONNECT ON DATABASE secureai_db TO secureai_app;
GRANT USAGE ON SCHEMA public TO secureai_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO secureai_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO secureai_app;

-- Policies: rows only visible to matching tenant
CREATE POLICY tenant_isolation_logs ON security_logs
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);

CREATE POLICY tenant_isolation_users ON users
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);

CREATE POLICY tenant_isolation_blocked ON blocked_ips
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);

CREATE POLICY tenant_isolation_tokens ON refresh_tokens
    USING (user_id IN (
        SELECT id FROM users
        WHERE tenant_id = current_setting('app.tenant_id', TRUE)::UUID
    ));

-- ============================================================
-- SEED: Demo tenant + admin user (password: Admin1234!)
-- ============================================================
INSERT INTO tenants (id, name, slug, plan) VALUES
    ('00000000-0000-0000-0000-000000000001', 'Demo Corp', 'demo', 'pro')
ON CONFLICT DO NOTHING;

INSERT INTO users (tenant_id, email, password_hash, role) VALUES
    ('00000000-0000-0000-0000-000000000001',
     'admin@demo.com',
     crypt('Admin1234!', gen_salt('bf', 12)),
     'admin')
ON CONFLICT DO NOTHING;
