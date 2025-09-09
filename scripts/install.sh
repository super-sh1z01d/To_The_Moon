#!/usr/bin/env bash
set -euo pipefail

# To The Moon — one-click-ish installer (Debian/Ubuntu friendly)
# - Creates system user/group `tothemoon`
# - Clones/pulls repo into /srv/tothemoon (or uses existing)
# - Creates Python venv, installs deps, applies Alembic migrations
# - Builds SPA if Node is available
# - Installs & starts systemd services (API + WS worker)
# - Performs health check

REPO_URL=${REPO_URL:-"https://github.com/super-sh1z01d/To_The_Moon.git"}
APP_USER=${APP_USER:-tothemoon}
APP_GROUP=${APP_GROUP:-$APP_USER}
APP_DIR=${APP_DIR:-/srv/tothemoon}
ENV_FILE=${ENV_FILE:-/etc/tothemoon.env}

log() { echo "[install] $*"; }

need_root() {
  if [ "$(id -u)" -ne 0 ]; then
    echo "Run as root: sudo bash scripts/install.sh" >&2; exit 1
  fi
}

ensure_packages() {
  if command -v apt-get >/dev/null 2>&1; then
    log "installing system packages (python3, venv, pip, git, curl)"
    apt-get update -y
    DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip git curl || true
  else
    log "apt-get not found; ensure python3/git/curl installed manually"
  fi
}

ensure_user() {
  if ! id -u "$APP_USER" >/dev/null 2>&1; then
    log "creating user $APP_USER"
    useradd -r -m -d "$APP_DIR" -s /bin/bash "$APP_USER"
  else
    log "user $APP_USER exists"
  fi
}

ensure_repo() {
  mkdir -p "$APP_DIR"
  chown -R "$APP_USER":"$APP_GROUP" "$APP_DIR"
  if [ ! -d "$APP_DIR/.git" ]; then
    log "cloning repo to $APP_DIR"
    sudo -u "$APP_USER" git clone "$REPO_URL" "$APP_DIR"
  else
    log "updating repo"
    (cd "$APP_DIR" && sudo -u "$APP_USER" git fetch --all && sudo -u "$APP_USER" git reset --hard origin/main)
  fi
}

ensure_env() {
  if [ ! -f "$ENV_FILE" ]; then
    log "creating $ENV_FILE (default values)"
    cat >"$ENV_FILE" <<'ENV'
APP_ENV=prod
LOG_LEVEL=INFO
# Use PostgreSQL in production; for quick start you may use sqlite (not recommended for prod)
# DATABASE_URL=postgresql+psycopg2://user:pass@127.0.0.1:5432/tothemoon
DATABASE_URL=sqlite:///dev.db
FRONTEND_DIST_PATH=/srv/tothemoon/frontend/dist
SCHEDULER_ENABLED=true
ENV
  else
    log "$ENV_FILE exists"
  fi
}

setup_python() {
  log "creating venv and installing python deps"
  cd "$APP_DIR"
  if [ ! -x "venv/bin/python" ]; then
    sudo -u "$APP_USER" python3 -m venv venv
  fi
  sudo -u "$APP_USER" venv/bin/python -m pip install --upgrade pip
  sudo -u "$APP_USER" venv/bin/python -m pip install -r requirements.txt
}

run_migrations() {
  log "running alembic migrations"
  cd "$APP_DIR"
  sudo -u "$APP_USER" env "$(cat "$ENV_FILE" | xargs)" venv/bin/python -m alembic upgrade head
}

build_frontend() {
  cd "$APP_DIR"
  if [ -d frontend ]; then
    if command -v npm >/dev/null 2>&1; then
      log "building frontend"
      (cd frontend && sudo -u "$APP_USER" npm ci && sudo -u "$APP_USER" npm run build)
    else
      log "npm not found; skipping SPA build (minimal /ui будет доступен)"
    fi
  fi
}

install_systemd() {
  log "installing systemd units"
  install -m 0644 "$APP_DIR"/scripts/systemd/tothemoon.service /etc/systemd/system/tothemoon.service
  install -m 0644 "$APP_DIR"/scripts/systemd/tothemoon-ws.service /etc/systemd/system/tothemoon-ws.service
  systemctl daemon-reload
  systemctl enable tothemoon.service tothemoon-ws.service
  systemctl restart tothemoon.service tothemoon-ws.service
}

health_check() {
  sleep 2
  if command -v curl >/dev/null 2>&1; then
    log "health check"
    if curl -fsS http://127.0.0.1:8000/health >/dev/null; then
      log "HEALTH OK"
    else
      log "HEALTH FAILED, printing last logs"
      journalctl -u tothemoon.service --no-pager -n 200 || true
      exit 1
    fi
  fi
}

need_root
ensure_packages
ensure_user
ensure_repo
ensure_env
setup_python
run_migrations
build_frontend
install_systemd
health_check

log "install completed"

