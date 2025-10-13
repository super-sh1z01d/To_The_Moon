#!/bin/bash
set -euo pipefail

SERVER_IP="67.213.119.189"
SERVER_USER="ubuntu"
SERVER_PASS="fjfii3ddkcAAlccCld124k"

if ! command -v sshpass >/dev/null 2>&1; then
  echo "Устанавливаю sshpass..."
  if command -v brew >/dev/null 2>&1; then
    brew install hudochenkov/sshpass/sshpass
  else
    echo "brew не найден, установите sshpass вручную" >&2
    exit 1
  fi
fi

echo "🔗 Обновляю код на ${SERVER_USER}@${SERVER_IP}..."
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" "SUDO_PASS='$SERVER_PASS' bash -s" <<'REMOTE'
set -euo pipefail

run_sudo() {
  printf '%s\n' "$SUDO_PASS" | sudo -S -p '' "$@"
}

cd /srv/tothemoon
run_sudo git fetch origin
run_sudo git reset --hard origin/main
printf "HEAD → %s\n" "$(run_sudo git rev-parse HEAD)"

echo "🛠️ Сборка фронтенда"
run_sudo rm -rf /srv/tothemoon/frontend/node_modules
run_sudo rm -rf /srv/tothemoon/frontend/dist
run_sudo -u tothemoon bash -lc 'cd /srv/tothemoon/frontend && npm ci && npm run build'
REMOTE

echo "🚀 Перезапуск to-the-moon.service"
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" \
  "printf '%s\n' '$SERVER_PASS' | sudo -S -p '' systemctl restart tothemoon.service"

echo "🚀 Перезапуск to-the-moon-ws.service (ожидайте обрыв соединения)"
if ! sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" \
  "printf '%s\n' '$SERVER_PASS' | sudo -S -p '' systemctl restart tothemoon-ws.service"; then
  echo "ℹ️  Перезапуск ws-сервиса оборвал SSH — это ожидаемо."
fi

echo "⏳ Жду 5 секунд..."
sleep 5

check_status() {
  local service="$1"
  local attempts=6
  local status=""
  local i=1
  while (( i <= attempts )); do
    status=$(sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" \
      "printf '%s\n' '$SERVER_PASS' | sudo -S -p '' systemctl is-active $service" 2>/dev/null || true)
    if [[ "$status" == "active" ]]; then
      echo "✅ $service: $status"
      return 0
    fi
    echo "⏳ $service: $status (попытка $i/$attempts)"
    sleep 5
    ((i++))
  done
  echo "⚠️  $service так и не перешёл в active (последний статус: $status)"
  return 1
}

check_status "tothemoon.service"
check_status "tothemoon-ws.service"

echo "🎉 Обновление удалённого сервера завершено"
