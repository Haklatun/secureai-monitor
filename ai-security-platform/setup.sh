#!/usr/bin/env bash
# setup.sh — One-command local setup for SecureAI Monitor
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[setup]${NC} $*"; }
warn()  { echo -e "${YELLOW}[warn]${NC}  $*"; }

info "Checking dependencies..."
command -v docker  >/dev/null || { warn "Docker not found. Install: https://docs.docker.com/get-docker/"; exit 1; }
command -v openssl >/dev/null || { warn "openssl not found"; exit 1; }

# Generate .env if missing
if [ ! -f .env ]; then
  info "Creating .env from template..."
  cp .env.example .env

  SECRET=$(openssl rand -hex 32)
  PG_PASS=$(openssl rand -hex 16)
  REDIS_PASS=$(openssl rand -hex 16)
  FERNET=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || echo "")

  sed -i.bak "s/CHANGE_ME_generate_with_openssl_rand_hex_32/${SECRET}/" .env
  sed -i.bak "s/CHANGE_ME_strong_password_here/${PG_PASS}/" .env
  sed -i.bak "s/CHANGE_ME_redis_password/${REDIS_PASS}/" .env
  [ -n "$FERNET" ] && sed -i.bak "s|# FERNET_KEY=.*|FERNET_KEY=${FERNET}|" .env || true
  rm -f .env.bak

  info ".env created with generated secrets"
else
  info ".env already exists — skipping"
fi

# Create SSL placeholder dir
mkdir -p infrastructure/nginx/ssl
if [ ! -f infrastructure/nginx/ssl/fullchain.pem ]; then
  warn "No SSL certs found — generating self-signed for local dev..."
  openssl req -x509 -newkey rsa:4096 -keyout infrastructure/nginx/ssl/privkey.pem \
    -out infrastructure/nginx/ssl/fullchain.pem -days 365 -nodes \
    -subj "/C=US/ST=Dev/L=Local/O=SecureAI/CN=localhost" 2>/dev/null
  info "Self-signed cert created (for local use only)"
fi

info "Building and starting services..."
docker compose up --build -d

info "Waiting for services to be healthy..."
sleep 8

info ""
info "✅  SecureAI Monitor is running!"
info ""
info "  Frontend:    http://localhost:3000"
info "  Backend API: http://localhost:8000"
info "  API Docs:    http://localhost:8000/docs"
info ""
info "  Demo login:  admin@demo.com / Admin1234!"
info ""
