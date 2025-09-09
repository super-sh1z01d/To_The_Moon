#!/usr/bin/env bash
set -euo pipefail

# Simple git-based deploy script (no Docker)
# Usage: on server, run from repo root: bash scripts/deploy.sh

APP_DIR=${APP_DIR:-$(pwd)}
PY=${PY:-python3}

echo "[deploy] repo: $APP_DIR"
cd "$APP_DIR"

echo "[deploy] git pull"
git pull --ff-only

echo "[deploy] install python deps"
$PY -m pip install -r requirements.txt

echo "[deploy] alembic upgrade head"
$PY -m alembic upgrade head

if [ -d frontend ]; then
  echo "[deploy] build frontend"
  (cd frontend && npm ci && npm run build)
fi

if command -v systemctl >/dev/null 2>&1; then
  echo "[deploy] restarting services"
  sudo systemctl restart tothemoon.service || true
  sudo systemctl restart tothemoon-ws.service || true
else
  echo "[deploy] systemctl not found; restart uvicorn manually if needed"
fi

echo "[deploy] done"

