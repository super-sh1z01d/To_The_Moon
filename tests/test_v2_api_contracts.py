from __future__ import annotations

import os
from unittest.mock import patch
from typing import Any

import pytest
from fastapi.testclient import TestClient

# Needed because app imports DB layer at module import time.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://user:pass@localhost:5432/tothemoon")

try:
    import itsdangerous  # noqa: F401
    _HAS_ITSDANGEROUS = True
except Exception:  # noqa: BLE001
    _HAS_ITSDANGEROUS = False

pytestmark = pytest.mark.skipif(
    not _HAS_ITSDANGEROUS,
    reason="itsdangerous is required for FastAPI session middleware tests",
)

if _HAS_ITSDANGEROUS:
    from src.app.main import app
    from src.domain.users.auth_service import get_current_admin_user
    from src.domain.users.schemas import User
else:
    app = None  # type: ignore[assignment]
    get_current_admin_user = None  # type: ignore[assignment]
    User = Any  # type: ignore[assignment]


def _error_message(payload: dict[str, Any]) -> str:
    detail = payload.get("detail")
    if isinstance(detail, str):
        return detail
    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str):
            return message
    return ""


def _admin_user() -> User:
    return User(id=1, email="admin@example.com", is_active=True, role="admin")


@pytest.fixture
def client():
    app.dependency_overrides[get_current_admin_user] = _admin_user
    with patch("src.app.main.init_scheduler", return_value=None):
        with TestClient(app) as tc:
            yield tc
    app.dependency_overrides.clear()


def test_settings_weights_hybrid_only_contract(client: TestClient) -> None:
    class _FakeSettingsService:
        def __init__(self, _db):
            pass

        def get_hybrid_momentum_weights(self):
            return {"w_tx": 0.25, "w_vol": 0.25, "w_fresh": 0.25, "w_oi": 0.25}

    with patch("src.app.routes.settings.SettingsService", _FakeSettingsService):
        response = client.get("/settings/weights")

    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"hybrid_momentum", "active_model"}
    assert data["active_model"] == "hybrid_momentum"
    assert "legacy" not in data


def test_settings_scoring_model_active_is_read_only(client: TestClient) -> None:
    class _FakeSettingsService:
        def __init__(self, _db):
            pass

    with patch("src.app.routes.settings.SettingsService", _FakeSettingsService):
        response = client.put("/settings/scoring_model_active", json={"value": "legacy"})

    assert response.status_code == 400
    assert "read-only in v2" in _error_message(response.json())


def test_health_queue_status_marks_unhealthy_with_large_backlog(client: TestClient) -> None:
    class _DummySessionCtx:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    class _FakeQueueRepo:
        def __init__(self, _db):
            pass

        def queue_health(self):
            return {
                "total": 500,
                "due": 400,
                "lag_seconds": 700,
                "leased_expired": 3,
                "deadletter_rate": 0.02,
                "by_status": {},
                "by_type": {},
            }

    class _FakeSettingsService:
        def __init__(self, _db):
            pass

        def get(self, key: str):
            if key == "backlog_warning_threshold":
                return "75"
            if key == "backlog_error_threshold":
                return "100"
            return None

    with (
        patch("src.app.routes.health.SessionLocal", return_value=_DummySessionCtx()),
        patch("src.app.routes.health.QueueRepository", _FakeQueueRepo),
        patch("src.app.routes.health.SettingsService", _FakeSettingsService),
        patch("src.app.routes.health.get_pipeline_worker_state", return_value={"running": True}),
    ):
        response = client.get("/health/queue")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unhealthy"
    assert "deadletter_rate_high" in data["reasons"]
    assert "queue_lag_high" in data["reasons"]
    assert "due_backlog_high" in data["reasons"]


