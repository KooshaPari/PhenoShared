"""Comprehensive functional tests for ``pheno.model_manager``.

The module imports ``pheno.runtime_admission`` which has been deleted
from the project, so we install a no-op stub in ``sys.modules`` before
the first import. Each test patches ``pheno.model_manager.validate_runtime_admission``
(via ``patch("pheno.model_manager.validate_runtime_admission", ...)``)
to drive different validator return values.

Focuses on the runtime-admission + spawn flow that the existing
``test_model_manager_coverage.py`` does not exercise:

* ``build_cmd`` template-mode path (args_tpl formatting, subs, draft
  injection, empty-token stripping)
* ``_validate_runtime_admission`` — full coverage of every branch:
  missing artifact, malformed binding, mismatched request fields,
  artifact identity, lease drift, runtime-binding drift, decision !=
  admitted, blocked lane, granted flag, incomplete cmd/uuid
* ``_prepare_start`` — admission_sha256 shape validation
* ``_spawn_prepared`` — actual subprocess.Popen call + state mutation
* ``start(dry_run=False)`` — end-to-end with full admission path
* ``swap_to(dry_run=False)`` — calls ``stop_on_demand`` then spawns
* ``_launch_template`` — config/launch directory YAML loading + missing
"""

from __future__ import annotations

import json
import sys
import types
from collections.abc import Callable
from hashlib import sha256
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Install stub for the missing `pheno.runtime_admission` module BEFORE we
# import `pheno.model_manager`. The stub provides a no-op
# `validate_runtime_admission` so the import succeeds; tests patch the
# pheno.model_manager-local binding per-test.
# ---------------------------------------------------------------------------

_STUB_NAME = "pheno.runtime_admission"
if _STUB_NAME not in sys.modules:
    _stub = types.ModuleType(_STUB_NAME)

    def _stub_validate(value: Any, *, root: Path) -> dict[str, Any]:
        return {}

    _stub.validate_runtime_admission = _stub_validate
    sys.modules[_STUB_NAME] = _stub

from pheno.model_manager import (  # noqa: E402
    ModelManager,
    ModelSpec,
    PreparedLaunch,
    RuntimeAdmissionError,
)


# ---------------------------------------------------------------------------
# Helpers — build fake admission artifacts
# ---------------------------------------------------------------------------


