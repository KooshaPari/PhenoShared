from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from pheno.serve.config import ServeConfig
from pheno.serve.server import ServeState


def _config(status: str = "planned") -> ServeConfig:
    return ServeConfig(
        path=Path("pheno-test.yaml"),
        raw={
            "server": {"upstream_timeout_s": 1},
            "profiles": {
                "local/qwen35-08b": {
                    "engine": "llama.cpp",
                    "base_url": "http://127.0.0.1:23080/v1",
                    "status": status,
                },
            },
        },
    )


def test_readyz_fails_closed_without_active_profile() -> None:
    ready, checks = ServeState(_config()).readiness()
    assert ready is False
    assert checks["active_profiles"] == 0


def test_readyz_probes_active_upstream() -> None:
    response = MagicMock(status=200)
    with patch("pheno.serve.server.urlopen") as opener:
        opener.return_value.__enter__.return_value = response
        ready, checks = ServeState(_config("active")).readiness()
    assert ready is True
    assert checks["local/qwen35-08b"]["status"] == 200


def test_models_hide_planned_profiles_by_default() -> None:
    models = ServeState(_config()).registry.openai_models()
    assert models["data"] == []
