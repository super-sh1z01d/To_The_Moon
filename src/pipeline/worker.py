from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import zlib
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable, Optional

from src.adapters.db.base import SessionLocal
from src.adapters.repositories.queue_repo import QueueRepository
from src.adapters.repositories.tokens_repo import TokensRepository
from src.adapters.services.dexscreener_batch_client import get_batch_client
from src.adapters.services.dexscreener_client import DexScreenerClient
from src.adapters.services.dex_broker import get_dex_broker, get_dex_broker_stats
from src.core.config import get_config
from src.domain.metrics.enhanced_dex_aggregator import aggregate_enhanced_metrics
from src.domain.pools.classifier_dex_only import classify_pairs_dex_only, determine_primary_pool_type
from src.domain.scoring.scoring_service import NoClassifiedPoolsError, ScoringService
from src.domain.settings.service import SettingsService
from src.domain.validation.dex_rules import check_activation_conditions

log = logging.getLogger("pipeline_worker")


JOB_ACTIVATION = "activation_check"
JOB_SCORING_HOT = "scoring_hot"
JOB_SCORING_COLD = "scoring_cold"
JOB_NOTARB = "notarb_snapshot"


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


TRANSIENT_ERROR_MARKERS = (
    "dex_pairs_unavailable",
    "timeout",
    "timed out",
    "rate limit",
    "429",
    "5xx",
    "server error",
    "connection",
    "temporarily unavailable",
)


def _is_transient_error(error_text: str) -> bool:
    msg = (error_text or "").strip().lower()
    if not msg:
        return False
    return any(marker in msg for marker in TRANSIENT_ERROR_MARKERS)


