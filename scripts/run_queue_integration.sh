#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-ttm-pg-integration}"
PORT="${PG_INT_PORT:-55432}"
PG_USER="${PG_USER:-ttm}"
PG_PASSWORD="${PG_PASSWORD:-ttm}"
PG_DB="${PG_DB:-tothemoon_int}"

cleanup() {
  docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

cleanup

echo "Starting PostgreSQL container ${CONTAINER_NAME} on port ${PORT}..."
docker run -d \
  --name "${CONTAINER_NAME}" \
  -e POSTGRES_USER="${PG_USER}" \
  -e POSTGRES_PASSWORD="${PG_PASSWORD}" \
  -e POSTGRES_DB="${PG_DB}" \
  -p "${PORT}:5432" \
  postgres:16-alpine >/dev/null

echo "Waiting for PostgreSQL to become ready..."
for _ in $(seq 1 40); do
  if docker exec "${CONTAINER_NAME}" pg_isready -U "${PG_USER}" -d "${PG_DB}" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! docker exec "${CONTAINER_NAME}" pg_isready -U "${PG_USER}" -d "${PG_DB}" >/dev/null 2>&1; then
  echo "PostgreSQL did not become ready in time"
  exit 1
fi

export INTEGRATION_DATABASE_URL="postgresql+psycopg2://${PG_USER}:${PG_PASSWORD}@localhost:${PORT}/${PG_DB}"
echo "Running integration tests against ${INTEGRATION_DATABASE_URL}"

if [[ "$#" -gt 0 ]]; then
  python3 -m pytest -q "$@"
else
  python3 -m pytest -q \
    tests/test_queue_repo_postgres_integration.py \
    tests/test_pipeline_worker_retry_recovery_integration.py
fi
