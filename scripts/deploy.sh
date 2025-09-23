#!/usr/bin/env bash
set -euo pipefail

# Git-based deploy script with System Stability Monitoring
# Usage: on server, run from repo root: bash scripts/deploy.sh

APP_DIR=${APP_DIR:-$(pwd)}
APP_USER=${APP_USER:-tothemoon}
ENV_FILE=${ENV_FILE:-/etc/tothemoon.env}
PY=${PY:-}

echo "🚀 [deploy] To The Moon with System Stability Monitoring"
echo "📅 [deploy] Started at: $(date)"

echo "[deploy] repo: $APP_DIR"
cd "$APP_DIR"

echo "[deploy] git update"
# Ensure ownership to avoid git safe.directory errors when run as root
if [ "$(id -u)" = "0" ]; then
  chown -R "$APP_USER":"$APP_USER" "$APP_DIR" || true
fi
# Mark directory as safe for git under app user
sudo -u "$APP_USER" git config --global --add safe.directory "$APP_DIR" >/dev/null 2>&1 || true
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

echo "📦 [deploy] install python deps ($PY)"
sudo -u "$APP_USER" $PY -m pip install --upgrade pip
sudo -u "$APP_USER" $PY -m pip install -r requirements.txt

echo "📊 [deploy] install monitoring dependencies"
sudo -u "$APP_USER" $PY -m pip install psutil

echo "🔍 [deploy] test monitoring components"
sudo -u "$APP_USER" bash -lc "set -a; [ -f '$ENV_FILE' ] && sed -e '/^#/d' -e '/^$/d' '$ENV_FILE' > /tmp/.tmoonenva && source /tmp/.tmoonenva; rm -f /tmp/.tmoonenva; set +a; cd '$APP_DIR' && '$PY' -c '
import sys
sys.path.append(\".\")
try:
    from src.monitoring.health_monitor import get_health_monitor
    from src.monitoring.metrics import get_performance_tracker
    from src.monitoring.alert_manager import get_alert_manager
    from src.scheduler.monitoring import get_priority_processor
    print(\"✅ All monitoring modules imported successfully\")
except Exception as e:
    print(f\"❌ Monitoring module import failed: {e}\")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'"

echo "🗄️  [deploy] alembic upgrade head"
# Load env variables safely (ignore comments/blank lines) and run alembic
sudo -u "$APP_USER" bash -lc "set -a; [ -f '$ENV_FILE' ] && sed -e '/^#/d' -e '/^$/d' '$ENV_FILE' > /tmp/.tmoonenva && source /tmp/.tmoonenva; rm -f /tmp/.tmoonenva; set +a; cd '$APP_DIR' && '$PY' -m alembic upgrade head"

if [ -d frontend ]; then
  echo "🎨 [deploy] build frontend"
  sudo -u "$APP_USER" bash -lc 'cd frontend && npm ci && npm run build'
fi

if command -v systemctl >/dev/null 2>&1; then
  echo "🔄 [deploy] restarting services with monitoring"
  if [ "$(id -u)" = "0" ]; then
    systemctl restart tothemoon.service || true
    systemctl restart tothemoon-ws.service || true
  else
    sudo systemctl restart tothemoon.service || true
    sudo systemctl restart tothemoon-ws.service || true
  fi
  
  # Wait for services to start
  echo "⏳ [deploy] waiting for services to start..."
  sleep 10
else
  echo "⚠️  [deploy] systemctl not found; restart uvicorn manually if needed"
fi

# Comprehensive health check with monitoring
if command -v curl >/dev/null 2>&1; then
  echo "🏥 [deploy] comprehensive health check"
  set +e
  
  # Test main health endpoint
  curl -fsS http://127.0.0.1:8000/health && echo "✅ [deploy] Main health: OK" || {
    echo "❌ [deploy] Main health: FAILED";
    systemctl status tothemoon.service || true;
    exit 1;
  }
  
  # Test monitoring endpoints
  curl -fsS http://127.0.0.1:8000/health/scheduler >/dev/null && echo "✅ [deploy] Scheduler monitoring: OK" || echo "⚠️  [deploy] Scheduler monitoring: DEGRADED"
  curl -fsS http://127.0.0.1:8000/health/resources >/dev/null && echo "✅ [deploy] Resources monitoring: OK" || echo "⚠️  [deploy] Resources monitoring: DEGRADED"
  curl -fsS http://127.0.0.1:8000/health/performance >/dev/null && echo "✅ [deploy] Performance monitoring: OK" || echo "⚠️  [deploy] Performance monitoring: DEGRADED"
  curl -fsS http://127.0.0.1:8000/health/priority >/dev/null && echo "✅ [deploy] Priority processing: OK" || echo "⚠️  [deploy] Priority processing: DEGRADED"
  
  set -e
fi

echo ""
echo "🎉 [deploy] System Stability Monitoring deployment completed!"
echo "📊 [deploy] Monitoring endpoints available:"
echo "   - Main health: http://127.0.0.1:8000/health"
echo "   - Scheduler: http://127.0.0.1:8000/health/scheduler"
echo "   - Resources: http://127.0.0.1:8000/health/resources"
echo "   - Performance: http://127.0.0.1:8000/health/performance"
echo "   - Priority: http://127.0.0.1:8000/health/priority"
echo ""
echo "📋 [deploy] Management commands:"
echo "   - Status: systemctl status tothemoon.service"
echo "   - Logs: journalctl -u tothemoon.service -f"
echo "   - Restart: systemctl restart tothemoon.service"
echo ""
