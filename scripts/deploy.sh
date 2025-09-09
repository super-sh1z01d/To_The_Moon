#!/usr/bin/env bash
set -euo pipefail

# Simple git-based deploy script (no Docker)
# Usage: on server, run from repo root: bash scripts/deploy.sh

APP_DIR=${APP_DIR:-$(pwd)}
PY=${PY:-}

echo "[deploy] repo: $APP_DIR"
cd "$APP_DIR"

echo "[deploy] git update"
set +e
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
UPSTREAM_OK=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} >/dev/null 2>&1; echo $?)
set -e
if [ "$UPSTREAM_OK" = "0" ]; then
  git pull --ff-only
else
  echo "[deploy] no upstream; fetching origin/main and checking out local main"
  git fetch origin main
  git checkout -B main origin/main
fi

if [ -z "$PY" ]; then
  if [ -x "venv/bin/python" ]; then
    PY="venv/bin/python"
  else
    echo "[deploy] create venv"
    python3 -m venv venv
    PY="venv/bin/python"
  fi
fi

echo "[deploy] install python deps ($PY)"
$PY -m pip install --upgrade pip
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

# Health check
sleep 3
if command -v curl >/dev/null 2>&1; then
  echo "[deploy] health check"
  set +e
  curl -fsS http://127.0.0.1:8000/health && echo "[deploy] HEALTH OK" || {
    echo "[deploy] HEALTH FAILED";
    systemctl status tothemoon.service || true;
    exit 1;
  }
  set -e
fi

echo "[deploy] done"