class PipelineWorker:
    def __init__(
        self,
        *,
        worker_id: Optional[str] = None,
        claim_limit: int = 40,
        lease_seconds: int = 45,
        idle_sleep_seconds: float = 0.35,
        seed_period_seconds: float = 3.0,
        max_attempts: int = 8,
    ) -> None:
        self.worker_id = worker_id or f"pipeline-{os.getpid()}"
        self.claim_limit = max(1, claim_limit)
        self.lease_seconds = max(10, lease_seconds)
        self.idle_sleep_seconds = max(0.1, idle_sleep_seconds)
        self.seed_period_seconds = max(1.0, seed_period_seconds)
        self.max_attempts = max(1, max_attempts)
        self._last_seed_at = datetime.fromtimestamp(0, tz=timezone.utc)
        self._seed_pause_until = datetime.fromtimestamp(0, tz=timezone.utc)
        self._seed_pause_reasons: list[str] = []

    def _heartbeat_interval_seconds(self) -> float:
        return max(5.0, self.lease_seconds / 3.0)

    def _compute_retry_delay(self, *, attempts: int, error_text: str) -> int:
        base_delay = min(600, 10 * max(1, attempts))
        if _is_transient_error(error_text):
            return min(900, max(30, base_delay * 2))
        return base_delay

    @staticmethod
    def _to_bool(value: Optional[str], default: bool = False) -> bool:
        if value is None:
            return default
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _to_int(value: Optional[str], default: int) -> int:
        try:
            return int(value) if value is not None else default
        except Exception:  # noqa: BLE001
            return default

    @staticmethod
    def _to_float(value: Optional[str], default: float) -> float:
        try:
            return float(value) if value is not None else default
        except Exception:  # noqa: BLE001
            return default

    def _token_in_canary(self, token_id: Optional[int], canary_percent: int) -> bool:
        if canary_percent >= 100:
            return True
        if canary_percent <= 0:
            return False
        if token_id is None:
            return False
        bucket = zlib.crc32(str(token_id).encode("utf-8")) % 100
        return bucket < canary_percent

    def _evaluate_seed_guard(self, queue_repo: QueueRepository, settings: SettingsService) -> list[str]:
        auto_rollback_enabled = self._to_bool(
            settings.get("pipeline_v2_auto_rollback_enabled"),
            default=True,
        )
        if not auto_rollback_enabled:
            return []

        queue_stats = queue_repo.queue_health()
        deadletter_rate = self._to_float(
            settings.get("pipeline_v2_deadletter_rollback_threshold"),
            default=0.01,
        )
        lag_seconds = self._to_int(
            settings.get("pipeline_v2_lag_rollback_seconds"),
            default=600,
        )
        due_threshold = self._to_int(
            settings.get("pipeline_v2_due_rollback_threshold"),
            default=300,
        )
        dex_error_threshold = self._to_float(
            settings.get("pipeline_v2_dex_error_rate_rollback_threshold"),
            default=0.25,
        )
        dex_min_requests = self._to_int(
            settings.get("pipeline_v2_dex_min_requests_for_rollback"),
            default=50,
        )

        reasons: list[str] = []
        if float(queue_stats.get("deadletter_rate", 0.0) or 0.0) >= deadletter_rate:
            reasons.append("deadletter_threshold_exceeded")
        if int(queue_stats.get("lag_seconds", 0) or 0) >= lag_seconds:
            reasons.append("lag_threshold_exceeded")
        if int(queue_stats.get("due", 0) or 0) >= due_threshold:
            reasons.append("due_threshold_exceeded")

        dex_stats = get_dex_broker_stats()
        batch_requests = int(dex_stats.get("batch_requests", 0) or 0)
        fallback_requests = int(dex_stats.get("fallback_requests", 0) or 0)
        failures = int(dex_stats.get("request_failures", 0) or 0)
        total_requests = batch_requests + fallback_requests
        if total_requests >= max(1, dex_min_requests):
            dex_error_rate = failures / total_requests
            if dex_error_rate >= dex_error_threshold:
                reasons.append("dex_error_rate_threshold_exceeded")
        return reasons

    @contextlib.asynccontextmanager
    async def _job_heartbeat(self, *, job_id: int):
        stop_event = asyncio.Event()
        interval = self._heartbeat_interval_seconds()

        async def _loop() -> None:
            while not stop_event.is_set():
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=interval)
                    break
                except asyncio.TimeoutError:
                    try:
                        with SessionLocal() as hb_db:
                            hb_repo = QueueRepository(hb_db)
                            hb_repo.heartbeat_jobs(
                                worker_id=self.worker_id,
                                job_ids=[job_id],
                                lease_seconds=self.lease_seconds,
                            )
                    except Exception as exc:  # noqa: BLE001
                        log.warning(
                            "pipeline_job_heartbeat_failed",
                            extra={"extra": {"job_id": job_id, "error": str(exc)}},
                        )

        task = asyncio.create_task(_loop())
        try:
            yield
        finally:
            stop_event.set()
            with contextlib.suppress(Exception):
                await task

    async def run_until_stopped(self, stop_event: asyncio.Event) -> None:
        log.info(
            "pipeline_worker_started",
            extra={
                "extra": {
                    "worker_id": self.worker_id,
                    "claim_limit": self.claim_limit,
                    "lease_seconds": self.lease_seconds,
                }
            },
        )

        while not stop_event.is_set():
            try:
                await self.run_iteration()
            except Exception as exc:  # noqa: BLE001
                log.exception("pipeline_worker_iteration_failed", extra={"extra": {"error": str(exc)}})
                await asyncio.sleep(1.0)

        log.info("pipeline_worker_stopped", extra={"extra": {"worker_id": self.worker_id}})

    async def run_iteration(self) -> None:
        now = _now()
        cfg = get_config()
        use_broker = bool(cfg.dex_broker_enabled)

        should_seed = (now - self._last_seed_at).total_seconds() >= self.seed_period_seconds
        if should_seed:
            with SessionLocal() as db:
                token_repo = TokensRepository(db)
                settings = SettingsService(db)
                queue_repo = QueueRepository(db)
                # Queue rebalance includes lease recovery and stale-retry boost.
                rebalance = queue_repo.rebalance_queue()
                cleaned = queue_repo.cleanup_finished_jobs(older_than_hours=24, limit=2000)
                inserted = 0

                if self._seed_pause_until > now:
                    _set_worker_runtime_state(
                        paused=True,
                        pause_until=self._seed_pause_until,
                        pause_reasons=self._seed_pause_reasons,
                    )
                else:
                    guard_reasons = self._evaluate_seed_guard(queue_repo, settings)
                    if guard_reasons:
                        cooldown = self._to_int(
                            settings.get("pipeline_v2_rollback_cooldown_sec"),
                            default=120,
                        )
                        self._seed_pause_until = now + timedelta(seconds=max(30, cooldown))
                        self._seed_pause_reasons = guard_reasons
                        _set_worker_runtime_state(
                            paused=True,
                            pause_until=self._seed_pause_until,
                            pause_reasons=self._seed_pause_reasons,
                        )
                        log.error(
                            "pipeline_auto_rollback_seed_pause",
                            extra={
                                "extra": {
                                    "pause_until": self._seed_pause_until.isoformat(),
                                    "reasons": guard_reasons,
                                }
                            },
                        )
                    else:
                        if self._seed_pause_reasons:
                            log.info("pipeline_seed_pause_cleared")
                        self._seed_pause_until = datetime.fromtimestamp(0, tz=timezone.utc)
                        self._seed_pause_reasons = []
                        _set_worker_runtime_state(paused=False, pause_until=None, pause_reasons=[])
                        inserted = self._seed_jobs(token_repo, settings, queue_repo)

                self._last_seed_at = now
                if inserted or rebalance.get("requeued_expired") or rebalance.get("boosted_retries"):
                    log.info(
                        "pipeline_seed_cycle",
                        extra={
                            "extra": {
                                "inserted_jobs": inserted,
                                "requeued": rebalance.get("requeued_expired", 0),
                                "boosted_retries": rebalance.get("boosted_retries", 0),
                                "cleaned": cleaned,
                            }
                        },
                    )

        with SessionLocal() as db:
            queue_repo = QueueRepository(db)
            jobs = queue_repo.claim_jobs(
                worker_id=self.worker_id,
                limit=self.claim_limit,
                lease_seconds=self.lease_seconds,
            )

            if not jobs:
                await asyncio.sleep(self.idle_sleep_seconds)
                return

            token_repo = TokensRepository(db)
            settings = SettingsService(db)
            scoring_service = ScoringService(token_repo, settings)

            broker = await get_dex_broker() if use_broker else None
            batch_client = await get_batch_client() if not use_broker else None
            fallback_client = DexScreenerClient(timeout=3.0) if not use_broker else None

            async def fetch_pairs(
                mint: str,
                *,
                lane: str,
                fallback_on_empty: bool,
            ) -> Optional[list[dict]]:
                if broker is not None:
                    pairs_map = await broker.get_pairs_for_mints(
                        [mint],
                        lane=lane,
                        fallback_on_empty=fallback_on_empty,
                    )
                    return pairs_map.get(mint)

                # Queue phase without broker (phase 1) uses batch client.
                pairs_map = await batch_client.get_pairs_for_mints([mint])  # type: ignore[union-attr]
                pairs = pairs_map.get(mint)

                if (
                    fallback_on_empty
                    and fallback_client is not None
                    and (pairs is None or (isinstance(pairs, list) and len(pairs) == 0))
                ):
                    return await asyncio.to_thread(fallback_client.get_pairs, mint)

                return pairs

            for job in jobs:
                try:
                    async with self._job_heartbeat(job_id=job.id):
                        await self._process_single_job(
                            queue_repo=queue_repo,
                            token_repo=token_repo,
                            settings=settings,
                            scoring_service=scoring_service,
                            fetch_pairs=fetch_pairs,
                            job=job,
                        )
                except Exception as exc:  # noqa: BLE001
                    error_text = str(exc)
                    retry_delay = self._compute_retry_delay(
                        attempts=int(job.attempts or 1),
                        error_text=error_text,
                    )
                    queue_repo.fail_job(
                        job.id,
                        worker_id=self.worker_id,
                        error=error_text,
                        retry_delay_seconds=retry_delay,
                        max_attempts=self.max_attempts,
                    )
                    if job.token_id is not None and _is_transient_error(error_text):
                        queue_repo.touch_runtime_state(
                            token_id=job.token_id,
                            backoff_until=_now() + timedelta(seconds=retry_delay),
                        )
                    log.warning(
                        "pipeline_job_failed",
                        extra={
                            "extra": {
                                "job_id": job.id,
                                "job_type": job.job_type,
                                "token_id": job.token_id,
                                "attempts": job.attempts,
                                "error": error_text,
                                "retry_delay_seconds": retry_delay,
                            }
                        },
                    )

    def _seed_jobs(self, token_repo: TokensRepository, settings: SettingsService, queue_repo: QueueRepository) -> int:
        inserted = 0

        # Activation lane has top priority.
        monitoring_limit = int(settings.get("pipeline_activation_batch") or 120)
        active_limit = int(settings.get("pipeline_active_check_batch") or 80)
        hot_limit = int(settings.get("pipeline_hot_batch") or 240)
        cold_limit = int(settings.get("pipeline_cold_batch") or 320)
        canary_percent = max(
            0,
            min(
                100,
                self._to_int(settings.get("pipeline_v2_canary_percent"), default=100),
            ),
        )

        monitoring = token_repo.list_by_status("monitoring", limit=monitoring_limit)
        active = token_repo.list_by_status("active", limit=active_limit)

        jobs = []
        for token in monitoring:
            if not self._token_in_canary(token.id, canary_percent):
                continue
            jobs.append(
                {
                    "job_type": JOB_ACTIVATION,
                    "token_id": token.id,
                    "priority": 400,
                    "idempotency_key": f"{JOB_ACTIVATION}:{token.id}",
                }
            )
        for token in active:
            if not self._token_in_canary(token.id, canary_percent):
                continue
            jobs.append(
                {
                    "job_type": JOB_ACTIVATION,
                    "token_id": token.id,
                    "priority": 390,
                    "idempotency_key": f"{JOB_ACTIVATION}:{token.id}",
                }
            )

        # Active tokens are always hot lane.
        active_for_scoring = token_repo.list_by_status("active", limit=hot_limit)
        for token in active_for_scoring:
            if not self._token_in_canary(token.id, canary_percent):
                continue
            jobs.append(
                {
                    "job_type": JOB_SCORING_HOT,
                    "token_id": token.id,
                    "priority": 300,
                    "idempotency_key": f"{JOB_SCORING_HOT}:{token.id}",
                }
            )

        # Monitoring tokens go to cold lane by default.
        monitoring_for_scoring = token_repo.list_by_status("monitoring", limit=cold_limit)
        for token in monitoring_for_scoring:
            if not self._token_in_canary(token.id, canary_percent):
                continue
            jobs.append(
                {
                    "job_type": JOB_SCORING_COLD,
                    "token_id": token.id,
                    "priority": 200,
                    "idempotency_key": f"{JOB_SCORING_COLD}:{token.id}",
                }
            )

        if jobs:
            inserted += queue_repo.enqueue_many(jobs)

        return inserted

    async def _process_single_job(
        self,
        *,
        queue_repo: QueueRepository,
        token_repo: TokensRepository,
        settings: SettingsService,
        scoring_service: ScoringService,
        fetch_pairs: Callable[..., Awaitable[Optional[list[dict]]]],
        job,
    ) -> None:
        if job.token_id is None:
            queue_repo.ack_job(job.id, worker_id=self.worker_id)
            return

        token = token_repo.get_by_id(job.token_id)
        if token is None:
            queue_repo.ack_job(job.id, worker_id=self.worker_id)
            return

        runtime_state = queue_repo.get_runtime_state(token.id)
        if runtime_state and runtime_state.backoff_until:
            backoff_until = runtime_state.backoff_until
            if backoff_until.tzinfo is None:
                backoff_until = backoff_until.replace(tzinfo=timezone.utc)
            now = _now()
            if backoff_until > now:
                delay_seconds = max(1, int((backoff_until - now).total_seconds()))
                queue_repo.defer_job(
                    job.id,
                    worker_id=self.worker_id,
                    delay_seconds=delay_seconds,
                    reason="token_backoff_active",
                )
                return

        if job.job_type == JOB_ACTIVATION:
            await self._handle_activation_job(
                queue_repo=queue_repo,
                token_repo=token_repo,
                settings=settings,
                fetch_pairs=fetch_pairs,
                job=job,
                token=token,
            )
            return

        if job.job_type in {JOB_SCORING_HOT, JOB_SCORING_COLD}:
            await self._handle_scoring_job(
                queue_repo=queue_repo,
                token_repo=token_repo,
                settings=settings,
                scoring_service=scoring_service,
                fetch_pairs=fetch_pairs,
                job=job,
                token=token,
                lane=job.job_type,
            )
            return

        if job.job_type == JOB_NOTARB:
            # NotArb uses persisted snapshots only; no direct Dex calls.
            queue_repo.ack_job(job.id, worker_id=self.worker_id)
            return

        queue_repo.ack_job(job.id, worker_id=self.worker_id)

    async def _handle_activation_job(
        self,
        *,
        queue_repo: QueueRepository,
        token_repo: TokensRepository,
        settings: SettingsService,
        fetch_pairs: Callable[..., Awaitable[Optional[list[dict]]]],
        job,
        token,
    ) -> None:
        threshold = float(settings.get("activation_min_liquidity_usd") or 200.0)
        pairs = await fetch_pairs(
            token.mint_address,
            lane="activation",
            fallback_on_empty=True,
        )

        if pairs is None:
            raise RuntimeError("dex_pairs_unavailable")

        pairs = pairs or []
        activation_ok = check_activation_conditions(token.mint_address, pairs, threshold)

        # Keep monitoring metrics fresh even before activation.
        enriched_pairs = classify_pairs_dex_only(pairs)
        if enriched_pairs:
            metrics = aggregate_enhanced_metrics(
                token.mint_address,
                enriched_pairs,
                token.created_at,
                min_liquidity_usd=50.0,
            )
            metrics["pool_classification_source"] = "dexscreener"
            primary_pool_type = determine_primary_pool_type(metrics.get("pools") or [])
            if primary_pool_type:
                metrics["primary_pool_type"] = primary_pool_type
            token_repo.update_pool_metrics_only(token.id, metrics)

        if token.status == "monitoring" and activation_ok:
            name = None
            symbol = None
            for pair in pairs:
                base = (pair.get("baseToken") or {})
                if str(base.get("address")) == token.mint_address:
                    name = name or base.get("name")
                    symbol = symbol or base.get("symbol")
                    if name and symbol:
                        break
            token_repo.update_token_fields(token, name=name, symbol=symbol)
            token_repo.set_active(token)
        elif token.status == "active" and not activation_ok:
            token_repo.set_monitoring(token)
        else:
            token_repo.update_token_timestamp(token.id)

        queue_repo.touch_runtime_state(
            token_id=token.id,
            activation_checked_at=_now(),
            clear_backoff=True,
        )
        queue_repo.ack_job(job.id, worker_id=self.worker_id)

    async def _handle_scoring_job(
        self,
        *,
        queue_repo: QueueRepository,
        token_repo: TokensRepository,
        settings: SettingsService,
        scoring_service: ScoringService,
        fetch_pairs: Callable[..., Awaitable[Optional[list[dict]]]],
        job,
        token,
        lane: str,
    ) -> None:
        pairs = await fetch_pairs(
            token.mint_address,
            lane=lane,
            fallback_on_empty=True,
        )
        if pairs is None:
            raise RuntimeError("dex_pairs_unavailable")

        try:
            score, smoothed_score, metrics, raw_components, smoothed_components = scoring_service.calculate_token_score(
                token,
                pairs,
            )
        except NoClassifiedPoolsError:
            token_repo.update_token_timestamp(token.id)
            queue_repo.touch_runtime_state(
                token_id=token.id,
                scored_at=_now(),
                score_band="cold",
                clear_backoff=True,
            )
            queue_repo.ack_job(job.id, worker_id=self.worker_id)
            return

        scoring_service.save_score_result(
            token=token,
            score=score,
            smoothed_score=smoothed_score,
            metrics=metrics,
            raw_components=raw_components,
            smoothed_components=smoothed_components,
        )

        min_score = float(settings.get("min_score") or 0.1)
        effective_score = float(smoothed_score if smoothed_score is not None else score)
        score_band = "hot" if effective_score >= min_score else "cold"

        queue_repo.touch_runtime_state(
            token_id=token.id,
            scored_at=_now(),
            score_band=score_band,
            clear_backoff=True,
        )
        queue_repo.ack_job(job.id, worker_id=self.worker_id)


