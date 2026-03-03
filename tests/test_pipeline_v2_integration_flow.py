from __future__ import annotations

import importlib.util
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

# Needed because imported modules load DB layer at import time.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://user:pass@localhost:5432/tothemoon")

from src.pipeline.worker import JOB_ACTIVATION, JOB_SCORING_HOT, PipelineWorker


def _load_tokens_route_module():
    module_path = Path(__file__).resolve().parents[1] / "src" / "app" / "routes" / "tokens.py"
    spec = importlib.util.spec_from_file_location("ttm_tokens_route_for_test", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _Store:
    def __init__(self) -> None:
        self.token = SimpleNamespace(
            id=701,
            mint_address="mint-701",
            name=None,
            symbol=None,
            status="monitoring",
            created_at=datetime.now(tz=timezone.utc),
            last_updated_at=None,
        )
        self.snapshot: dict | None = None
        self.snapshot_id = 0


class _FakeTokensRepo:
    def __init__(self, store: _Store) -> None:
        self.store = store

    def get_by_id(self, token_id: int):
        return self.store.token if token_id == self.store.token.id else None

    def update_pool_metrics_only(self, token_id: int, metrics: dict) -> None:
        if token_id != self.store.token.id:
            return
        if self.store.snapshot is None:
            self.store.snapshot = {}
        self.store.snapshot["metrics"] = metrics

    def update_token_fields(self, token, *, name=None, symbol=None):
        token.name = name
        token.symbol = symbol

    def set_active(self, token) -> None:
        token.status = "active"
        token.last_updated_at = datetime.now(tz=timezone.utc)

    def set_monitoring(self, token) -> None:
        token.status = "monitoring"
        token.last_updated_at = datetime.now(tz=timezone.utc)

    def update_token_timestamp(self, token_id: int) -> None:
        if token_id == self.store.token.id:
            self.store.token.last_updated_at = datetime.now(tz=timezone.utc)

    def save_snapshot(self, *, score: float, smoothed_score: float | None, metrics: dict, scoring_model: str) -> int:
        self.store.snapshot_id += 1
        self.store.snapshot = {
            "id": self.store.snapshot_id,
            "score": score,
            "smoothed_score": smoothed_score,
            "metrics": metrics,
            "scoring_model": scoring_model,
            "created_at": datetime.now(tz=timezone.utc),
        }
        return self.store.snapshot_id

    def list_non_archived_with_latest_scores(self, *, statuses=None, min_score=None, limit=50, offset=0, sort="score_desc"):
        token = self.store.token
        if statuses and token.status not in statuses:
            return []
        if self.store.snapshot is None:
            return [(token, {})]

        snap = self.store.snapshot
        metrics = snap.get("metrics") or {}
        effective = snap.get("smoothed_score")
        if effective is None:
            effective = snap.get("score")
        if min_score is not None and effective is not None and float(effective) < float(min_score):
            return []

        latest = {
            "latest_score": snap.get("score"),
            "latest_smoothed_score": snap.get("smoothed_score"),
            "latest_liquidity_usd": metrics.get("L_tot"),
            "latest_delta_p_5m": metrics.get("delta_p_5m"),
            "latest_delta_p_15m": metrics.get("delta_p_15m"),
            "latest_n_5m": metrics.get("n_5m"),
            "latest_primary_dex": metrics.get("primary_dex"),
            "latest_pool_type": metrics.get("primary_pool_type"),
            "latest_pool_type_counts": None,
            "latest_image_url": metrics.get("image_url"),
            "latest_pool_counts": None,
            "latest_fetched_at": metrics.get("fetched_at"),
            "latest_scoring_model": snap.get("scoring_model"),
            "latest_created_at": snap.get("created_at"),
            "pools": metrics.get("pools"),
        }
        return [(token, latest)]

    def count_non_archived_with_latest_scores(self, *, statuses=None, min_score=None):
        return len(
            self.list_non_archived_with_latest_scores(
                statuses=statuses,
                min_score=min_score,
                limit=1,
                offset=0,
                sort="score_desc",
            )
        )


class _FakeSettings:
    def __init__(self, _db=None):
        pass

    def get(self, key: str):
        mapping = {
            "activation_min_liquidity_usd": "200",
            "min_score": "0.1",
        }
        return mapping.get(key)


class _FakeQueueRepo:
    def __init__(self):
        self.acked: list[int] = []
        self.touched: list[dict] = []

    def get_runtime_state(self, _token_id: int):
        return None

    def touch_runtime_state(self, **kwargs):
        self.touched.append(kwargs)

    def ack_job(self, job_id: int, **_kwargs):
        self.acked.append(job_id)
        return True


class _FakeScoringService:
    def __init__(self, repo: _FakeTokensRepo):
        self.repo = repo

    def calculate_token_score(self, _token, _pairs):
        metrics = {
            "L_tot": 1800.0,
            "delta_p_5m": 0.11,
            "delta_p_15m": 0.19,
            "n_5m": 67,
            "primary_dex": "raydium",
            "primary_pool_type": "raydium_clmm",
            "pools": [
                {
                    "address": "pool-701",
                    "dex": "raydium",
                    "quote": "SOL",
                    "pool_type": "raydium_clmm",
                    "owner_program": "prog-701",
                    "is_wsol": True,
                }
            ],
            "fetched_at": datetime.now(tz=timezone.utc),
        }
        return 0.44, 0.42, metrics, {"tx_accel": 0.62}, {"tx_accel": 0.59}

    def save_score_result(
        self,
        *,
        token,
        score: float,
        smoothed_score: float | None,
        metrics: dict,
        raw_components=None,
        smoothed_components=None,
    ):
        return self.repo.save_snapshot(
            score=score,
            smoothed_score=smoothed_score,
            metrics=metrics,
            scoring_model="hybrid_momentum",
        )


@pytest.mark.asyncio
async def test_v2_activation_scoring_api_visibility_flow():
    tokens_routes = _load_tokens_route_module()
    store = _Store()
    token_repo = _FakeTokensRepo(store)
    queue_repo = _FakeQueueRepo()
    settings = _FakeSettings()
    scoring_service = _FakeScoringService(token_repo)
    worker = PipelineWorker(worker_id="integration-flow-worker")

    pairs = [
        {
            "dexId": "pumpfun-amm",
            "labels": ["pumpfun-amm"],
            "baseToken": {"address": store.token.mint_address, "name": "Moon 701", "symbol": "M701"},
            "quoteToken": {"symbol": "SOL"},
            "liquidity": {"usd": 300.0},
            "txns": {"m5": {"buys": 12, "sells": 8}, "h1": {"buys": 45, "sells": 41}},
            "volume": {"m5": 150.0, "h1": 900.0},
        },
        {
            "dexId": "raydium",
            "labels": ["clmm"],
            "baseToken": {"address": store.token.mint_address, "name": "Moon 701", "symbol": "M701"},
            "quoteToken": {"symbol": "SOL"},
            "liquidity": {"usd": 1200.0},
            "txns": {"m5": {"buys": 30, "sells": 20}, "h1": {"buys": 90, "sells": 75}},
            "volume": {"m5": 330.0, "h1": 2100.0},
            "pairAddress": "pair-701",
        },
    ]

    async def _fetch_pairs(*_args, **_kwargs):
        return pairs

    activation_job = SimpleNamespace(id=1001, token_id=store.token.id, job_type=JOB_ACTIVATION)
    scoring_job = SimpleNamespace(id=1002, token_id=store.token.id, job_type=JOB_SCORING_HOT)

    await worker._process_single_job(
        queue_repo=queue_repo,
        token_repo=token_repo,
        settings=settings,
        scoring_service=scoring_service,
        fetch_pairs=_fetch_pairs,
        job=activation_job,
    )
    await worker._process_single_job(
        queue_repo=queue_repo,
        token_repo=token_repo,
        settings=settings,
        scoring_service=scoring_service,
        fetch_pairs=_fetch_pairs,
        job=scoring_job,
    )

    assert store.token.status == "active"
    assert store.token.symbol == "M701"
    assert queue_repo.acked == [1001, 1002]

    with (
        patch.object(tokens_routes, "TokensRepository", lambda _db: token_repo),
        patch.object(tokens_routes, "SettingsService", _FakeSettings),
    ):
        response = await tokens_routes.list_tokens(
            db=object(),
            limit=50,
            offset=0,
            min_score=None,
            sort="score_desc",
            statuses="active,monitoring",
            status=None,
        )

    assert response.total == 1
    assert len(response.items) == 1
    item = response.items[0]
    assert item.mint_address == store.token.mint_address
    assert item.status == "active"
    assert item.score is not None and float(item.score) >= 0.42
    assert item.scoring_model == "hybrid_momentum"
    assert item.primary_pool_type == "raydium_clmm"
