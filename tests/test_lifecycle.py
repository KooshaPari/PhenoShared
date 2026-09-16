from pathlib import Path

import pytest

from pheno.serve.config import ServeConfig
from pheno.serve.lifecycle import SlotController


def _config(tmp_path: Path, engine: str) -> ServeConfig:
    model = tmp_path / "model"
    model.mkdir()
    return ServeConfig(
        path=tmp_path / "config.yaml",
        raw={
            "server": {},
            "engine_slots": {},
            "profiles": {
                "local/test": {
                    "engine": engine,
                    "model_path": str(model),
                    "base_url": "http://127.0.0.1:8123/v1",
                    "status": "active",
                }
            },
        },
    )


@pytest.mark.parametrize(
    ("engine", "executable", "marker"),
    [
        ("vllm", "vllm", "serve"),
        ("llama.cpp", "llama-server", "-m"),
        ("tensorrt_llm", "trtllm-serve", "--host"),
    ],
)
def test_non_sglang_launches_are_explicit_local_plans(
    tmp_path, monkeypatch, engine, executable, marker
):
    monkeypatch.setenv("PHENO_VLLM_EXECUTABLE", executable)
    monkeypatch.setenv("PHENO_LLAMA_SERVER", executable)
    monkeypatch.setenv("PHENO_TRTLLM_EXECUTABLE", executable)
    plan = SlotController(_config(tmp_path, engine)).plan("local/test")
    assert plan.engine == engine
    assert plan.model_path == tmp_path / "model"
    assert "8123" in plan.command
    assert marker in plan.command


def test_launch_rejects_missing_local_model_path(tmp_path):
    config = _config(tmp_path, "vllm")
    config.raw["profiles"]["local/test"]["model_path"] = ""
    with pytest.raises(ValueError, match="local model_path"):
        SlotController(config).plan("local/test")