def _write_models_yaml(
    path: Path,
    *,
    port_base: int = 8080,
    binary: str = "llama-server",
    ik_flags: str = "",
    tiers: dict[str, Any] | None = None,
) -> None:
    """Write a config/models.yaml with controllable tiers."""
    if tiers is None:
        tiers = {}
    for tier_dict in tiers.values():
        if not isinstance(tier_dict, dict):
            continue
        for node in tier_dict.values():
            if not isinstance(node, dict):
                continue
            if node.get("runtime") == "gpu" and "device_target" not in node:
                node["device_target"] = "RTX 3090 Ti"
    payload: dict[str, Any] = {
        "llama_server": {
            "binary": binary,
            "ik_llama_flags": ik_flags,
            "port_base": port_base,
        },
        "tiers": tiers,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_swarm_yaml(path: Path, **kwargs: Any) -> None:
    path.write_text(json.dumps(kwargs), encoding="utf-8")


def _make_full_binding() -> dict[str, str]:
    """A complete, valid runtime_admission binding dict."""
    return {
        "lane_id": "rtx3090_qwen35_9b_vllm_c0",
        "model_id": "Qwen3.5-0.8B",
        "candidate_id": "cand-1234",
        "runtime_id": "runtime-vllm",
        "device_id": "device-3090",
        "device_uuid": "GPU-uuid-aaaa",
        "cell_id": "cell-A",
        "artifact_sha256": "0" * 64,
        "command_binary": "llama-server",
    }


def _make_lane(
    binding: dict[str, str],
    *,
    decision: str = "admitted",
    action_permitted: bool = True,
    granted: bool = True,
    artifact_content_sha: str | None = None,
    artifact_candidate_id: str | None = None,
    artifact_cell_id: str | None = None,
    artifact_device_id: str | None = None,
    artifact_runtime: str | None = None,
    lease_device_uuid: str | None = None,
    lease_artifact_sha: str | None = None,
    runtime_binding_runtime: str | None = None,
    request_override: dict[str, str] | None = None,
    blockers: list[str] | None = None,
) -> dict[str, Any]:
    """Build a lane dict that pairs with ``_make_full_binding``."""
    if artifact_content_sha is None:
        artifact_content_sha = binding["artifact_sha256"]
    if artifact_candidate_id is None:
        artifact_candidate_id = binding["candidate_id"]
    if artifact_cell_id is None:
        artifact_cell_id = binding["cell_id"]
    if artifact_device_id is None:
        artifact_device_id = binding["device_id"]
    if artifact_runtime is None:
        artifact_runtime = binding["runtime_id"]
    if runtime_binding_runtime is None:
        runtime_binding_runtime = binding["runtime_id"]

    request: dict[str, str] = {
        "candidate_id": binding["candidate_id"],
        "runtime_id": binding["runtime_id"],
        "device_id": binding["device_id"],
        "cell_id": binding["cell_id"],
    }
    if request_override:
        request.update(request_override)

    lane: dict[str, Any] = {
        "lane_id": binding["lane_id"],
        "request": request,
        "artifact_binding": {
            "candidate_id": artifact_candidate_id,
            "cell_id": artifact_cell_id,
            "device_id": artifact_device_id,
            "runtime": artifact_runtime,
            "binding": {"content_sha256": artifact_content_sha},
        },
        "endpoint_lease": {},
        "runtime_binding": {"runtime": runtime_binding_runtime},
        "decision": decision,
        "action_permitted": action_permitted,
        "authorization": {"launch": {"granted": granted}},
        "blockers": blockers if blockers is not None else [],
    }
    if lease_device_uuid is not None or lease_artifact_sha is not None:
        lane["endpoint_lease"] = {
            "device_uuid": lease_device_uuid,
            "artifact_sha256": lease_artifact_sha,
        }
    return lane


def _make_admission_value(
    binding: dict[str, str],
    lane: dict[str, Any],
    *,
    admission_sha: str | None = None,
) -> dict[str, Any]:
    """Wrap a lane in a value dict the stub validator returns."""
    return {
        "lanes": [lane],
        "admission_sha256": admission_sha or ("a" * 64),
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_model_file(tmp_path: Path) -> Path:
    """Create a placeholder GGUF file so path-exists checks pass."""
    f = tmp_path / "model.gguf"
    f.write_bytes(b"GGUF\x03\x00\x00\x00")
    return f


@pytest.fixture()
def manager_factory(
    tmp_path: Path,
    fake_model_file: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[..., ModelManager]:
    """Factory that builds a ModelManager rooted at tmp_path."""
    config_path = tmp_path / "models.yaml"
    swarm_path = tmp_path / "local_swarm.yaml"
    state_dir = tmp_path / "state"
    state_path = state_dir / "model_manager.json"
    admission_path = state_dir / "admission.json"

    # Re-bind STATE_DIR in both pheno.model_manager and pheno.paths so the
    # manager's hardcoded state_path lands inside tmp_path.
    import pheno.model_manager as _mm_mod
    import pheno.paths as pheno_paths

    monkeypatch.setattr(_mm_mod, "STATE_DIR", state_dir)
    monkeypatch.setattr(pheno_paths, "STATE_DIR", state_dir)

    # Also rebind CONFIG_DIR so ${PHENO_ROOT} and config/launch work.
    config_dir = tmp_path / "config"
    monkeypatch.setattr(_mm_mod, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(pheno_paths, "CONFIG_DIR", config_dir)

    def _factory(
        *,
        tiers: dict[str, Any] | None = None,
        swarm: dict[str, Any] | None = None,
        binary: str = "llama-server",
        ik_flags: str = "",
        port_base: int = 8080,
        runtime_admission: dict[str, str] | None = None,
        admission_path_override: Path | None = None,
    ) -> ModelManager:
        if tiers is None:
            tiers = {
                "local": {
                    "qwen08b": {
                        "id": "Qwen3.5-0.8B",
                        "path": str(fake_model_file),
                        "always_on": True,
                        "kv_ctx": 8192,
                        "runtime": "gpu",
                        "device_target": "RTX 3090 Ti",
                    }
                }
            }
        # Patch missing device_target on any gpu model
        for tier_dict in tiers.values():
            if not isinstance(tier_dict, dict):
                continue
            for node in tier_dict.values():
                if not isinstance(node, dict):
                    continue
                if node.get("runtime") == "gpu" and "device_target" not in node:
                    node["device_target"] = "RTX 3090 Ti"

        # Only attach runtime_admission if explicitly provided.
        if runtime_admission is not None:
            for tier_dict in tiers.values():
                if not isinstance(tier_dict, dict):
                    continue
                for node in tier_dict.values():
                    if isinstance(node, dict):
                        node["runtime_admission"] = dict(runtime_admission)

        _write_models_yaml(
            config_path,
            tiers=tiers,
            binary=binary,
            ik_flags=ik_flags,
            port_base=port_base,
        )
        if swarm:
            _write_swarm_yaml(swarm_path, **swarm)
        else:
            _write_swarm_yaml(swarm_path)

        # Wipe any existing state.
        state_path.parent.mkdir(parents=True, exist_ok=True)
        if state_path.exists():
            state_path.unlink()
        admission_path.parent.mkdir(parents=True, exist_ok=True)
        if admission_path.exists():
            admission_path.unlink()

        return ModelManager(
            config_path=config_path,
            swarm_path=swarm_path,
            admission_path=admission_path_override or admission_path,
        )

    return _factory


@pytest.fixture()
def binding() -> dict[str, str]:
    return _make_full_binding()


@pytest.fixture()
def device_uuid() -> str:
    return "GPU-uuid-aaaa"


def _validator_patch(value: dict[str, Any]):
    """Return a context manager that replaces the model_manager's
    ``validate_runtime_admission`` with a stub returning ``value``.

    We patch the local binding ``pheno.model_manager.validate_runtime_admission``
    rather than the stub module's attribute because the model_manager
    captured a reference at import time.
    """
    return patch(
        "pheno.model_manager.validate_runtime_admission",
        return_value=value,
    )


def _validator_patch_side_effect(side_effect: Any):
    """Same as ``_validator_patch`` but for a side_effect callable."""
    return patch(
        "pheno.model_manager.validate_runtime_admission",
        side_effect=side_effect,
    )


# ---------------------------------------------------------------------------
# build_cmd: template-mode path (lines 179-192)
# ---------------------------------------------------------------------------


class TestBuildCmdTemplateMode:
    """``build_cmd`` template-mode (args_tpl) path."""

    def test_template_mode_substitutes_subs(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
        tmp_path: Path,
    ) -> None:
        config_dir = tmp_path / "config"
        launch_dir = config_dir / "launch"
        launch_dir.mkdir(parents=True, exist_ok=True)
        (launch_dir / "qwen08b.yaml").write_text(
            json.dumps(
                {
                    "args": [
                        "{binary}",
                        "-m",
                        "{path}",
                        "--port",
                        "{port}",
                        "-c",
                        "{kv_ctx}",
                        "--ik",
                        "{ik_flags}",
                    ]
                }
            ),
            encoding="utf-8",
        )

        mm = manager_factory(
            ik_flags="-fa -fmoe",
            tiers={
                "local": {
                    "qwen08b": {
                        "id": "Qwen3.5-0.8B",
                        "path": str(fake_model_file),
                        "always_on": True,
                        "runtime": "gpu",
                        "device_target": "RTX 3090 Ti",
                    }
                }
            },
        )
        cmd = mm.build_cmd("local.qwen08b")
        assert cmd[0] == "llama-server"
        assert "-m" in cmd
        assert str(fake_model_file) in cmd
        assert "--port" in cmd
        assert "8080" in cmd
        assert "-c" in cmd
        assert "8192" in cmd
        assert "--ik" in cmd
        assert "-fa" in cmd
        assert "-fmoe" in cmd

    def test_template_mode_drops_empty_tokens(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
        tmp_path: Path,
    ) -> None:
        config_dir = tmp_path / "config"
        launch_dir = config_dir / "launch"
        launch_dir.mkdir(parents=True, exist_ok=True)
        (launch_dir / "qwen08b.yaml").write_text(
            json.dumps(
                {
                    "args": [
                        "{binary}",
                        "-m",
                        "{path}",
                        "--port",
                        "{port}",
                        "",
                        "{ik_flags}",  # empty -> becomes "" -> filtered
                    ]
                }
            ),
            encoding="utf-8",
        )

        mm = manager_factory(
            ik_flags="",
            tiers={
                "local": {
                    "qwen08b": {
                        "id": "Qwen3.5-0.8B",
                        "path": str(fake_model_file),
                        "always_on": True,
                        "runtime": "gpu",
                        "device_target": "RTX 3090 Ti",
                    }
                }
            },
        )
        cmd = mm.build_cmd("local.qwen08b")
        # All non-empty tokens preserved; no empty strings
        assert "" not in cmd
        assert cmd[0] == "llama-server"

    def test_template_mode_appends_extra_args(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
        tmp_path: Path,
    ) -> None:
        config_dir = tmp_path / "config"
        launch_dir = config_dir / "launch"
        launch_dir.mkdir(parents=True, exist_ok=True)
        (launch_dir / "qwen08b.yaml").write_text(
            json.dumps({"args": ["{binary}", "-m", "{path}", "--port", "{port}"]}),
            encoding="utf-8",
        )
        mm = manager_factory(
            tiers={
                "local": {
                    "qwen08b": {
                        "id": "Qwen3.5-0.8B",
                        "path": str(fake_model_file),
                        "always_on": True,
                        "runtime": "gpu",
                        "device_target": "RTX 3090 Ti",
                        "ik_llama_expert_offload": "-ngl 99 -fa",
                    }
                }
            },
        )
        cmd = mm.build_cmd("local.qwen08b")
        # extra_args come after template tokens
        assert "-ngl" in cmd
        assert "99" in cmd
        assert "-fa" in cmd

    def test_template_mode_appends_draft_args(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
        tmp_path: Path,
    ) -> None:
        config_dir = tmp_path / "config"
        launch_dir = config_dir / "launch"
        launch_dir.mkdir(parents=True, exist_ok=True)
        (launch_dir / "main.yaml").write_text(
            json.dumps(
                {
                    "args": ["{binary}", "-m", "{path}", "--port", "{port}"],
                    "draft_args": ["-draft", "{draft_path}"],
                }
            ),
            encoding="utf-8",
        )
        # Need a draft GGUF path that exists
        draft_file = tmp_path / "draft.gguf"
        draft_file.write_bytes(b"GGUF\x03\x00\x00\x00")
        mm = manager_factory(
            tiers={
                "local": {
                    "main": {
                        "id": "MainModel",
                        "path": str(fake_model_file),
                        "always_on": True,
                        "runtime": "gpu",
                        "device_target": "RTX 3090 Ti",
                        "draft_model": "local.draft",
                    },
                    "draft": {
                        "id": "DraftModel",
                        "path": str(draft_file),
                        "always_on": True,
                        "runtime": "cpu",  # so it doesn't get a port
                        "draft_for": "main",
                    },
                }
            },
        )
        cmd = mm.build_cmd("local.main")
        assert "-draft" in cmd
        assert str(draft_file) in cmd

    def test_inline_mode_unchanged(
        self, manager_factory: Callable[..., ModelManager]
    ) -> None:
        # Sanity: when no template exists, the inline path is used.
        mm = manager_factory()
        cmd = mm.build_cmd("local.qwen08b")
        assert cmd[0] == "llama-server"
        assert "-m" in cmd


# ---------------------------------------------------------------------------
# _validate_runtime_admission (lines 254-359)
# ---------------------------------------------------------------------------


class TestValidateRuntimeAdmission:
    """``_validate_runtime_admission`` covers every admission branch."""

    def test_admission_path_missing_raises(
        self, manager_factory: Callable[..., ModelManager]
    ) -> None:
        # No admission_path created → .is_file() is False
        mm = manager_factory()
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        with pytest.raises(RuntimeAdmissionError, match="missing or invalid"):
            mm._validate_runtime_admission(spec, ("llama-server",), "GPU-x")

    def test_binding_missing_raises(
        self,
        manager_factory: Callable[..., ModelManager],
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        mm = manager_factory()  # no runtime_admission in YAML
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        value = _make_admission_value(binding, _make_lane(binding))
        mm.admission_path.write_text("{}", encoding="utf-8")
        with _validator_patch(value):
            with pytest.raises(
                RuntimeAdmissionError, match="no exact runtime admission semantic"
            ):
                mm._validate_runtime_admission(
                    spec, ("llama-server",), device_uuid
                )

    def test_binding_wrong_type_raises(
        self,
        manager_factory: Callable[..., ModelManager],
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        mm = manager_factory(runtime_admission=binding)
        # Replace the binding with a list to break the isinstance check
        for tier_dict in mm.raw.get("tiers", {}).values():
            for node in tier_dict.values():
                if isinstance(node, dict):
                    node["runtime_admission"] = ["not", "a", "dict"]
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        value = _make_admission_value(binding, _make_lane(binding))
        mm.admission_path.write_text("{}", encoding="utf-8")
        with _validator_patch(value):
            with pytest.raises(
                RuntimeAdmissionError, match="no exact runtime admission semantic"
            ):
                mm._validate_runtime_admission(
                    spec, ("llama-server",), device_uuid
                )

    def test_binding_missing_keys_raises(
        self,
        manager_factory: Callable[..., ModelManager],
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        mm = manager_factory(runtime_admission=binding)
        # Remove one required key
        for tier_dict in mm.raw.get("tiers", {}).values():
            for node in tier_dict.values():
                if isinstance(node, dict):
                    node["runtime_admission"] = {
                        k: v for k, v in binding.items() if k != "lane_id"
                    }
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        value = _make_admission_value(binding, _make_lane(binding))
        mm.admission_path.write_text("{}", encoding="utf-8")
        with _validator_patch(value):
            with pytest.raises(
                RuntimeAdmissionError, match="no exact runtime admission semantic"
            ):
                mm._validate_runtime_admission(
                    spec, ("llama-server",), device_uuid
                )

    def test_binding_non_string_values_raises(
        self,
        manager_factory: Callable[..., ModelManager],
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        mm = manager_factory(runtime_admission=binding)
        for tier_dict in mm.raw.get("tiers", {}).values():
            for node in tier_dict.values():
                if isinstance(node, dict):
                    node["runtime_admission"] = {**binding, "lane_id": 12345}
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        value = _make_admission_value(binding, _make_lane(binding))
        mm.admission_path.write_text("{}", encoding="utf-8")
        with _validator_patch(value):
            with pytest.raises(
                RuntimeAdmissionError, match="no exact runtime admission semantic"
            ):
                mm._validate_runtime_admission(
                    spec, ("llama-server",), device_uuid
                )

    def test_validator_raises_oserror(
        self,
        manager_factory: Callable[..., ModelManager],
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        mm = manager_factory(runtime_admission=binding)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        mm.admission_path.write_text("{}", encoding="utf-8")
        with _validator_patch_side_effect(OSError("boom")):
            with pytest.raises(RuntimeAdmissionError, match="missing or invalid"):
                mm._validate_runtime_admission(
                    spec, ("llama-server",), device_uuid
                )

    def test_validator_raises_valueerror(
        self,
        manager_factory: Callable[..., ModelManager],
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        mm = manager_factory(runtime_admission=binding)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        mm.admission_path.write_text("{}", encoding="utf-8")
        with _validator_patch_side_effect(ValueError("boom")):
            with pytest.raises(RuntimeAdmissionError, match="missing or invalid"):
                mm._validate_runtime_admission(
                    spec, ("llama-server",), device_uuid
                )

    def test_validator_raises_typeerror(
        self,
        manager_factory: Callable[..., ModelManager],
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        mm = manager_factory(runtime_admission=binding)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        mm.admission_path.write_text("{}", encoding="utf-8")
        with _validator_patch_side_effect(TypeError("boom")):
            with pytest.raises(RuntimeAdmissionError, match="missing or invalid"):
                mm._validate_runtime_admission(
                    spec, ("llama-server",), device_uuid
                )

    def test_lane_missing_raises(
        self,
        manager_factory: Callable[..., ModelManager],
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        mm = manager_factory(runtime_admission=binding)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        mm.admission_path.write_text("{}", encoding="utf-8")
        value: dict[str, Any] = {"lanes": [], "admission_sha256": "a" * 64}
        with _validator_patch(value):
            with pytest.raises(RuntimeAdmissionError, match="lane is missing"):
                mm._validate_runtime_admission(
                    spec, ("llama-server",), device_uuid
                )

    def test_lane_duplicate_raises(
        self,
        manager_factory: Callable[..., ModelManager],
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        mm = manager_factory(runtime_admission=binding)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        mm.admission_path.write_text("{}", encoding="utf-8")
        lane = _make_lane(binding)
        value: dict[str, Any] = {
            "lanes": [lane, lane],
            "admission_sha256": "a" * 64,
        }
        with _validator_patch(value):
            with pytest.raises(RuntimeAdmissionError, match="non-unique"):
                mm._validate_runtime_admission(
                    spec, ("llama-server",), device_uuid
                )

    def test_model_id_mismatch_raises(
        self,
        manager_factory: Callable[..., ModelManager],
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        mm = manager_factory(runtime_admission=binding)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        # Tamper with node.id so it no longer equals binding["model_id"]
        for tier_dict in mm.raw.get("tiers", {}).values():
            for node in tier_dict.values():
                if isinstance(node, dict):
                    node["id"] = "DIFFERENT"
        mm.admission_path.write_text("{}", encoding="utf-8")
        value = _make_admission_value(binding, _make_lane(binding))
        with _validator_patch(value):
            with pytest.raises(RuntimeAdmissionError, match="semantic tuple mismatch"):
                mm._validate_runtime_admission(
                    spec, ("llama-server",), device_uuid
                )

    def test_request_candidate_id_mismatch_raises(
        self,
        manager_factory: Callable[..., ModelManager],
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        mm = manager_factory(runtime_admission=binding)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        mm.admission_path.write_text("{}", encoding="utf-8")
        value = _make_admission_value(
            binding,
            _make_lane(binding, request_override={"candidate_id": "WRONG"}),
        )
        with _validator_patch(value):
            with pytest.raises(RuntimeAdmissionError, match="semantic tuple mismatch"):
                mm._validate_runtime_admission(
                    spec, ("llama-server",), device_uuid
                )

    def test_artifact_candidate_id_mismatch_raises(
        self,
        manager_factory: Callable[..., ModelManager],
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        mm = manager_factory(runtime_admission=binding)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        mm.admission_path.write_text("{}", encoding="utf-8")
        value = _make_admission_value(
            binding, _make_lane(binding, artifact_candidate_id="WRONG")
        )
        with _validator_patch(value):
            with pytest.raises(RuntimeAdmissionError, match="semantic tuple mismatch"):
                mm._validate_runtime_admission(
                    spec, ("llama-server",), device_uuid
                )

    def test_artifact_cell_id_mismatch_raises(
        self,
        manager_factory: Callable[..., ModelManager],
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        mm = manager_factory(runtime_admission=binding)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        mm.admission_path.write_text("{}", encoding="utf-8")
        value = _make_admission_value(
            binding, _make_lane(binding, artifact_cell_id="WRONG")
        )
        with _validator_patch(value):
            with pytest.raises(RuntimeAdmissionError, match="semantic tuple mismatch"):
                mm._validate_runtime_admission(
                    spec, ("llama-server",), device_uuid
                )

    def test_artifact_device_id_mismatch_raises(
        self,
        manager_factory: Callable[..., ModelManager],
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        mm = manager_factory(runtime_admission=binding)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        mm.admission_path.write_text("{}", encoding="utf-8")
        value = _make_admission_value(
            binding, _make_lane(binding, artifact_device_id="WRONG")
        )
        with _validator_patch(value):
            with pytest.raises(RuntimeAdmissionError, match="semantic tuple mismatch"):
                mm._validate_runtime_admission(
                    spec, ("llama-server",), device_uuid
                )

    def test_artifact_runtime_mismatch_raises(
        self,
        manager_factory: Callable[..., ModelManager],
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        mm = manager_factory(runtime_admission=binding)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        mm.admission_path.write_text("{}", encoding="utf-8")
        value = _make_admission_value(
            binding, _make_lane(binding, artifact_runtime="WRONG")
        )
        with _validator_patch(value):
            with pytest.raises(RuntimeAdmissionError, match="semantic tuple mismatch"):
                mm._validate_runtime_admission(
                    spec, ("llama-server",), device_uuid
                )

    def test_artifact_sha_mismatch_raises(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        # Use a binding sha that differs from the actual file sha.
        mm = manager_factory(runtime_admission=binding)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        wrong_binding = {**binding, "artifact_sha256": "f" * 64}
        for tier_dict in mm.raw.get("tiers", {}).values():
            for node in tier_dict.values():
                if isinstance(node, dict):
                    node["runtime_admission"] = wrong_binding
        mm.admission_path.write_text("{}", encoding="utf-8")
        value = _make_admission_value(
            wrong_binding,
            _make_lane(wrong_binding, artifact_content_sha="f" * 64),
        )
        with _validator_patch(value):
            with pytest.raises(RuntimeAdmissionError, match="semantic tuple mismatch"):
                mm._validate_runtime_admission(
                    spec, ("llama-server",), device_uuid
                )

    def test_artifact_binding_sha_mismatch_raises(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        # binding sha = real file sha, but lane's content_sha256 differs
        real_sha = sha256(fake_model_file.read_bytes()).hexdigest()
        b = {**binding, "artifact_sha256": real_sha}
        mm = manager_factory(runtime_admission=b)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        mm.admission_path.write_text("{}", encoding="utf-8")
        value = _make_admission_value(
            b,
            _make_lane(b, artifact_content_sha="0" * 64),
        )
        with _validator_patch(value):
            with pytest.raises(RuntimeAdmissionError, match="semantic tuple mismatch"):
                mm._validate_runtime_admission(
                    spec, ("llama-server",), device_uuid
                )

    def test_device_uuid_mismatch_raises(
        self,
        manager_factory: Callable[..., ModelManager],
        binding: dict[str, str],
    ) -> None:
        mm = manager_factory(runtime_admission=binding)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        mm.admission_path.write_text("{}", encoding="utf-8")
        value = _make_admission_value(binding, _make_lane(binding))
        with _validator_patch(value):
            with pytest.raises(RuntimeAdmissionError, match="semantic tuple mismatch"):
                mm._validate_runtime_admission(
                    spec, ("llama-server",), "WRONG-UUID"
                )

    def test_command_binary_mismatch_raises(
        self,
        manager_factory: Callable[..., ModelManager],
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        mm = manager_factory(runtime_admission=binding)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        mm.admission_path.write_text("{}", encoding="utf-8")
        value = _make_admission_value(binding, _make_lane(binding))
        with _validator_patch(value):
            # cmd[0] = "different-server" doesn't match binding's "llama-server"
            with pytest.raises(RuntimeAdmissionError, match="semantic tuple mismatch"):
                mm._validate_runtime_admission(
                    spec, ("different-server",), device_uuid
                )

    def test_lease_device_uuid_drift_raises(
        self,
        manager_factory: Callable[..., ModelManager],
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        mm = manager_factory(runtime_admission=binding)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        mm.admission_path.write_text("{}", encoding="utf-8")
        value = _make_admission_value(
            binding,
            _make_lane(binding, lease_device_uuid="OTHER-UUID"),
        )
        with _validator_patch(value):
            with pytest.raises(RuntimeAdmissionError, match="semantic tuple mismatch"):
                mm._validate_runtime_admission(
                    spec, ("llama-server",), device_uuid
                )

    def test_lease_artifact_sha_drift_raises(
        self,
        manager_factory: Callable[..., ModelManager],
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        mm = manager_factory(runtime_admission=binding)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        mm.admission_path.write_text("{}", encoding="utf-8")
        value = _make_admission_value(
            binding,
            _make_lane(binding, lease_artifact_sha="OTHER-SHA"),
        )
        with _validator_patch(value):
            with pytest.raises(RuntimeAdmissionError, match="semantic tuple mismatch"):
                mm._validate_runtime_admission(
                    spec, ("llama-server",), device_uuid
                )

    def test_runtime_binding_runtime_drift_raises(
        self,
        manager_factory: Callable[..., ModelManager],
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        mm = manager_factory(runtime_admission=binding)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        mm.admission_path.write_text("{}", encoding="utf-8")
        value = _make_admission_value(
            binding,
            _make_lane(binding, runtime_binding_runtime="OTHER-RUNTIME"),
        )
        with _validator_patch(value):
            with pytest.raises(RuntimeAdmissionError, match="semantic tuple mismatch"):
                mm._validate_runtime_admission(
                    spec, ("llama-server",), device_uuid
                )

    def test_decision_not_admitted_raises(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        real_sha = sha256(fake_model_file.read_bytes()).hexdigest()
        b = {**binding, "artifact_sha256": real_sha}
        mm = manager_factory(runtime_admission=b)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        mm.admission_path.write_text("{}", encoding="utf-8")
        value = _make_admission_value(
            b,
            _make_lane(b, artifact_content_sha=real_sha, decision="denied"),
        )
        with _validator_patch(value):
            with pytest.raises(RuntimeAdmissionError, match="denied"):
                mm._validate_runtime_admission(
                    spec, ("llama-server",), device_uuid
                )

    def test_action_not_permitted_raises(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        real_sha = sha256(fake_model_file.read_bytes()).hexdigest()
        b = {**binding, "artifact_sha256": real_sha}
        mm = manager_factory(runtime_admission=b)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        mm.admission_path.write_text("{}", encoding="utf-8")
        value = _make_admission_value(
            b,
            _make_lane(b, artifact_content_sha=real_sha, action_permitted=False),
        )
        with _validator_patch(value):
            with pytest.raises(RuntimeAdmissionError, match="denied"):
                mm._validate_runtime_admission(
                    spec, ("llama-server",), device_uuid
                )

    def test_granted_false_raises(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        real_sha = sha256(fake_model_file.read_bytes()).hexdigest()
        b = {**binding, "artifact_sha256": real_sha}
        mm = manager_factory(runtime_admission=b)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        mm.admission_path.write_text("{}", encoding="utf-8")
        value = _make_admission_value(
            b,
            _make_lane(b, artifact_content_sha=real_sha, granted=False),
        )
        with _validator_patch(value):
            with pytest.raises(RuntimeAdmissionError, match="denied"):
                mm._validate_runtime_admission(
                    spec, ("llama-server",), device_uuid
                )

    def test_blockers_in_error_message(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        real_sha = sha256(fake_model_file.read_bytes()).hexdigest()
        b = {**binding, "artifact_sha256": real_sha}
        mm = manager_factory(runtime_admission=b)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        mm.admission_path.write_text("{}", encoding="utf-8")
        value = _make_admission_value(
            b,
            _make_lane(
                b,
                artifact_content_sha=real_sha,
                decision="denied",
                blockers=["missing_fingerprint", "stale_lease"],
            ),
        )
        with _validator_patch(value):
            with pytest.raises(
                RuntimeAdmissionError,
                match="missing_fingerprint,stale_lease",
            ):
                mm._validate_runtime_admission(
                    spec, ("llama-server",), device_uuid
                )

    def test_empty_cmd_raises(
        self,
        manager_factory: Callable[..., ModelManager],
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        # NOTE: When cmd is empty, the semantic-mismatch branch fires first
        # (command_binary = "" vs configured_binary = "llama-server"). The
        # ``incomplete`` branch at line 355 is therefore unreachable in normal
        # execution; this test documents that fact by asserting the actual
        # error observed.
        mm = manager_factory(runtime_admission=binding)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        mm.admission_path.write_text("{}", encoding="utf-8")
        value = _make_admission_value(binding, _make_lane(binding))
        with _validator_patch(value):
            with pytest.raises(RuntimeAdmissionError, match="semantic tuple mismatch"):
                mm._validate_runtime_admission(spec, (), device_uuid)

    def test_empty_device_uuid_raises(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
        binding: dict[str, str],
    ) -> None:
        # NOTE: When device_uuid is empty, the semantic-mismatch branch fires
        # first (device_uuid="" != binding["device_uuid"]="GPU-uuid-aaaa").
        # The ``incomplete`` branch at line 355 is unreachable when the
        # binding's device_uuid is a non-empty string, so this test documents
        # the actual behavior.
        real_sha = sha256(fake_model_file.read_bytes()).hexdigest()
        b = {**binding, "artifact_sha256": real_sha}
        mm = manager_factory(runtime_admission=b)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        mm.admission_path.write_text("{}", encoding="utf-8")
        value = _make_admission_value(
            b, _make_lane(b, artifact_content_sha=real_sha)
        )
        with _validator_patch(value):
            with pytest.raises(RuntimeAdmissionError, match="semantic tuple mismatch"):
                mm._validate_runtime_admission(spec, ("llama-server",), "")

    def test_success_returns_admission_sha(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
        binding: dict[str, str],
        device_uuid: str,
    ) -> None:
        # The artifact_sha256 in the binding must match the real file sha
        # for success.
        real_sha = sha256(fake_model_file.read_bytes()).hexdigest()
        b = {**binding, "artifact_sha256": real_sha}
        mm = manager_factory(runtime_admission=b)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        mm.admission_path.write_text("{}", encoding="utf-8")
        value = _make_admission_value(
            b,
            _make_lane(b, artifact_content_sha=real_sha),
            admission_sha=real_sha,
        )
        with _validator_patch(value):
            out = mm._validate_runtime_admission(
                spec, ("llama-server",), device_uuid
            )
        assert out == real_sha


# ---------------------------------------------------------------------------
# _prepare_start admission validation (lines 388-393)
# ---------------------------------------------------------------------------


class TestPrepareStartAdmission:
    """``_prepare_start`` admission_sha256 shape validation."""

    def test_admission_sha_not_64_hex_raises(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
    ) -> None:
        real_sha = sha256(fake_model_file.read_bytes()).hexdigest()
        b = _make_full_binding()
        b["artifact_sha256"] = real_sha
        mm = manager_factory(runtime_admission=b)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None

        # Set up admission so all checks pass, but admission_sha256 has wrong shape
        lane = _make_lane(b, artifact_content_sha=real_sha)
        value = _make_admission_value(
            b, lane, admission_sha="not-valid-hex-sha"
        )
        mm.admission_path.write_text("{}", encoding="utf-8")
        with _validator_patch(value), patch.object(
            mm,
            "launch_env",
            return_value={"CUDA_VISIBLE_DEVICES": "GPU-uuid-aaaa"},
        ):
            with pytest.raises(
                RuntimeAdmissionError, match="no content identity"
            ):
                mm._prepare_start("local.qwen08b")

    def test_admission_sha_non_string_raises(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
    ) -> None:
        real_sha = sha256(fake_model_file.read_bytes()).hexdigest()
        b = _make_full_binding()
        b["artifact_sha256"] = real_sha
        mm = manager_factory(runtime_admission=b)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None

        lane = _make_lane(b, artifact_content_sha=real_sha)
        value = _make_admission_value(b, lane, admission_sha=12345)  # not a string
        mm.admission_path.write_text("{}", encoding="utf-8")
        with _validator_patch(value), patch.object(
            mm,
            "launch_env",
            return_value={"CUDA_VISIBLE_DEVICES": "GPU-uuid-aaaa"},
        ):
            with pytest.raises(
                RuntimeAdmissionError, match="no content identity"
            ):
                mm._prepare_start("local.qwen08b")


# ---------------------------------------------------------------------------
# _spawn_prepared (lines 402-430)
# ---------------------------------------------------------------------------


class TestSpawnPrepared:
    """``_spawn_prepared`` actually spawns subprocesses and mutates state."""

    def test_spawn_prepared_popen_called(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
    ) -> None:
        real_sha = sha256(fake_model_file.read_bytes()).hexdigest()
        b = _make_full_binding()
        b["artifact_sha256"] = real_sha
        mm = manager_factory(runtime_admission=b)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None

        prepared = PreparedLaunch(
            spec=spec,
            cmd=("llama-server", "-m", str(fake_model_file)),
            env={"CUDA_VISIBLE_DEVICES": "GPU-uuid-aaaa"},
            device_uuid="GPU-uuid-aaaa",
            admission_sha256=real_sha,
        )

        fake_proc = MagicMock()
        fake_proc.pid = 99999
        with patch(
            "pheno.model_manager.subprocess.Popen", return_value=fake_proc
        ), patch("pheno.model_manager.time.sleep"):  # don't actually sleep
            result = mm._spawn_prepared(prepared)

        assert result["status"] == "started"
        assert result["name"] == "local.qwen08b"
        assert result["pid"] == 99999
        assert result["port"] == spec.port
        assert result["admission_sha256"] == real_sha
        assert result["device_uuid"] == "GPU-uuid-aaaa"
        assert result["cmd"] == ["llama-server", "-m", str(fake_model_file)]

    def test_spawn_prepared_registers_proc(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
    ) -> None:
        real_sha = sha256(fake_model_file.read_bytes()).hexdigest()
        b = _make_full_binding()
        b["artifact_sha256"] = real_sha
        mm = manager_factory(runtime_admission=b)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None

        prepared = PreparedLaunch(
            spec=spec,
            cmd=("llama-server",),
            env={"CUDA_VISIBLE_DEVICES": "GPU-uuid-aaaa"},
            device_uuid="GPU-uuid-aaaa",
            admission_sha256=real_sha,
        )
        fake_proc = MagicMock()
        with patch(
            "pheno.model_manager.subprocess.Popen", return_value=fake_proc
        ), patch("pheno.model_manager.time.sleep"):
            mm._spawn_prepared(prepared)
        # Process registered
        assert mm._procs["local.qwen08b"] is fake_proc

    def test_spawn_prepared_saves_state_with_admission(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
    ) -> None:
        real_sha = sha256(fake_model_file.read_bytes()).hexdigest()
        b = _make_full_binding()
        b["artifact_sha256"] = real_sha
        mm = manager_factory(runtime_admission=b)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None

        prepared = PreparedLaunch(
            spec=spec,
            cmd=("llama-server",),
            env={"CUDA_VISIBLE_DEVICES": "GPU-uuid-aaaa"},
            device_uuid="GPU-uuid-aaaa",
            admission_sha256=real_sha,
        )
        fake_proc = MagicMock()
        with patch(
            "pheno.model_manager.subprocess.Popen", return_value=fake_proc
        ), patch("pheno.model_manager.time.sleep"):
            mm._spawn_prepared(prepared)
        state = mm.load_state()
        assert "local.qwen08b" in state["loaded"]
        assert state["ports"]["local.qwen08b"] == spec.port
        assert "local.qwen08b" in state["admissions"]
        assert state["admissions"]["local.qwen08b"]["admission_sha256"] == real_sha
        assert state["admissions"]["local.qwen08b"]["device_uuid"] == "GPU-uuid-aaaa"

    def test_spawn_prepared_no_duplicate_state_entry(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
    ) -> None:
        real_sha = sha256(fake_model_file.read_bytes()).hexdigest()
        b = _make_full_binding()
        b["artifact_sha256"] = real_sha
        mm = manager_factory(runtime_admission=b)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None

        # Pre-populate state with the model already loaded
        mm.save_state(
            {
                "loaded": ["local.qwen08b"],
                "always_on": [],
                "ports": {},
                "admissions": {},
            }
        )

        prepared = PreparedLaunch(
            spec=spec,
            cmd=("llama-server",),
            env={"CUDA_VISIBLE_DEVICES": "GPU-uuid-aaaa"},
            device_uuid="GPU-uuid-aaaa",
            admission_sha256=real_sha,
        )
        fake_proc = MagicMock()
        with patch(
            "pheno.model_manager.subprocess.Popen", return_value=fake_proc
        ), patch("pheno.model_manager.time.sleep"):
            mm._spawn_prepared(prepared)
        state = mm.load_state()
        # No duplicate appended
        assert state["loaded"].count("local.qwen08b") == 1


# ---------------------------------------------------------------------------
# start() non-dry-run end-to-end (line 445)
# ---------------------------------------------------------------------------


class TestStartRealSpawn:
    """``start(dry_run=False)`` end-to-end."""

    def test_start_spawns_via_popen(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
    ) -> None:
        real_sha = sha256(fake_model_file.read_bytes()).hexdigest()
        b = _make_full_binding()
        b["artifact_sha256"] = real_sha
        mm = manager_factory(runtime_admission=b)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        # Stage the admission value (correct sha)
        value = _make_admission_value(
            b,
            _make_lane(b, artifact_content_sha=real_sha),
            admission_sha=real_sha,
        )
        mm.admission_path.write_text("{}", encoding="utf-8")
        with _validator_patch(value), patch.object(
            mm, "launch_env", return_value={"CUDA_VISIBLE_DEVICES": "GPU-uuid-aaaa"}
        ), patch("pheno.model_manager.subprocess.Popen") as mock_popen, patch(
            "pheno.model_manager.time.sleep"
        ):
            mock_popen.return_value = MagicMock(pid=4242)
            result = mm.start("local.qwen08b", dry_run=False)
        assert result["status"] == "started"
        assert result["name"] == "local.qwen08b"
        assert result["pid"] == 4242
        mock_popen.assert_called_once()

    def test_start_propagates_runtime_admission_error(
        self,
        manager_factory: Callable[..., ModelManager],
    ) -> None:
        mm = manager_factory()  # No runtime_admission → raises
        with patch.object(mm, "launch_env", return_value={}):
            with pytest.raises(RuntimeAdmissionError):
                mm.start("local.qwen08b", dry_run=False)

    def test_start_with_unknown_model_raises(
        self,
        manager_factory: Callable[..., ModelManager],
    ) -> None:
        mm = manager_factory()
        with pytest.raises(ValueError, match="Unknown model"):
            mm.start("does.not.exist", dry_run=False)


# ---------------------------------------------------------------------------
# swap_to() non-dry-run end-to-end (lines 477-478)
# ---------------------------------------------------------------------------


class TestSwapToRealSpawn:
    """``swap_to(dry_run=False)`` stops on-demand then spawns."""

    def test_swap_to_spawns_via_popen(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
    ) -> None:
        real_sha = sha256(fake_model_file.read_bytes()).hexdigest()
        b = _make_full_binding()
        b["artifact_sha256"] = real_sha
        mm = manager_factory(runtime_admission=b)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        # Stage the admission value
        value = _make_admission_value(
            b,
            _make_lane(b, artifact_content_sha=real_sha),
            admission_sha=real_sha,
        )
        mm.admission_path.write_text("{}", encoding="utf-8")
        with _validator_patch(value), patch.object(
            mm, "launch_env", return_value={"CUDA_VISIBLE_DEVICES": "GPU-uuid-aaaa"}
        ), patch("pheno.model_manager.subprocess.Popen") as mock_popen, patch(
            "pheno.model_manager.time.sleep"
        ):
            mock_popen.return_value = MagicMock(pid=7777)
            result = mm.swap_to("local.qwen08b", dry_run=False)
        assert result["status"] == "started"
        assert result["name"] == "local.qwen08b"
        mock_popen.assert_called_once()

    def test_swap_to_calls_stop_on_demand(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
    ) -> None:
        real_sha = sha256(fake_model_file.read_bytes()).hexdigest()
        b = _make_full_binding()
        b["artifact_sha256"] = real_sha
        mm = manager_factory(runtime_admission=b)
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        value = _make_admission_value(
            b,
            _make_lane(b, artifact_content_sha=real_sha),
            admission_sha=real_sha,
        )
        mm.admission_path.write_text("{}", encoding="utf-8")
        with _validator_patch(value), patch.object(
            mm,
            "launch_env",
            return_value={"CUDA_VISIBLE_DEVICES": "GPU-uuid-aaaa"},
        ), patch.object(mm, "stop_on_demand") as mock_stop, patch(
            "pheno.model_manager.subprocess.Popen", return_value=MagicMock(pid=1)
        ), patch("pheno.model_manager.time.sleep"):
            mm.swap_to("local.qwen08b", dry_run=False)
        # stop_on_demand must run before spawn
        mock_stop.assert_called_once()


# ---------------------------------------------------------------------------
# _launch_template edge cases
# ---------------------------------------------------------------------------


class TestLaunchTemplate:
    """``_launch_template`` loads config/launch/<key>.yaml."""

    def test_no_launch_template_returns_empty(
        self, manager_factory: Callable[..., ModelManager]
    ) -> None:
        mm = manager_factory()
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        tpl = mm._launch_template(spec)
        assert tpl == {}

    def test_launch_template_loads_yaml(
        self,
        manager_factory: Callable[..., ModelManager],
        tmp_path: Path,
    ) -> None:
        mm = manager_factory()
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        # Drop a launch template named after the spec's key
        config_dir = tmp_path / "config"
        launch_dir = config_dir / "launch"
        launch_dir.mkdir(parents=True, exist_ok=True)
        (launch_dir / "qwen08b.yaml").write_text(
            json.dumps({"args": ["x", "y"], "draft_args": ["z"]}),
            encoding="utf-8",
        )
        tpl = mm._launch_template(spec)
        assert tpl == {"args": ["x", "y"], "draft_args": ["z"]}

    def test_launch_template_uses_explicit_template_name(
        self,
        manager_factory: Callable[..., ModelManager],
        tmp_path: Path,
    ) -> None:
        mm = manager_factory()
        # Find the spec and override its launch_template
        spec: ModelSpec | None = None
        for s in mm.list_models():
            if s.name == "local.qwen08b":
                s.launch_template = "alternate"
                spec = s
                break
        assert spec is not None
        config_dir = tmp_path / "config"
        launch_dir = config_dir / "launch"
        launch_dir.mkdir(parents=True, exist_ok=True)
        (launch_dir / "alternate.yaml").write_text(
            json.dumps({"args": ["alt"]}), encoding="utf-8"
        )
        tpl = mm._launch_template(spec)
        assert tpl == {"args": ["alt"]}

    def test_launch_template_empty_yaml_returns_empty(
        self,
        manager_factory: Callable[..., ModelManager],
        tmp_path: Path,
    ) -> None:
        mm = manager_factory()
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        config_dir = tmp_path / "config"
        launch_dir = config_dir / "launch"
        launch_dir.mkdir(parents=True, exist_ok=True)
        (launch_dir / "qwen08b.yaml").write_text("", encoding="utf-8")
        # yaml.safe_load("") returns None → {} after the `or {}`
        tpl = mm._launch_template(spec)
        assert tpl == {}


# ---------------------------------------------------------------------------
# start(dry_run=True) / swap_to(dry_run=True) (lines 432-444, 464-476)
# ---------------------------------------------------------------------------


class TestDryRunBranches:
    """``start(dry_run=True)`` / ``swap_to(dry_run=True)`` short-circuit."""

    def test_start_dry_run_returns_dry_run_dict(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
    ) -> None:
        real_sha = sha256(fake_model_file.read_bytes()).hexdigest()
        b = _make_full_binding()
        b["artifact_sha256"] = real_sha
        mm = manager_factory(runtime_admission=b)
        value = _make_admission_value(
            b,
            _make_lane(b, artifact_content_sha=real_sha),
            admission_sha=real_sha,
        )
        mm.admission_path.write_text("{}", encoding="utf-8")
        with _validator_patch(value), patch.object(
            mm,
            "launch_env",
            return_value={"CUDA_VISIBLE_DEVICES": "GPU-uuid-aaaa"},
        ):
            result = mm.start("local.qwen08b", dry_run=True)
        assert result["status"] == "dry_run"
        assert result["name"] == "local.qwen08b"
        assert result["cmd"][0] == "llama-server"
        assert result["admission_sha256"] == real_sha
        assert result["device_uuid"] == "GPU-uuid-aaaa"

    def test_swap_to_dry_run_returns_dry_run_dict(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
    ) -> None:
        real_sha = sha256(fake_model_file.read_bytes()).hexdigest()
        b = _make_full_binding()
        b["artifact_sha256"] = real_sha
        mm = manager_factory(runtime_admission=b)
        value = _make_admission_value(
            b,
            _make_lane(b, artifact_content_sha=real_sha),
            admission_sha=real_sha,
        )
        mm.admission_path.write_text("{}", encoding="utf-8")
        with _validator_patch(value), patch.object(
            mm,
            "launch_env",
            return_value={"CUDA_VISIBLE_DEVICES": "GPU-uuid-aaaa"},
        ):
            result = mm.swap_to("local.qwen08b", dry_run=True)
        assert result["status"] == "dry_run"
        assert result["name"] == "local.qwen08b"
        assert result["admission_sha256"] == real_sha

    def test_start_returns_prepare_start_dict(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
    ) -> None:
        # When _prepare_start returns a "skipped" dict, start() should
        # propagate it without further validation.
        mm = manager_factory(
            tiers={
                "local": {
                    "qwen08b": {
                        "id": "Qwen3.5-0.8B",
                        "path": str(fake_model_file),
                        "always_on": False,
                        "kv_ctx": 1024,
                        "runtime": "cpu",
                    }
                }
            },
        )
        result = mm.start("local.qwen08b", dry_run=True)
        assert result["status"] == "skipped"

    def test_swap_to_returns_prepare_start_dict(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
    ) -> None:
        mm = manager_factory(
            tiers={
                "local": {
                    "qwen08b": {
                        "id": "Qwen3.5-0.8B",
                        "path": str(fake_model_file),
                        "always_on": False,
                        "kv_ctx": 1024,
                        "runtime": "cpu",
                    }
                }
            },
        )
        result = mm.swap_to("local.qwen08b", dry_run=False)
        assert result["status"] == "skipped"


# ---------------------------------------------------------------------------
# _prepare_start skipped branches (lines 365-382)
# ---------------------------------------------------------------------------


class TestPrepareStartSkipped:
    """``_prepare_start`` returns early for cpu / draft / no-port / missing-GGUF."""

    def test_cpu_model_is_skipped(
        self, manager_factory: Callable[..., ModelManager], fake_model_file: Path
    ) -> None:
        mm = manager_factory(
            tiers={
                "local": {
                    "qwen08b": {
                        "id": "Qwen3.5-0.8B",
                        "path": str(fake_model_file),
                        "always_on": False,
                        "kv_ctx": 8192,
                        "runtime": "cpu",
                    }
                }
            },
        )
        result = mm._prepare_start("local.qwen08b")
        assert result["status"] == "skipped"
        assert result["name"] == "local.qwen08b"
        assert "cpu-only" in result["reason"]

    def test_draft_for_model_is_skipped(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
        tmp_path: Path,
    ) -> None:
        draft_file = tmp_path / "draft.gguf"
        draft_file.write_bytes(b"GGUF\x03\x00\x00\x00")
        mm = manager_factory(
            tiers={
                "local": {
                    "main": {
                        "id": "MainModel",
                        "path": str(fake_model_file),
                        "always_on": True,
                        "kv_ctx": 8192,
                        "runtime": "gpu",
                        "device_target": "RTX 3090 Ti",
                        "draft_model": "local.draft",
                    },
                    "draft": {
                        "id": "DraftModel",
                        "path": str(draft_file),
                        "always_on": True,
                        "kv_ctx": 1024,
                        "runtime": "cpu",
                        "draft_for": "main",
                    },
                }
            },
        )
        result = mm._prepare_start("local.draft")
        assert result["status"] == "skipped"
        assert "cpu-only" in result["reason"]

    def test_missing_gguf_is_skipped(
        self, manager_factory: Callable[..., ModelManager]
    ) -> None:
        mm = manager_factory(
            tiers={
                "local": {
                    "qwen08b": {
                        "id": "Qwen3.5-0.8B",
                        "path": "/nonexistent/path/model.gguf",
                        "always_on": True,
                        "kv_ctx": 8192,
                        "runtime": "gpu",
                        "device_target": "RTX 3090 Ti",
                    }
                }
            },
        )
        result = mm._prepare_start("local.qwen08b")
        assert result["status"] == "skipped"
        assert "GGUF missing" in result["reason"]


# ---------------------------------------------------------------------------
# status() / stop_on_demand / ensure_always_on (lines 447-503)
# ---------------------------------------------------------------------------


class TestLifecycle:
    """``status`` / ``stop_on_demand`` / ``ensure_always_on`` integration."""

    def test_status_includes_models(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
    ) -> None:
        mm = manager_factory()
        result = mm.status()
        assert "state" in result
        assert "models" in result
        # local.qwen08b is GPU with a port → row included
        names = [row["name"] for row in result["models"]]
        assert "local.qwen08b" in names

    def test_status_row_has_fields(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
    ) -> None:
        mm = manager_factory()
        result = mm.status()
        row = next(r for r in result["models"] if r["name"] == "local.qwen08b")
        assert row["always_on"] is True
        assert row["port"] == 8080
        assert row["endpoint"] == "http://127.0.0.1:8080/v1"
        assert row["gguf_exists"] is True
        assert row["draft_model"] is None

    def test_status_skips_cpu_models(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
    ) -> None:
        mm = manager_factory(
            tiers={
                "local": {
                    "main": {
                        "id": "Main",
                        "path": str(fake_model_file),
                        "always_on": True,
                        "kv_ctx": 8192,
                        "runtime": "gpu",
                        "device_target": "RTX 3090 Ti",
                    },
                    "helper": {
                        "id": "Helper",
                        "path": str(fake_model_file),
                        "always_on": False,
                        "kv_ctx": 1024,
                        "runtime": "cpu",
                    },
                }
            },
        )
        result = mm.status()
        names = [r["name"] for r in result["models"]]
        assert "local.main" in names
        assert "local.helper" not in names

    def test_stop_on_demand_terminates_non_always_on(
        self,
        manager_factory: Callable[..., ModelManager],
        fake_model_file: Path,
    ) -> None:
        real_sha = sha256(fake_model_file.read_bytes()).hexdigest()
        b = _make_full_binding()
        b["artifact_sha256"] = real_sha
        mm = manager_factory(runtime_admission=b)
        # Ensure the qwen08b spec is in _spec_index (it is, from list_models)
        # but list_models() caches - let's just add our on-demand spec by
        # calling list_models() first to populate _spec_index, then add ours.
        mm.list_models()
        spec_od = ModelSpec(
            name="local.on_demand",
            path=str(fake_model_file),
            port=0,
            always_on=False,
            on_demand=True,
            runtime="gpu",
            device_target="RTX 3090 Ti",
        )
        mm._spec_index["local.on_demand"] = spec_od
        fake_proc = MagicMock()
        mm._procs["local.on_demand"] = fake_proc
        mm._procs["local.qwen08b"] = MagicMock()  # always_on, should NOT terminate
        mm.save_state(
            {
                "loaded": ["local.on_demand", "local.qwen08b"],
                "always_on": ["local.qwen08b"],
                "ports": {},
                "admissions": {},
            }
        )
        mm.stop_on_demand()
        # The on-demand proc got terminated and was deleted from index
        assert "local.on_demand" not in mm._procs
        fake_proc.terminate.assert_called_once()
        # Always-on was left alone
        assert "local.qwen08b" in mm._procs
        # State reflects removal
        state = mm.load_state()
        assert "local.on_demand" not in state["loaded"]
        assert "local.qwen08b" in state["loaded"]

    def test_ensure_always_on_dry_run(
        self, manager_factory: Callable[..., ModelManager], fake_model_file: Path
    ) -> None:
        real_sha = sha256(fake_model_file.read_bytes()).hexdigest()
        b = _make_full_binding()
        b["artifact_sha256"] = real_sha
        mm = manager_factory(runtime_admission=b)
        value = _make_admission_value(
            b,
            _make_lane(b, artifact_content_sha=real_sha),
            admission_sha=real_sha,
        )
        mm.admission_path.write_text("{}", encoding="utf-8")
        with _validator_patch(value), patch.object(
            mm,
            "launch_env",
            return_value={"CUDA_VISIBLE_DEVICES": "GPU-uuid-aaaa"},
        ):
            results = mm.ensure_always_on(dry_run=True)
        assert len(results) == 1
        assert results[0]["status"] == "dry_run"
        assert results[0]["name"] == "local.qwen08b"


# ---------------------------------------------------------------------------
# _expand / build_cmd ValueError / ik_flags_for_spec (lines 80-87, 155-156, 172-206)
# ---------------------------------------------------------------------------


class TestExpandAndBuildCmd:
    """Smaller helpers not exercised elsewhere."""

    def test_expand_with_default(
        self, manager_factory: Callable[..., ModelManager]
    ) -> None:
        mm = manager_factory()
        # ${UNSET_VAR:-fallback} -> fallback when env var unset
        assert mm._expand("${UNSET_VAR:-fallback}") == "fallback"
        # Empty string returns empty
        assert mm._expand("") == ""

    def test_expand_uses_env_when_set(
        self, manager_factory: Callable[..., ModelManager], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PHENO_TEST_VAR", "set-value")
        mm = manager_factory()
        assert mm._expand("${PHENO_TEST_VAR:-fallback}") == "set-value"

    def test_build_cmd_unknown_model_raises(
        self, manager_factory: Callable[..., ModelManager]
    ) -> None:
        mm = manager_factory()
        with pytest.raises(ValueError, match="Unknown model"):
            mm.build_cmd("does.not.exist")

    def test_ik_flags_strips_c_token(
        self, manager_factory: Callable[..., ModelManager], fake_model_file: Path
    ) -> None:
        mm = manager_factory(
            ik_flags="-fa -c 32768 -rtr",
            tiers={
                "local": {
                    "qwen08b": {
                        "id": "Qwen3.5-0.8B",
                        "path": str(fake_model_file),
                        "always_on": True,
                        "runtime": "gpu",
                        "device_target": "RTX 3090 Ti",
                    }
                }
            },
        )
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        # _ik_flags_for_spec removes "-c <number>" tokens (double-space stays)
        assert mm._ik_flags_for_spec(spec) == "-fa  -rtr"
        # Inline-mode build_cmd also consumes the stripped flags
        cmd = mm.build_cmd("local.qwen08b")
        assert "-fa" in cmd
        assert "-rtr" in cmd
        assert "32768" not in cmd  # the -c 32768 was stripped

    def test_extra_args_parses_lines(
        self, manager_factory: Callable[..., ModelManager], fake_model_file: Path
    ) -> None:
        mm = manager_factory(
            tiers={
                "local": {
                    "qwen08b": {
                        "id": "Qwen3.5-0.8B",
                        "path": str(fake_model_file),
                        "always_on": True,
                        "runtime": "gpu",
                        "device_target": "RTX 3090 Ti",
                        # Mix empty lines / whitespace-only lines so the
                        # `if line.strip():` skip branch fires.
                        "ik_llama_expert_offload": "-ngl 99\n\n   \n--foo bar",
                    }
                }
            },
        )
        cmd = mm.build_cmd("local.qwen08b")
        assert "-ngl" in cmd
        assert "99" in cmd
        assert "--foo" in cmd
        assert "bar" in cmd

    def test_extra_args_empty_returns_empty_list(
        self, manager_factory: Callable[..., ModelManager], fake_model_file: Path
    ) -> None:
        mm = manager_factory(
            tiers={
                "local": {
                    "qwen08b": {
                        "id": "Qwen3.5-0.8B",
                        "path": str(fake_model_file),
                        "always_on": True,
                        "runtime": "gpu",
                        "device_target": "RTX 3090 Ti",
                    }
                }
            },
        )
        for node in mm.raw["tiers"]["local"].values():
            assert mm._extra_args(node) == []

    def test_list_models_skips_non_dict_nodes(
        self, manager_factory: Callable[..., ModelManager], fake_model_file: Path
    ) -> None:
        mm = manager_factory(
            tiers={
                "local": {
                    "qwen08b": {
                        "id": "Qwen3.5-0.8B",
                        "path": str(fake_model_file),
                        "always_on": True,
                        "runtime": "gpu",
                        "device_target": "RTX 3090 Ti",
                    },
                    "garbage_str": "not a dict",  # skipped
                    "no_path": {  # skipped (no "path" key)
                        "id": "NoPathModel",
                        "always_on": True,
                    },
                },
                "broken_tier": "this is not a dict",  # tier-level skip
            },
        )
        specs_out = [s.name for s in mm.list_models()]
        assert "local.qwen08b" in specs_out
        assert "local.garbage_str" not in specs_out
        assert "local.no_path" not in specs_out
        assert "broken_tier" not in specs_out

    def test_no_port_spec_is_skipped(
        self, manager_factory: Callable[..., ModelManager], fake_model_file: Path
    ) -> None:
        # CPU + no draft_for model has port=0; the "no server port" branch
        # is reached by adding a GPU model whose port allocation chain
        # produces 0 (which doesn't happen in normal config), so we just
        # craft a gpu tier with runtime=cpu-like override. Actually port=0
        # only happens for cpu/draft models. We just patch the spec.
        mm = manager_factory()
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        # Force port to 0 to exercise the no-port branch
        spec.port = 0  # type: ignore[misc]
        result = mm._prepare_start("local.qwen08b")
        assert result["status"] == "skipped"
        assert "no server port" in result["reason"]


# ---------------------------------------------------------------------------
# launch_env / _resolve_device_uuid (lines 215-244)
# ---------------------------------------------------------------------------


class TestLaunchEnv:
    """``launch_env`` injects CUDA_VISIBLE_DEVICES for gpu models."""

    def test_launch_env_returns_os_environ_for_cpu(
        self, manager_factory: Callable[..., ModelManager], fake_model_file: Path
    ) -> None:
        mm = manager_factory(
            tiers={
                "local": {
                    "qwen08b": {
                        "id": "Qwen3.5-0.8B",
                        "path": str(fake_model_file),
                        "always_on": False,
                        "kv_ctx": 1024,
                        "runtime": "cpu",
                    }
                }
            },
        )
        env = mm.launch_env("local.qwen08b")
        # CPU model returns os.environ copy - no CUDA_VISIBLE_DEVICES injection
        assert "CUDA_VISIBLE_DEVICES" not in env

    def test_launch_env_unknown_model_raises(
        self, manager_factory: Callable[..., ModelManager]
    ) -> None:
        mm = manager_factory()
        with pytest.raises(ValueError, match="Unknown model"):
            mm.launch_env("does.not.exist")

    def test_launch_env_injects_cuda_visible_devices(
        self, manager_factory: Callable[..., ModelManager], fake_model_file: Path
    ) -> None:
        mm = manager_factory()
        with patch.object(
            mm, "_resolve_device_uuid", return_value="GPU-FAKE-UUID-1"
        ) as mock_rrd:
            env = mm.launch_env("local.qwen08b")
        mock_rrd.assert_called_once()
        assert env["CUDA_VISIBLE_DEVICES"] == "GPU-FAKE-UUID-1"
        assert env["CUDA_DEVICE_ORDER"] == "PCI_BUS_ID"

    def test_resolve_device_uuid_target_unavailable(
        self, manager_factory: Callable[..., ModelManager], fake_model_file: Path
    ) -> None:
        import subprocess as _subprocess
        mm = manager_factory()
        with patch.object(
            _subprocess,
            "run",
            return_value=MagicMock(returncode=1, stdout=""),
        ):
            with pytest.raises(RuntimeError, match="not uniquely available"):
                mm._resolve_device_uuid("RTX 3090 Ti")

    def test_resolve_device_uuid_no_match_for_target(
        self, manager_factory: Callable[..., ModelManager], fake_model_file: Path
    ) -> None:
        import subprocess as _subprocess
        mm = manager_factory()
        # nvidia-smi returns a UUID but with a different name
        csv_line = "GPU-aaaa, RTX 4090"
        with patch.object(
            _subprocess,
            "run",
            return_value=MagicMock(returncode=0, stdout=csv_line),
        ):
            with pytest.raises(RuntimeError, match="not uniquely available"):
                mm._resolve_device_uuid("RTX 3090 Ti")

    def test_resolve_device_uuid_multiple_matches_raises(
        self, manager_factory: Callable[..., ModelManager], fake_model_file: Path
    ) -> None:
        import subprocess as _subprocess
        mm = manager_factory()
        # Two rows with the same name → "not uniquely available"
        csv_lines = "GPU-aaaa, RTX 3090 Ti\nGPU-bbbb, RTX 3090 Ti"
        with patch.object(
            _subprocess,
            "run",
            return_value=MagicMock(returncode=0, stdout=csv_lines),
        ):
            with pytest.raises(RuntimeError, match="not uniquely available"):
                mm._resolve_device_uuid("RTX 3090 Ti")

    def test_resolve_device_uuid_returns_match(
        self, manager_factory: Callable[..., ModelManager], fake_model_file: Path
    ) -> None:
        import subprocess as _subprocess
        mm = manager_factory()
        csv_line = "GPU-uuid-aaaa, RTX 3090 Ti"
        with patch.object(
            _subprocess,
            "run",
            return_value=MagicMock(returncode=0, stdout=csv_line),
        ):
            result = mm._resolve_device_uuid("RTX 3090 Ti")
        assert result == "GPU-uuid-aaaa"

    def test_resolve_device_uuid_empty_target_raises(
        self, manager_factory: Callable[..., ModelManager]
    ) -> None:
        mm = manager_factory()
        with pytest.raises(ValueError, match="missing an explicit device_target"):
            mm._resolve_device_uuid("")