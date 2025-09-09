#!/usr/bin/env bash
set -euo pipefail

# Simple git-based deploy script (no Docker)
# Usage: on server, run from repo root: bash scripts/deploy.sh

APP_DIR=${APP_DIR:-$(pwd)}
APP_USER=${APP_USER:-tothemoon}
ENV_FILE=${ENV_FILE:-/etc/tothemoon.env}
PY=${PY:-}

echo "[deploy] repo: $APP_DIR"
cd "$APP_DIR"

echo "[deploy] git update"
# Run git as app user to avoid safe.directory issues
if sudo -u "$APP_USER" test -d .git; then
  set +e
  UPSTREAM_OK=$(sudo -u "$APP_USER" git rev-parse --abbrev-ref --symbolic-full-name @{u} >/dev/null 2>&1; echo $?)
  set -e
  if [ "$UPSTREAM_OK" = "0" ]; then
    sudo -u "$APP_USER" git pull --ff-only
  else
    echo "[deploy] no upstream; fetching origin/main and checking out local main"
    sudo -u "$APP_USER" git fetch origin main
    sudo -u "$APP_USER" git checkout -B main origin/main
  fi
else
  echo "[deploy] not a git repo; initializing"
  sudo -u "$APP_USER" git init
  sudo -u "$APP_USER" git remote add origin https://github.com/super-sh1z01d/To_The_Moon.git 2>/dev/null || \
    sudo -u "$APP_USER" git remote set-url origin https://github.com/super-sh1z01d/To_The_Moon.git
  sudo -u "$APP_USER" git fetch origin main
  sudo -u "$APP_USER" git checkout -B main origin/main
fi

if [ -z "$PY" ]; then
  if [ -x "venv/bin/python" ]; then
    PY="venv/bin/python"
  else
    echo "[deploy] create venv"
    sudo -u "$APP_USER" python3 -m venv venv
    PY="venv/bin/python"
  fi
fi

echo "[deploy] install python deps ($PY)"
sudo -u "$APP_USER" $PY -m pip install --upgrade pip
sudo -u "$APP_USER" $PY -m pip install -r requirements.txt

echo "[deploy] alembic upgrade head"
sudo -u "$APP_USER" env $(cat "$ENV_FILE" | xargs) $PY -m alembic upgrade head

if [ -d frontend ]; then
  echo "[deploy] build frontend"
  sudo -u "$APP_USER" bash -lc 'cd frontend && npm ci && npm run build'
fi

if command -v systemctl >/dev/null 2>&1; then
  echo "[deploy] restarting services"
  if [ "$(id -u)" = "0" ]; then
    systemctl restart tothemoon.service || true
    systemctl restart tothemoon-ws.service || true
  else
    sudo systemctl restart tothemoon.service || true
    sudo systemctl restart tothemoon-ws.service || true
  fi
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