_worker_task: Optional[asyncio.Task] = None
_stop_event: Optional[asyncio.Event] = None
_worker_runtime_state: dict[str, object] = {
    "paused": False,
    "pause_until": None,
    "pause_reasons": [],
}


def _reset_worker_runtime_state() -> None:
    _worker_runtime_state["paused"] = False
    _worker_runtime_state["pause_until"] = None
    _worker_runtime_state["pause_reasons"] = []


def _set_worker_runtime_state(*, paused: bool, pause_until: Optional[datetime], pause_reasons: list[str]) -> None:
    _worker_runtime_state["paused"] = bool(paused)
    _worker_runtime_state["pause_until"] = pause_until.isoformat() if pause_until else None
    _worker_runtime_state["pause_reasons"] = list(pause_reasons)


def get_pipeline_worker_state() -> dict[str, object]:
    running = _worker_task is not None and not _worker_task.done()
    return {
        "running": running,
        "worker_task_done": bool(_worker_task.done()) if _worker_task else False,
        "worker_task_cancelled": bool(_worker_task.cancelled()) if _worker_task else False,
        "paused": bool(_worker_runtime_state.get("paused", False)),
        "pause_until": _worker_runtime_state.get("pause_until"),
        "pause_reasons": list(_worker_runtime_state.get("pause_reasons") or []),
    }


async def start_pipeline_worker() -> None:
    global _worker_task, _stop_event

    if _worker_task is not None and not _worker_task.done():
        return

    _reset_worker_runtime_state()
    _stop_event = asyncio.Event()
    worker = PipelineWorker()
    _worker_task = asyncio.create_task(worker.run_until_stopped(_stop_event))


async def stop_pipeline_worker() -> None:
    global _worker_task, _stop_event

    if _stop_event is not None:
        _stop_event.set()

    if _worker_task is not None:
        try:
            await asyncio.wait_for(_worker_task, timeout=5.0)
        except asyncio.TimeoutError:
            _worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await _worker_task

    _worker_task = None
    _stop_event = None
    _reset_worker_runtime_state()
