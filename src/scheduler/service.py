from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI

from src.adapters.db.base import SessionLocal
from src.adapters.repositories.queue_repo import QueueRepository
from src.core.config import get_config
from src.scheduler.notarb_tasks import update_notarb_pools_file
from src.scheduler.tasks import (
    archive_once,
    monitor_token_processing_once,
    optimize_performance_once,
    send_system_health_summary_once,
)


log = logging.getLogger("scheduler")


def init_scheduler(app: FastAPI) -> Optional[AsyncIOScheduler]:
    cfg = get_config()
    if not cfg.scheduler_enabled:
        log.info("scheduler_disabled")
        return None

    if os.environ.get("DISABLE_SCHEDULER_IN_WORKER", "false").lower() == "true":
        log.info("scheduler_disabled_by_env_var")
        return None

    # Queue-first runtime: scheduler is only for system-level jobs.
    if not (cfg.pipeline_v2_enabled and cfg.queue_v2_enabled):
        log.warning(
            "scheduler_pipeline_v2_disabled",
            extra={"extra": {"pipeline_v2_enabled": cfg.pipeline_v2_enabled, "queue_v2_enabled": cfg.queue_v2_enabled}},
        )
        return None

    scheduler = AsyncIOScheduler()

    async def _start_pipeline_worker() -> None:
        from src.pipeline.worker import start_pipeline_worker

        await start_pipeline_worker()

    def queue_maintenance_once() -> None:
        with SessionLocal() as sess:
            queue_repo = QueueRepository(sess)
            rebalance = queue_repo.rebalance_queue()
            cleaned = queue_repo.cleanup_finished_jobs(older_than_hours=24, limit=5000)
            requeued = int(rebalance.get("requeued_expired", 0))
            boosted = int(rebalance.get("boosted_retries", 0))
            if requeued or boosted or cleaned:
                log.info(
                    "queue_maintenance_completed",
                    extra={
                        "extra": {
                            "requeued": requeued,
                            "boosted_retries": boosted,
                            "cleaned": cleaned,
                        }
                    },
                )

    asyncio.create_task(_start_pipeline_worker())

    scheduler.add_job(
        queue_maintenance_once,
        IntervalTrigger(seconds=20),
        id="queue_maintenance",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        archive_once,
        IntervalTrigger(hours=1),
        id="archiver_hourly",
        max_instances=1,
    )
    scheduler.add_job(
        monitor_token_processing_once,
        IntervalTrigger(minutes=5),
        id="token_processing_monitor",
        max_instances=1,
    )
    scheduler.add_job(
        send_system_health_summary_once,
        IntervalTrigger(hours=1),
        id="health_summary",
        max_instances=1,
    )
    scheduler.add_job(
        optimize_performance_once,
        IntervalTrigger(minutes=3),
        id="performance_optimizer",
        max_instances=1,
    )
    scheduler.add_job(
        update_notarb_pools_file,
        IntervalTrigger(seconds=60),
        id="notarb_pools_updater",
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()
    app.state.scheduler = scheduler
    log.info("scheduler_started_pipeline_v2")
    return scheduler
