from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

# Needed because settings service imports DB layer at module import time.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://user:pass@localhost:5432/tothemoon")

from src.domain.settings.service import SettingsService


def _make_service() -> SettingsService:
    svc = SettingsService(db=MagicMock())
    svc.repo = MagicMock()
    return svc


def test_set_rejects_removed_legacy_keys() -> None:
    svc = _make_service()
    with pytest.raises(ValueError, match="removed in v2"):
        svc.set("weight_s", "0.35")


def test_set_rejects_scoring_model_active_updates() -> None:
    svc = _make_service()
    with pytest.raises(ValueError, match="read-only in v2"):
        svc.set("scoring_model_active", "hybrid_momentum")


def test_get_all_forces_hybrid_model_and_ignores_legacy_keys() -> None:
    svc = _make_service()
    svc.repo.get_all.return_value = {
        "w_tx": "0.40",
        "weight_s": "0.99",
        "scoring_model_active": "legacy",
    }

    data = svc.get_all()

    assert data["w_tx"] == "0.40"
    assert data["scoring_model_active"] == "hybrid_momentum"
    assert "weight_s" not in data


def test_cleanup_legacy_settings_normalizes_model() -> None:
    svc = _make_service()
    svc.repo.delete_many.return_value = 6
    svc.repo.get.return_value = "legacy"

    removed = svc.cleanup_legacy_settings()

    assert removed == 6
    svc.repo.set.assert_called_once_with("scoring_model_active", "hybrid_momentum")


def test_set_validates_pipeline_v2_canary_percent_range() -> None:
    svc = _make_service()
    svc.repo.get.return_value = None

    with pytest.raises(ValueError, match="Invalid value"):
        svc.set("pipeline_v2_canary_percent", "150")

    svc.set("pipeline_v2_canary_percent", "60")
    svc.repo.set.assert_called_with("pipeline_v2_canary_percent", "60")


def test_set_validates_pipeline_v2_auto_rollback_bool() -> None:
    svc = _make_service()
    svc.repo.get.return_value = None

    with pytest.raises(ValueError, match="Invalid value"):
        svc.set("pipeline_v2_auto_rollback_enabled", "maybe")

    svc.set("pipeline_v2_auto_rollback_enabled", "true")
    svc.repo.set.assert_called_with("pipeline_v2_auto_rollback_enabled", "true")


def test_set_validates_pipeline_v2_dex_error_rate_threshold() -> None:
    svc = _make_service()
    svc.repo.get.return_value = None

    with pytest.raises(ValueError, match="Invalid value"):
        svc.set("pipeline_v2_dex_error_rate_rollback_threshold", "1.5")

    svc.set("pipeline_v2_dex_error_rate_rollback_threshold", "0.4")
    svc.repo.set.assert_called_with("pipeline_v2_dex_error_rate_rollback_threshold", "0.4")


def test_set_validates_pipeline_v2_dex_min_requests() -> None:
    svc = _make_service()
    svc.repo.get.return_value = None

    with pytest.raises(ValueError, match="Invalid value"):
        svc.set("pipeline_v2_dex_min_requests_for_rollback", "0")

    svc.set("pipeline_v2_dex_min_requests_for_rollback", "50")
    svc.repo.set.assert_called_with("pipeline_v2_dex_min_requests_for_rollback", "50")