def test_health_queue_adds_seed_pause_reason_when_worker_paused(client: TestClient) -> None:
    class _DummySessionCtx:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    class _FakeQueueRepo:
        def __init__(self, _db):
            pass

        def queue_health(self):
            return {
                "total": 10,
                "due": 0,
                "lag_seconds": 0,
                "leased_expired": 0,
                "deadletter_rate": 0.0,
                "by_status": {},
                "by_type": {},
            }

    class _FakeSettingsService:
        def __init__(self, _db):
            pass

        def get(self, key: str):
            if key == "backlog_warning_threshold":
                return "75"
            if key == "backlog_error_threshold":
                return "100"
            return None

    with (
        patch("src.app.routes.health.SessionLocal", return_value=_DummySessionCtx()),
        patch("src.app.routes.health.QueueRepository", _FakeQueueRepo),
        patch("src.app.routes.health.SettingsService", _FakeSettingsService),
        patch(
            "src.app.routes.health.get_pipeline_worker_state",
            return_value={"running": True, "paused": True, "pause_reasons": ["deadletter_threshold_exceeded"]},
        ),
    ):
        response = client.get("/health/queue")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert "seed_paused_auto_rollback" in data["reasons"]


def test_admin_recalculate_uses_queue_v2_mode(client: TestClient) -> None:
    with patch("src.app.routes.admin.asyncio.create_task") as mock_create_task:
        response = client.post("/admin/recalculate")
        scheduled = mock_create_task.call_args.args[0]
        scheduled.close()

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "started"
    assert data["mode"] == "queue_v2"
    mock_create_task.assert_called_once()


def test_admin_queue_rebalance_returns_rebalance_payload(client: TestClient) -> None:
    class _DummySessionCtx:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    class _FakeQueueRepo:
        def __init__(self, _db):
            pass

        def rebalance_queue(self):
            return {"requeued_expired": 7, "boosted_retries": 12}

        def queue_health(self):
            return {
                "total": 100,
                "due": 5,
                "lag_seconds": 15,
                "leased_expired": 0,
                "deadletter_rate": 0.0,
                "by_status": {"queued": 5, "retry": 2, "leased": 1, "done": 92, "deadletter": 0, "cancelled": 0},
                "by_type": {"activation_check": 3, "scoring_hot": 2},
            }

    with (
        patch("src.app.routes.admin.SessionLocal", return_value=_DummySessionCtx()),
        patch("src.app.routes.admin.QueueRepository", _FakeQueueRepo),
    ):
        response = client.post("/admin/queue/rebalance")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["rebalance"]["requeued_expired"] == 7
    assert data["rebalance"]["boosted_retries"] == 12
    assert data["queue"]["total"] == 100


def test_admin_queue_canary_updates_rollout_percent(client: TestClient) -> None:
    class _FakeSettingsService:
        value = "30"

        def __init__(self, _db):
            pass

        def get(self, key: str):
            if key == "pipeline_v2_canary_percent":
                return self.__class__.value
            return None

        def set(self, key: str, value: str):
            if key == "pipeline_v2_canary_percent":
                self.__class__.value = value

    class _DummySessionCtx:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    with (
        patch("src.app.routes.admin.SessionLocal", return_value=_DummySessionCtx()),
        patch("src.app.routes.admin.SettingsService", _FakeSettingsService),
        patch("src.pipeline.worker.get_pipeline_worker_state", return_value={"running": True, "paused": False}),
    ):
        response = client.post("/admin/queue/canary", json={"percent": 60})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["previous_percent"] == 30
    assert data["current_percent"] == 60


def test_admin_queue_canary_rejects_non_rollout_steps(client: TestClient) -> None:
    response = client.post("/admin/queue/canary", json={"percent": 55})

    assert response.status_code == 400
    assert "percent must be one of" in _error_message(response.json())


def test_health_dex_degraded_when_broker_in_degraded_mode(client: TestClient) -> None:
    with patch(
        "src.app.routes.health.get_dex_broker_stats",
        return_value={
            "degraded_mode": True,
            "request_failures": 5,
            "batch_requests": 20,
            "fallback_requests": 3,
        },
    ):
        response = client.get("/health/dex")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["dex_broker"]["degraded_mode"] is True
