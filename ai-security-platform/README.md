# SecureAI Monitor — Production-Grade AI Security Platform

A multi-tenant, AI-powered security monitoring SaaS built with FastAPI, Next.js, PostgreSQL + pgvector, and scikit-learn.

---

## Architecture

```
Internet → Nginx (SSL/rate-limit) → FastAPI backend ←→ PostgreSQL (RLS)
                                 → Next.js frontend         ↕
                                 → WebSocket alerts      Redis (rate-limit)
                                 → AI Engine (IsolationForest + embeddings)
```

---

## Quick Start (Local)

### 1. Clone and configure

```bash
git clone <repo>
cd ai-security-platform
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY, POSTGRES_PASSWORD, REDIS_PASSWORD
openssl rand -hex 32   # paste output as SECRET_KEY
```

### 2. Start all services

```bash
docker compose up --build
```

Services start at:
- Frontend:  http://localhost:3000
- Backend API: http://localhost:8000
- API docs:  http://localhost:8000/docs
- PostgreSQL: localhost:5432

### 3. Demo login

| Field    | Value           |
|----------|-----------------|
| Email    | admin@demo.com  |
| Password | Admin1234!      |

---

## Project Structure

```
ai-security-platform/
├── backend/
│   ├── app/
│   │   ├── api/          # Route handlers (auth, logs, websocket)
│   │   ├── core/         # Config, JWT security, WebSocket manager
│   │   ├── db/           # SQLAlchemy session, ORM models
│   │   ├── models/       # Pydantic schemas (input/output validation)
│   │   └── services/     # AI engine, log service, auth service
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── app/          # Next.js 14 App Router pages
│       ├── components/   # UI, charts, logs components
│       └── lib/          # API client, WebSocket hook
├── infrastructure/
│   ├── nginx/            # Reverse proxy + SSL config
│   └── postgres/         # DB init SQL (extensions, RLS, seed)
├── .github/workflows/    # CI/CD pipeline
├── docker-compose.yml
└── .env.example
```

---

## Security Features

| Feature | Implementation |
|---------|----------------|
| Multi-tenant isolation | PostgreSQL Row-Level Security (RLS) per tenant |
| Authentication | JWT access tokens (15 min) + refresh tokens (7 days) |
| Password storage | bcrypt (cost factor 12) via passlib |
| Sensitive data | Encrypted with Fernet (AES-128-CBC) in DB |
| Input validation | Pydantic v2 strict schemas on all endpoints |
| Rate limiting | slowapi (30 req/min API, 5 req/min auth) + Nginx zones |
| Transport | TLS 1.2/1.3 via Nginx, HSTS enabled |
| Headers | X-Frame-Options, CSP, X-Content-Type-Options |
| SQL injection | SQLAlchemy parameterized queries only |
| Token rotation | Refresh token rotated on every use |

---

## AI Detection Engine

The engine runs a 3-step pipeline on every ingested log:

1. **Embed** — converts the log event + payload into a 384-dim vector using `all-MiniLM-L6-v2` (sentence-transformers)
2. **Score** — feeds the embedding through an Isolation Forest trained on recent traffic; outputs an anomaly score in [0, 1]
3. **Classify** — combines the score with rule-based heuristics (keyword matching, HTTP status codes) to assign `low / medium / high / critical`

Anomalous events (score ≥ threshold, default 0.65) are:
- Flagged in the database
- Broadcast over tenant-scoped WebSocket connections
- Highlighted in the dashboard with real-time toast notifications

To retrain the model on recent data, call:

```python
from app.services.ai_engine import retrain
await retrain(embeddings_list)  # list of 384-dim float arrays
```

---

## API Reference

### Auth

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | Email/password → JWT tokens |
| POST | `/api/auth/refresh` | Rotate refresh token |
| POST | `/api/auth/logout` | Revoke all refresh tokens |
| GET  | `/api/auth/me` | Current user info |

### Logs

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/logs` | Ingest a log event (runs AI pipeline) |
| GET  | `/api/logs` | List logs (filterable, paginated) |
| GET  | `/api/logs/stats` | Summary stats for dashboard |
| GET  | `/api/logs/timeseries` | Hourly event counts |
| PATCH | `/api/logs/{id}/resolve` | Mark log as resolved |

### WebSocket

```
ws://host/ws/alerts?token=<access_token>
```

Receives JSON alerts for anomalous events in real time, scoped per tenant.

---

## Production Deployment (AWS / DigitalOcean)

### 1. Provision server

Minimum: 2 vCPU, 4 GB RAM (DigitalOcean Droplet or AWS t3.medium)

```bash
# On the server
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git
sudo usermod -aG docker $USER
```

### 2. Configure DNS + SSL

```bash
# Point your domain A record to the server IP
# Then generate SSL cert
sudo apt install certbot
sudo certbot certonly --standalone -d yourdomain.com
# Certs land at /etc/letsencrypt/live/yourdomain.com/
# Copy to ./infrastructure/nginx/ssl/
```

### 3. Deploy

```bash
git clone <repo> /opt/secureai && cd /opt/secureai
cp .env.example .env && nano .env   # fill in real secrets
docker compose -f docker-compose.yml up -d
```

### 4. Managed PostgreSQL (recommended)

Replace the `postgres` service in `docker-compose.yml` with a connection string to AWS RDS or DigitalOcean Managed PostgreSQL. Enable the pgvector and pgcrypto extensions manually:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

### 5. Monitoring

Add Prometheus + Grafana by extending `docker-compose.yml`:

```yaml
prometheus:
  image: prom/prometheus
  volumes:
    - ./infrastructure/prometheus.yml:/etc/prometheus/prometheus.yml

grafana:
  image: grafana/grafana
  ports: ["3001:3000"]
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✅ | JWT signing key — generate with `openssl rand -hex 32` |
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://user:pass@host/db` |
| `POSTGRES_PASSWORD` | ✅ | PostgreSQL password |
| `REDIS_PASSWORD` | ✅ | Redis password |
| `ALLOWED_ORIGINS` | ✅ | CORS origins (comma-separated) |
| `ANOMALY_THRESHOLD` | — | Anomaly score cutoff (default: 0.65) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | — | JWT lifetime (default: 15) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | — | Refresh token lifetime (default: 7) |
| `ALERT_WEBHOOK_URL` | — | Slack/Discord webhook for alerts |

---

## License

MIT — free to use, modify, and deploy commercially.
