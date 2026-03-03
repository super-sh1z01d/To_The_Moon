from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import patch

# Needed because scheduler service imports DB layer at module import time.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://user:pass@localhost:5432/tothemoon")

from src.scheduler.service import init_scheduler


class _FakeScheduler:
    def __init__(self):
        self.jobs: list[dict] = []
        self.started = False

    def add_job(self, func, *args, **kwargs):  # noqa: ANN001
        self.jobs.append(
            {
                "id": kwargs.get("id"),
                "func_name": getattr(func, "__name__", str(func)),
                "args": args,
                "kwargs": kwargs,
            }
        )

    def start(self):
        self.started = True


def test_init_scheduler_returns_none_when_scheduler_disabled():
    app = SimpleNamespace(state=SimpleNamespace())

    with (
        patch(
            "src.scheduler.service.get_config",
            return_value=SimpleNamespace(
                scheduler_enabled=False,
            ),
        ),
        patch("src.scheduler.service.AsyncIOScheduler") as mock_scheduler_cls,
        patch("src.scheduler.service.asyncio.create_task") as mock_create_task,
    ):
        scheduler = init_scheduler(app)

    assert scheduler is None
    assert not hasattr(app.state, "scheduler")
    mock_scheduler_cls.assert_not_called()
    mock_create_task.assert_not_called()


def test_init_scheduler_pipeline_v2_uses_system_jobs_and_starts_worker():
    app = SimpleNamespace(state=SimpleNamespace())
    fake_scheduler = _FakeScheduler()

    with (
        patch(
            "src.scheduler.service.get_config",
            return_value=SimpleNamespace(
                scheduler_enabled=True,
            ),
        ),
        patch("src.scheduler.service.AsyncIOScheduler", return_value=fake_scheduler),
        patch("src.scheduler.service.asyncio.create_task") as mock_create_task,
    ):
        scheduler = init_scheduler(app)

    assert scheduler is fake_scheduler
    assert fake_scheduler.started is True
    assert app.state.scheduler is fake_scheduler

    job_ids = {j["id"] for j in fake_scheduler.jobs}
    assert "queue_maintenance" in job_ids
    assert "archiver_hourly" in job_ids
    assert "token_processing_monitor" in job_ids
    assert "health_summary" in job_ids
    assert "performance_optimizer" in job_ids
    assert "notarb_pools_updater" in job_ids

    assert "hot_updater" not in job_ids
    assert "cold_updater" not in job_ids
    assert "activation_enforcer" not in job_ids

    # Worker bootstrap happens asynchronously in v2 mode.
    mock_create_task.assert_called_once()
    created_coro = mock_create_task.call_args.args[0]
    if hasattr(created_coro, "close"):
        created_coro.close()
