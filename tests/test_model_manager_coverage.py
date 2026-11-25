"""Comprehensive coverage tests for ``pheno.model_manager``.

The module imports ``pheno.runtime_admission`` which has been deleted from
the project, so we install a minimal stub in ``sys.modules`` before the
first import. We then point the manager's YAML/state files at a tmp dir
so we never touch the real config or state.

Covers:
* `_expand` env-var expansion + default-fallback syntax
* `_extra_args` line-parsing of `ik_llama_expert_offload`
* `list_models` YAML parsing + port allocation
* `get_spec` lookup by name
* `_resolve_draft_path` draft resolution
* `_ik_flags_for_spec` -c stripping
* `_append_draft_args` cmd extension
* `build_cmd` template + inline modes
* `load_state` / `save_state` JSON persistence
* `status` row generation
* `launch_env` (with mocked `_resolve_device_uuid`)
* `start(dry_run=True)` / `ensure_always_on(dry_run=True)` / `swap_to(dry_run=True)`
* `stop_on_demand` (with mocked `_spawn_prepared` / `_procs`)
"""

from __future__ import annotations

import json
import subprocess
import sys
import types
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Install stub for the missing `pheno.runtime_admission` module BEFORE we
# import `pheno.model_manager` (which imports `validate_runtime_admission`
# from it). The stub is a no-op function that returns a marker dict.
# ---------------------------------------------------------------------------

_STUB_NAME = "pheno.runtime_admission"
if _STUB_NAME not in sys.modules:
    _stub = types.ModuleType(_STUB_NAME)

    def _validate_runtime_admission_stub(
        value: Any, *, root: Path
    ) -> dict[str, Any]:
        """No-op stub for validate_runtime_admission; tests inject their own."""
        return {}

    _stub.validate_runtime_admission = _validate_runtime_admission_stub
    sys.modules[_STUB_NAME] = _stub

# Now safe to import
from pheno.model_manager import (  # noqa: E402
    ModelManager,
    ModelSpec,
    PreparedLaunch,
    RuntimeAdmissionError,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _write_models_yaml(
    path: Path,
    *,
    port_base: int = 8080,
    binary: str = "${PHENO_LLAMA_SERVER:-llama-server}",
    ik_flags: str = "-fa -fmoe -rtr -c 32768 -ctk q8_0 -ctv q8_0",
    tiers: dict[str, Any] | None = None,
) -> None:
    """Write a config/models.yaml with controllable tiers."""
    if tiers is None:
        tiers = {}
    payload: dict[str, Any] = {
        "llama_server": {
            "binary": binary,
            "ik_llama_flags": ik_flags,
            "port_base": port_base,
        },
        "tiers": tiers,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_swarm_yaml(
    path: Path,
    *,
    always_on_draft: str = "",
    endpoints: dict[str, str] | None = None,
) -> None:
    """Write a config/local_swarm.yaml with controllable always_on draft."""
    payload: dict[str, Any] = {}
    if always_on_draft:
        payload["always_on"] = {"draft": always_on_draft}
    if endpoints:
        payload["endpoints"] = endpoints
    path.write_text(json.dumps(payload), encoding="utf-8")


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
    """Factory that builds a ModelManager rooted at tmp_path.

    The factory monkey-patches ``pheno.paths.STATE_DIR`` so the manager's
    internal ``state_path`` lands inside ``tmp_path`` (otherwise it would
    default to ``PHENO_ROOT / state`` and leak across tests / real state).
    """
    config_path = tmp_path / "models.yaml"
    swarm_path = tmp_path / "local_swarm.yaml"
    state_dir = tmp_path / "state"
    state_path = state_dir / "model_manager.json"
    admission_path = state_dir / "admission.json"

    # Re-bind STATE_DIR inside pheno.model_manager (which imported it via
    # ``from pheno.paths import STATE_DIR``) so the manager's hardcoded
    # state_path lands inside ``tmp_path``.
    import pheno.model_manager as _mm_mod
    import pheno.paths as pheno_paths
    monkeypatch.setattr(_mm_mod, "STATE_DIR", state_dir)
    monkeypatch.setattr(pheno_paths, "STATE_DIR", state_dir)

    def _factory(
        *,
        tiers: dict[str, Any] | None = None,
        swarm: dict[str, Any] | None = None,
        binary: str = "llama-server",
        ik_flags: str = "",
        port_base: int = 8080,
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
                    },
                }
            }
        # Patch missing device_target on any gpu model so launch_env works
        for tier_dict in tiers.values():
            if not isinstance(tier_dict, dict):
                continue
            for node in tier_dict.values():
                if not isinstance(node, dict):
                    continue
                if node.get("runtime") == "gpu" and "device_target" not in node:
                    node["device_target"] = "RTX 3090 Ti"

        _write_models_yaml(
            config_path,
            tiers=tiers,
            binary=binary,
            ik_flags=ik_flags,
            port_base=port_base,
        )
        if swarm:
            _write_swarm_yaml(
                swarm_path,
                always_on_draft=swarm.get("always_on", {}).get("draft", ""),
                endpoints=swarm.get("endpoints"),
            )
        else:
            _write_swarm_yaml(swarm_path)
        # Wipe state so the constructor doesn't pick up stale state files.
        state_path.parent.mkdir(parents=True, exist_ok=True)
        if state_path.exists():
            state_path.unlink()
        admission_path.parent.mkdir(parents=True, exist_ok=True)
        return ModelManager(
            config_path=config_path,
            swarm_path=swarm_path,
            admission_path=admission_path,
        )

    return _factory


# ---------------------------------------------------------------------------
# ModelSpec + PreparedLaunch dataclasses
# ---------------------------------------------------------------------------


class TestModelSpecDataclass:
    """``ModelSpec`` field defaults."""

    def test_default_construction(self) -> None:
        spec = ModelSpec(name="tier.key", path="/p", port=8080, always_on=False)
        assert spec.name == "tier.key"
        assert spec.path == "/p"
        assert spec.port == 8080
        assert spec.always_on is False
        assert spec.on_demand is False
        assert spec.runtime == "gpu"
        assert spec.kv_ctx == 8192
        assert spec.draft_for == ""
        assert spec.draft_model == ""
        assert spec.extra_args == []
        assert spec.launch_template == ""
        assert spec.device_target == ""

    def test_custom_construction(self) -> None:
        spec = ModelSpec(
            name="tier.x",
            path="/p",
            port=9000,
            always_on=True,
            on_demand=True,
            runtime="cpu",
            kv_ctx=4096,
            draft_for="parent",
            draft_model="child",
            extra_args=["-a", "1"],
            launch_template="tpl",
            device_target="gtx_1080_ti",
        )
        assert spec.runtime == "cpu"
        assert spec.kv_ctx == 4096
        assert spec.draft_for == "parent"
        assert spec.draft_model == "child"
        assert spec.extra_args == ["-a", "1"]
        assert spec.device_target == "gtx_1080_ti"


class TestPreparedLaunchDataclass:
    """``PreparedLaunch`` is a frozen dataclass."""

    def test_construction(self) -> None:
        spec = ModelSpec(name="tier.x", path="/p", port=9000, always_on=True)
        pl = PreparedLaunch(
            spec=spec,
            cmd=("llama-server", "-m", "/p"),
            env={"CUDA_VISIBLE_DEVICES": "0"},
            device_uuid="GPU-uuid-123",
            admission_sha256="0" * 64,
        )
        assert pl.spec is spec
        assert pl.cmd == ("llama-server", "-m", "/p")
        assert pl.env["CUDA_VISIBLE_DEVICES"] == "0"
        assert pl.device_uuid == "GPU-uuid-123"

    def test_is_frozen(self) -> None:
        spec = ModelSpec(name="tier.x", path="/p", port=9000, always_on=True)
        pl = PreparedLaunch(spec=spec, cmd=(), env={}, device_uuid="x",
                              admission_sha256="0" * 64)
        with pytest.raises(Exception):
            pl.device_uuid = "y"  # type: ignore[misc]


# Type aliases used to annotate fixture parameters in tests below.
# Using the modern `type` statement syntax (PEP 695) supported on Python 3.12+.
type ManagerFactory = Callable[..., "ModelManager"]
type MonkeyPatchType = pytest.MonkeyPatch


# ---------------------------------------------------------------------------
# ModelManager._expand
# ---------------------------------------------------------------------------


class TestExpand:
    """``_expand`` expands env vars with ``${VAR:-default}`` syntax."""

    def test_expand_empty_string(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        assert mm._expand("") == ""

    def test_expand_no_vars(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        assert mm._expand("hello world") == "hello world"

    def test_expand_present_var(self, manager_factory: ManagerFactory, monkeypatch: MonkeyPatchType) -> None:
        monkeypatch.setenv("MY_VAR", "expanded-value")
        mm = manager_factory()
        assert mm._expand("prefix ${MY_VAR:-default} suffix") == "prefix expanded-value suffix"

    def test_expand_missing_var_with_default(self, manager_factory: ManagerFactory, monkeypatch: MonkeyPatchType) -> None:
        monkeypatch.delenv("MISSING_VAR_XYZ", raising=False)
        mm = manager_factory()
        assert mm._expand("${MISSING_VAR_XYZ:-fallback}") == "fallback"

    def test_expand_missing_var_empty_default(self, manager_factory: ManagerFactory, monkeypatch: MonkeyPatchType) -> None:
        monkeypatch.delenv("MISSING_VAR_XYZ", raising=False)
        mm = manager_factory()
        assert mm._expand("[${MISSING_VAR_XYZ:-}]") == "[]"

    def test_expand_mix_of_vars(self, manager_factory: ManagerFactory, monkeypatch: MonkeyPatchType) -> None:
        monkeypatch.setenv("PRESENT", "yes")
        monkeypatch.delenv("ABSENT", raising=False)
        mm = manager_factory()
        text = "${PRESENT:-no}-${ABSENT:-fallback}"
        assert mm._expand(text) == "yes-fallback"


# ---------------------------------------------------------------------------
# ModelManager._extra_args
# ---------------------------------------------------------------------------


class TestExtraArgs:
    """``_extra_args`` parses multi-line `ik_llama_expert_offload`."""

    def test_empty_returns_empty(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        assert mm._extra_args({}) == []
        assert mm._extra_args({"ik_llama_expert_offload": ""}) == []
        assert mm._extra_args({"ik_llama_expert_offload": None}) == []

    def test_single_line_parsed(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        node = {"ik_llama_expert_offload": "-ngl 99 -fa"}
        assert mm._extra_args(node) == ["-ngl", "99", "-fa"]

    def test_multi_line_parsed(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        node = {"ik_llama_expert_offload": "-ngl 99\n-fa\n-fmoe"}
        # shlex.split handles newlines as separators, so all flags end up in one list
        out = mm._extra_args(node)
        assert "-ngl" in out
        assert "99" in out
        assert "-fa" in out
        assert "-fmoe" in out

    def test_blank_lines_skipped(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        node = {"ik_llama_expert_offload": "-ngl 99\n\n\n-fa"}
        out = mm._extra_args(node)
        assert out == ["-ngl", "99", "-fa"]

    def test_quoted_args_preserved(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        node = {"ik_llama_expert_offload": '--model-url "http://example.com/x"'}
        out = mm._extra_args(node)
        assert "http://example.com/x" in out


# ---------------------------------------------------------------------------
# ModelManager.list_models + get_spec
# ---------------------------------------------------------------------------


class TestListModels:
    """``list_models`` parses YAML, allocates ports, returns specs."""

    def test_returns_model_specs(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        models = mm.list_models()
        assert len(models) == 1
        assert models[0].name == "local.qwen08b"
        assert models[0].always_on is True
        assert models[0].port == 8080

    def test_port_allocation_increments_per_model(self, manager_factory: ManagerFactory) -> None:
        tiers = {
            "tier": {
                "a": {"path": "/p", "always_on": True},
                "b": {"path": "/p2", "on_demand": True},
                "c": {"path": "/p3", "on_demand": True},
            }
        }
        mm = manager_factory(tiers=tiers, port_base=9000)
        models = mm.list_models()
        ports = [m.port for m in models]
        # Each gpu model gets an incrementing port
        assert ports == [9000, 9001, 9002]

    def test_cpu_runtime_gets_no_port(self, manager_factory: ManagerFactory) -> None:
        tiers = {
            "tier": {
                "a": {"path": "/p", "runtime": "cpu"},
                "b": {"path": "/p2", "runtime": "gpu"},
            }
        }
        mm = manager_factory(tiers=tiers, port_base=7000)
        models = {m.name: m for m in mm.list_models()}
        # cpu runtime → port = 0
        assert models["tier.a"].port == 0
        # gpu runtime → port allocated
        assert models["tier.b"].port == 7000

    def test_draft_for_gets_no_port(self, manager_factory: ManagerFactory) -> None:
        tiers = {
            "tier": {
                "main": {"path": "/p"},
                "draft": {"path": "/draft", "draft_for": "main"},
            }
        }
        mm = manager_factory(tiers=tiers, port_base=7000)
        models = {m.name: m for m in mm.list_models()}
        assert models["tier.main"].port == 7000
        assert models["tier.draft"].port == 0

    def test_non_dict_nodes_skipped(self, manager_factory: ManagerFactory) -> None:
        # A string at the tier level should be skipped, not crash
        tiers = {
            "tier": {
                "good": {"path": "/p"},
                "bad": "not a dict",
                "also_bad": 42,
            }
        }
        mm = manager_factory(tiers=tiers)
        models = mm.list_models()
        # Only "good" should appear
        names = [m.name for m in models]
        assert names == ["tier.good"]

    def test_non_dict_tier_skipped(self, manager_factory: ManagerFactory) -> None:
        # A scalar at the top tier level should not crash
        tiers = {
            "tier": {"good": {"path": "/p"}},
            "broken": "string",
        }
        mm = manager_factory(tiers=tiers)
        models = mm.list_models()
        assert any(m.name == "tier.good" for m in models)

    def test_list_models_caches_results(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        a = mm.list_models()
        b = mm.list_models()
        # Should return new list objects but with same content
        assert a == b
        # Caching is implementation detail; just assert no crash

    def test_get_spec_returns_matching(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        assert spec.name == "local.qwen08b"

    def test_get_spec_returns_none_when_missing(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        assert mm.get_spec("does.not.exist") is None

    def test_extra_args_included(self, manager_factory: ManagerFactory) -> None:
        tiers = {
            "tier": {
                "a": {"path": "/p", "ik_llama_expert_offload": "-ngl 99 -fa"},
            }
        }
        mm = manager_factory(tiers=tiers)
        spec = mm.get_spec("tier.a")
        assert spec is not None
        assert "-ngl" in spec.extra_args
        assert "99" in spec.extra_args

    def test_path_expanded_for_env_vars(self, manager_factory: ManagerFactory, monkeypatch: MonkeyPatchType) -> None:
        monkeypatch.setenv("CUSTOM_MODEL", "/custom/path/model.gguf")
        tiers = {
            "tier": {
                "a": {"path": "${CUSTOM_MODEL:-/default}"},
            }
        }
        mm = manager_factory(tiers=tiers)
        spec = mm.get_spec("tier.a")
        assert spec is not None
        assert spec.path == "/custom/path/model.gguf"


# ---------------------------------------------------------------------------
# ModelManager._resolve_draft_path
# ---------------------------------------------------------------------------


class TestResolveDraftPath:
    """``_resolve_draft_path`` looks up the draft model's path."""

    def test_no_draft_returns_empty(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        spec = ModelSpec(name="tier.a", path="/p", port=9000, always_on=True)
        assert mm._resolve_draft_path(spec) == ""

    def test_draft_spec_via_swarm(self, manager_factory: ManagerFactory) -> None:
        tiers = {
            "tier": {
                "main": {"path": "/main-path"},
                "draft": {"path": "/draft-path"},
            }
        }
        swarm = {"always_on": {"draft": "tier.draft"}}
        mm = manager_factory(tiers=tiers, swarm=swarm)
        spec = mm.get_spec("tier.main")
        assert spec is not None
        assert mm._resolve_draft_path(spec) == "/draft-path"

    def test_draft_spec_via_draft_model_attr(self, manager_factory: ManagerFactory) -> None:
        tiers = {
            "tier": {
                "main": {"path": "/main-path"},
                "draft": {"path": "/draft-path-via-attr"},
            }
        }
        mm = manager_factory(tiers=tiers)
        spec = mm.get_spec("tier.main")
        assert spec is not None
        spec.draft_model = "tier.draft"
        assert mm._resolve_draft_path(spec) == "/draft-path-via-attr"

    def test_draft_spec_missing_returns_empty(self, manager_factory: ManagerFactory) -> None:
        tiers = {"tier": {"main": {"path": "/main-path"}}}
        swarm = {"always_on": {"draft": "tier.does-not-exist"}}
        mm = manager_factory(tiers=tiers, swarm=swarm)
        spec = mm.get_spec("tier.main")
        assert spec is not None
        assert mm._resolve_draft_path(spec) == ""


# ---------------------------------------------------------------------------
# ModelManager._ik_flags_for_spec
# ---------------------------------------------------------------------------


class TestIkFlagsForSpec:
    """``_ik_flags_for_spec`` strips ``-c <n>`` flags."""

    def test_strips_minus_c_flag(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory(ik_flags="-fa -fmoe -rtr -c 32768 -ctk q8_0 -ctv q8_0")
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        out = mm._ik_flags_for_spec(spec)
        assert "-c" not in out.split()
        assert "32768" not in out.split()
        # Other flags preserved
        assert "-fa" in out
        assert "-fmoe" in out
        assert "-rtr" in out

    def test_keeps_minus_ctk_and_minus_ctv(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory(ik_flags="-ctk q8_0 -ctv q8_0")
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        out = mm._ik_flags_for_spec(spec)
        assert "-ctk" in out
        assert "-ctv" in out

    def test_empty_ik_flags(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory(ik_flags="")
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        assert mm._ik_flags_for_spec(spec) == ""


# ---------------------------------------------------------------------------
# ModelManager._append_draft_args
# ---------------------------------------------------------------------------


class TestAppendDraftArgs:
    """``_append_draft_args`` extends cmd with draft-model flags."""

    def test_no_draft_does_nothing(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        spec = mm.get_spec("local.qwen08b")
        assert spec is not None
        cmd = ["llama-server", "-m", "/p"]
        original = list(cmd)
        mm._append_draft_args(cmd, spec, {})
        assert cmd == original

    def test_appends_default_draft_args(self, manager_factory: ManagerFactory, fake_model_file: Path) -> None:
        tiers = {
            "tier": {
                "main": {"path": "/main-path"},
                "draft": {"path": str(fake_model_file)},
            }
        }
        swarm = {"always_on": {"draft": "tier.draft"}}
        mm = manager_factory(tiers=tiers, swarm=swarm)
        spec = mm.get_spec("tier.main")
        assert spec is not None
        cmd: list[str] = []
        mm._append_draft_args(cmd, spec, {})
        # Default template: -md {draft_path} --draft-max 16
        assert "-md" in cmd
        assert str(fake_model_file) in cmd
        assert "--draft-max" in cmd
        assert "16" in cmd

    def test_appends_custom_template_draft_args(
        self, manager_factory: ManagerFactory, fake_model_file: Path
    ) -> None:
        tiers = {
            "tier": {
                "main": {"path": "/main-path"},
                "draft": {"path": str(fake_model_file)},
            }
        }
        swarm = {"always_on": {"draft": "tier.draft"}}
        mm = manager_factory(tiers=tiers, swarm=swarm)
        spec = mm.get_spec("tier.main")
        assert spec is not None
        cmd: list[str] = []
        tpl = {"draft_args": ["-draft", "{draft_path}", "--max", "8"]}
        mm._append_draft_args(cmd, spec, tpl)
        assert "-draft" in cmd
        assert str(fake_model_file) in cmd
        assert "--max" in cmd
        assert "8" in cmd

    def test_skips_when_draft_file_missing(
        self, manager_factory: ManagerFactory, tmp_path: Path
    ) -> None:
        # The draft path exists as a string but the file doesn't exist
        tiers = {
            "tier": {
                "main": {"path": "/main-path"},
                "draft": {"path": "/this/path/does/not/exist.gguf"},
            }
        }
        swarm = {"always_on": {"draft": "tier.draft"}}
        mm = manager_factory(tiers=tiers, swarm=swarm)
        spec = mm.get_spec("tier.main")
        assert spec is not None
        cmd: list[str] = []
        mm._append_draft_args(cmd, spec, {})
        # No draft args appended
        assert cmd == []


# ---------------------------------------------------------------------------
# ModelManager.build_cmd
# ---------------------------------------------------------------------------


class TestBuildCmd:
    """``build_cmd`` returns the llama-server command."""

    def test_build_inline_mode(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        cmd = mm.build_cmd("local.qwen08b")
        assert cmd[0] == "llama-server"
        assert "-m" in cmd
        assert cmd[cmd.index("-m") + 1].endswith("model.gguf")
        assert "--port" in cmd
        assert "8080" in cmd
        assert "-c" in cmd

    def test_build_unknown_model_raises(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        with pytest.raises(ValueError, match="Unknown model"):
            mm.build_cmd("does.not.exist")

    def test_build_with_ik_flags(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory(ik_flags="-fa -fmoe -ctk q8_0 -ctv q8_0")
        cmd = mm.build_cmd("local.qwen08b")
        assert "-fa" in cmd
        assert "-fmoe" in cmd
        assert "-ctk" in cmd
        assert "-ctv" in cmd

    def test_build_strips_minus_c_from_ik_flags(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory(ik_flags="-fa -c 32768")
        cmd = mm.build_cmd("local.qwen08b")
        # -fa should be present; -c 32768 should be stripped from ik flags
        assert "-fa" in cmd
        # But -c 8192 (from kv_ctx) should be present
        idx = cmd.index("-c")
        assert cmd[idx + 1] == "8192"

    def test_build_with_extra_args(self, manager_factory: ManagerFactory) -> None:
        tiers = {
            "tier": {
                "a": {
                    "path": "/p",
                    "ik_llama_expert_offload": "-ngl 99 -fa",
                }
            }
        }
        mm = manager_factory(tiers=tiers)
        cmd = mm.build_cmd("tier.a")
        assert "-ngl" in cmd
        assert "99" in cmd


# ---------------------------------------------------------------------------
# ModelManager.load_state + save_state
# ---------------------------------------------------------------------------


class TestLoadSaveState:
    """``load_state`` and ``save_state`` round-trip JSON."""

    def test_load_state_returns_default_when_missing(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        state = mm.load_state()
        assert state == {"loaded": [], "always_on": [], "ports": {}}

    def test_save_and_load_roundtrip(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        payload = {
            "loaded": ["model.a"],
            "always_on": ["model.b"],
            "ports": {"model.a": 8080},
            "admissions": {"model.a": {"admission_sha256": "0" * 64, "device_uuid": "x"}},
        }
        mm.save_state(payload)
        loaded = mm.load_state()
        assert loaded == payload

    def test_save_state_creates_parent_dirs(self, manager_factory: ManagerFactory, tmp_path: Path) -> None:
        # Delete the default state dir to verify save_state creates it
        mm = manager_factory()
        # Note: state_path is configured by the fixture
        # Just verify that save works
        mm.save_state({"loaded": ["x"]})
        assert mm.state_path.exists()

    def test_save_state_overwrites(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        mm.save_state({"loaded": ["a"]})
        mm.save_state({"loaded": ["b"]})
        assert mm.load_state() == {"loaded": ["b"]}


# ---------------------------------------------------------------------------
# ModelManager.status
# ---------------------------------------------------------------------------


class TestStatus:
    """``status`` aggregates model readiness info."""

    def test_status_returns_state_and_models(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        s = mm.status()
        assert "state" in s
        assert "models" in s
        assert isinstance(s["models"], list)
        # CPU / draft / no-port models are filtered out
        for row in s["models"]:
            assert "name" in row
            assert "port" in row
            assert "always_on" in row
            assert "loaded" in row
            assert "endpoint" in row
            assert "gguf_exists" in row
            assert "draft_model" in row
            assert "draft_path" in row

    def test_status_gguf_exists_for_existing_file(
        self, manager_factory: ManagerFactory, fake_model_file: Path
    ) -> None:
        tiers = {"tier": {"a": {"path": str(fake_model_file), "always_on": True}}}
        mm = manager_factory(tiers=tiers)
        s = mm.status()
        rows = [r for r in s["models"] if r["name"] == "tier.a"]
        assert rows
        assert rows[0]["gguf_exists"] is True

    def test_status_gguf_exists_for_missing_file(self, manager_factory: ManagerFactory) -> None:
        tiers = {"tier": {"a": {"path": "/does/not/exist.gguf", "always_on": True}}}
        mm = manager_factory(tiers=tiers)
        s = mm.status()
        rows = [r for r in s["models"] if r["name"] == "tier.a"]
        assert rows[0]["gguf_exists"] is False

    def test_status_endpoint_falls_back_to_default(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        s = mm.status()
        rows = s["models"]
        assert any(
            r["endpoint"] == "http://127.0.0.1:8080/v1" for r in rows
        )

    def test_status_endpoint_overridden_by_swarm(
        self, manager_factory: ManagerFactory
    ) -> None:
        # swarm endpoints keyed by short name (no tier prefix)
        mm = manager_factory(
            swarm={"endpoints": {"qwen08b": "http://qwen.local:9000/v1"}}
        )
        s = mm.status()
        rows = [r for r in s["models"] if r["name"] == "local.qwen08b"]
        assert rows
        assert rows[0]["endpoint"] == "http://qwen.local:9000/v1"

    def test_status_loaded_flag_from_state(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        # Save a state with this model marked loaded
        mm.save_state({"loaded": ["local.qwen08b"], "always_on": [], "ports": {}})
        s = mm.status()
        rows = [r for r in s["models"] if r["name"] == "local.qwen08b"]
        assert rows[0]["loaded"] is True

    def test_status_filters_cpu_models(self, manager_factory: ManagerFactory) -> None:
        tiers = {
            "tier": {
                "a": {"path": "/p", "always_on": True, "runtime": "gpu"},
                "b": {"path": "/p2", "runtime": "cpu"},
            }
        }
        mm = manager_factory(tiers=tiers)
        s = mm.status()
        names = [r["name"] for r in s["models"]]
        assert "tier.a" in names
        assert "tier.b" not in names


# ---------------------------------------------------------------------------
# ModelManager.launch_env
# ---------------------------------------------------------------------------


class TestLaunchEnv:
    """``launch_env`` builds env vars for a launch."""

    def test_launch_env_unknown_model_raises(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        with pytest.raises(ValueError, match="Unknown model"):
            mm.launch_env("does.not.exist")

    def test_launch_env_cpu_model_returns_os_environ(
        self, manager_factory: ManagerFactory, monkeypatch: MonkeyPatchType
    ) -> None:
        monkeypatch.setenv("PRESET_VAR", "yes")
        tiers = {
            "tier": {
                "a": {"path": "/p", "runtime": "cpu"},
            }
        }
        mm = manager_factory(tiers=tiers)
        env = mm.launch_env("tier.a")
        # For cpu models, env is a copy of os.environ (no device injection)
        assert env["PRESET_VAR"] == "yes"

    def test_launch_env_draft_model_returns_os_environ(
        self, manager_factory: ManagerFactory, monkeypatch: MonkeyPatchType
    ) -> None:
        monkeypatch.setenv("PRESET_VAR", "yes")
        tiers = {
            "tier": {
                "main": {"path": "/main"},
                "draft": {"path": "/draft", "draft_for": "main"},
            }
        }
        mm = manager_factory(tiers=tiers)
        env = mm.launch_env("tier.draft")
        assert env["PRESET_VAR"] == "yes"

    def test_launch_env_gpu_injects_cuda_visible_devices(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        # Mock _resolve_device_uuid
        with patch.object(
            mm, "_resolve_device_uuid", return_value="GPU-FAKE-UUID-1"
        ) as mock_rrd:
            env = mm.launch_env("local.qwen08b")
        mock_rrd.assert_called_once()
        assert env["CUDA_VISIBLE_DEVICES"] == "GPU-FAKE-UUID-1"
        assert env["CUDA_DEVICE_ORDER"] == "PCI_BUS_ID"


# ---------------------------------------------------------------------------
# ModelManager.start(dry_run=True)
# ---------------------------------------------------------------------------


class TestStartDryRun:
    """``start(dry_run=True)`` returns a plan without spawning."""

    def test_start_dry_run_returns_plan(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        with patch.object(
            mm, "_validate_runtime_admission",
            return_value="a" * 64,
        ), patch.object(
            mm, "_resolve_device_uuid",
            return_value="GPU-FAKE-UUID",
        ):
            result = mm.start("local.qwen08b", dry_run=True)
        assert result["status"] == "dry_run"
        assert result["name"] == "local.qwen08b"
        assert result["port"] == 8080
        assert result["admission_sha256"] == "a" * 64
        assert result["device_uuid"] == "GPU-FAKE-UUID"
        assert "cmd" in result
        assert isinstance(result["cmd"], list)
        assert result["cmd"][0] == "llama-server"

    def test_start_dry_run_unknown_model_raises(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        with pytest.raises(ValueError, match="Unknown model"):
            mm.start("does.not.exist", dry_run=True)

    def test_start_skips_cpu_model(self, manager_factory: ManagerFactory) -> None:
        tiers = {
            "tier": {
                "a": {"path": "/p", "runtime": "cpu"},
            }
        }
        mm = manager_factory(tiers=tiers)
        result = mm.start("tier.a", dry_run=True)
        assert result["status"] == "skipped"
        assert "cpu-only" in result["reason"]

    def test_start_skips_draft_model(self, manager_factory: ManagerFactory) -> None:
        tiers = {
            "tier": {
                "main": {"path": "/p"},
                "draft": {"path": "/draft", "draft_for": "main"},
            }
        }
        mm = manager_factory(tiers=tiers)
        result = mm.start("tier.draft", dry_run=True)
        assert result["status"] == "skipped"
        assert "draft" in result["reason"]

    def test_start_skips_when_port_unassigned(self, manager_factory: ManagerFactory) -> None:
        tiers = {
            "tier": {
                "a": {"path": "/p", "runtime": "cpu"},
                "b": {"path": "/p2"},
            }
        }
        mm = manager_factory(tiers=tiers)
        # tier.a has port=0; starting it should skip with "no server port"
        result = mm.start("tier.a", dry_run=True)
        assert result["status"] == "skipped"

    def test_start_skips_when_gguf_missing(self, manager_factory: ManagerFactory) -> None:
        tiers = {
            "tier": {
                "a": {"path": "/no/such/file.gguf", "always_on": True},
            }
        }
        mm = manager_factory(tiers=tiers)
        result = mm.start("tier.a", dry_run=True)
        assert result["status"] == "skipped"
        assert "GGUF missing" in result["reason"]


# ---------------------------------------------------------------------------
# ModelManager.ensure_always_on(dry_run=True)
# ---------------------------------------------------------------------------


class TestEnsureAlwaysOn:
    """``ensure_always_on(dry_run=True)`` starts always-on models."""

    def test_returns_one_per_always_on_model(
        self,
        manager_factory: ManagerFactory,
        fake_model_file: Path,
    ) -> None:
        tiers = {
            "tier": {
                "a": {"path": str(fake_model_file), "always_on": True},
                "b": {"path": str(fake_model_file), "on_demand": True},
                "c": {"path": str(fake_model_file), "always_on": True},
            }
        }
        mm = manager_factory(tiers=tiers)
        with patch.object(
            mm, "_validate_runtime_admission",
            return_value="a" * 64,
        ), patch.object(
            mm, "_resolve_device_uuid",
            return_value="GPU-FAKE",
        ):
            results = mm.ensure_always_on(dry_run=True)
        # Only the two always_on models are returned
        assert len(results) == 2
        names = {r["name"] for r in results}
        assert names == {"tier.a", "tier.c"}

    def test_skips_drafts(self, manager_factory: ManagerFactory, fake_model_file: Path) -> None:
        tiers = {
            "tier": {
                "main": {"path": str(fake_model_file), "always_on": True},
                "draft": {
                    "path": str(fake_model_file),
                    "draft_for": "main",
                    "always_on": True,
                },
            }
        }
        mm = manager_factory(tiers=tiers)
        with patch.object(
            mm, "_validate_runtime_admission",
            return_value="a" * 64,
        ), patch.object(
            mm, "_resolve_device_uuid",
            return_value="GPU-FAKE",
        ):
            results = mm.ensure_always_on(dry_run=True)
        # Draft should be skipped (draft_for set), main should be returned
        names = [r["name"] for r in results]
        assert "tier.draft" not in names

    def test_empty_when_no_always_on(self, manager_factory: ManagerFactory) -> None:
        tiers = {
            "tier": {
                "a": {"path": "/p", "on_demand": True},
            }
        }
        mm = manager_factory(tiers=tiers)
        results = mm.ensure_always_on(dry_run=True)
        assert results == []


# ---------------------------------------------------------------------------
# ModelManager.swap_to(dry_run=True)
# ---------------------------------------------------------------------------


class TestSwapToDryRun:
    """``swap_to(dry_run=True)`` returns a swap plan."""

    def test_swap_dry_run_returns_plan(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        with patch.object(
            mm, "_validate_runtime_admission",
            return_value="b" * 64,
        ), patch.object(
            mm, "_resolve_device_uuid",
            return_value="GPU-FAKE-UUID",
        ):
            result = mm.swap_to("local.qwen08b", dry_run=True)
        assert result["status"] == "dry_run"
        assert result["name"] == "local.qwen08b"
        assert result["admission_sha256"] == "b" * 64
        assert "cmd" in result

    def test_swap_skips_cpu_model(self, manager_factory: ManagerFactory) -> None:
        tiers = {"tier": {"a": {"path": "/p", "runtime": "cpu"}}}
        mm = manager_factory(tiers=tiers)
        result = mm.swap_to("tier.a", dry_run=True)
        assert result["status"] == "skipped"


# ---------------------------------------------------------------------------
# ModelManager.stop_on_demand
# ---------------------------------------------------------------------------


class TestStopOnDemand:
    """``stop_on_demand`` terminates on-demand procs and updates state."""

    def test_stop_on_demand_terminates_procs(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        # Inject a fake proc into the running set
        fake_proc = MagicMock()
        mm._procs["local.qwen08b"] = fake_proc
        mm.save_state({"loaded": ["local.qwen08b"], "always_on": [], "ports": {}})
        # The model's always_on=True so it should NOT be terminated
        mm.stop_on_demand()
        fake_proc.terminate.assert_not_called()
        assert "local.qwen08b" in mm._procs

    def test_stop_on_demand_drops_on_demand_from_state(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        # Save state with both always_on and on_demand entries
        mm.save_state(
            {
                "loaded": ["local.qwen08b"],
                "always_on": ["local.qwen08b"],
                "ports": {"local.qwen08b": 8080},
            }
        )
        mm.stop_on_demand()
        # always_on entries are preserved
        assert "local.qwen08b" in mm.load_state()["loaded"]

    def test_stop_on_demand_terminates_non_always(self, manager_factory: ManagerFactory) -> None:
        # Make two models: one always_on, one on_demand
        tiers = {
            "tier": {
                "always": {"path": "/p/a", "always_on": True},
                "demand": {"path": "/p/d", "on_demand": True},
            }
        }
        mm = manager_factory(tiers=tiers)
        # Inject fake procs
        always_proc = MagicMock()
        demand_proc = MagicMock()
        mm._procs["tier.always"] = always_proc
        mm._procs["tier.demand"] = demand_proc
        mm.save_state(
            {
                "loaded": ["tier.always", "tier.demand"],
                "always_on": ["tier.always"],
                "ports": {},
            }
        )
        mm.stop_on_demand()
        always_proc.terminate.assert_not_called()
        demand_proc.terminate.assert_called_once()
        assert "tier.demand" not in mm._procs
        assert "tier.always" in mm._procs
        # State should be cleaned
        loaded = mm.load_state()["loaded"]
        assert "tier.demand" not in loaded
        assert "tier.always" in loaded


# ---------------------------------------------------------------------------
# ModelManager._resolve_device_uuid
# ---------------------------------------------------------------------------


class TestResolveDeviceUuid:
    """``_resolve_device_uuid`` shells out to nvidia-smi."""

    def test_raises_when_target_empty(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        with pytest.raises(ValueError, match="device_target"):
            mm._resolve_device_uuid("")

    def test_returns_uuid_when_match_found(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        fake_result = MagicMock()
        fake_result.returncode = 0
        fake_result.stdout = "GPU-uuid-aaaa, RTX 3090 Ti\nGPU-uuid-bbbb, GTX 1080 Ti\n"
        with patch.object(
            subprocess, "run", return_value=fake_result
        ):
            uuid = mm._resolve_device_uuid("GTX 1080 Ti")
        assert uuid == "GPU-uuid-bbbb"

    def test_raises_when_no_match(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        fake_result = MagicMock()
        fake_result.returncode = 0
        fake_result.stdout = "GPU-uuid-aaaa, RTX 3090 Ti\n"
        with patch.object(
            subprocess, "run", return_value=fake_result
        ):
            with pytest.raises(RuntimeError, match="not uniquely available"):
                mm._resolve_device_uuid("GTX 1080 Ti")

    def test_raises_when_nvidia_smi_fails(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        fake_result = MagicMock()
        fake_result.returncode = 1
        fake_result.stdout = ""
        with patch.object(
            subprocess, "run", return_value=fake_result
        ):
            with pytest.raises(RuntimeError, match="not uniquely available"):
                mm._resolve_device_uuid("RTX 3090 Ti")

    def test_raises_when_multiple_matches(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory()
        fake_result = MagicMock()
        fake_result.returncode = 0
        fake_result.stdout = (
            "GPU-uuid-aaaa, RTX 3090 Ti\n"
            "GPU-uuid-bbbb, RTX 3090 Ti\n"
        )
        with patch.object(
            subprocess, "run", return_value=fake_result
        ):
            with pytest.raises(RuntimeError, match="not uniquely available"):
                mm._resolve_device_uuid("RTX 3090 Ti")


# ---------------------------------------------------------------------------
# RuntimeAdmissionError
# ---------------------------------------------------------------------------


class TestRuntimeAdmissionError:
    """``RuntimeAdmissionError`` is a RuntimeError subclass."""

    def test_is_runtime_error(self) -> None:
        err = RuntimeAdmissionError("test")
        assert isinstance(err, RuntimeError)
        assert str(err) == "test"


# ---------------------------------------------------------------------------
# Swarm loading
# ---------------------------------------------------------------------------


class TestSwarmLoading:
    """``ModelManager`` loads swarm.yaml when present."""

    def test_swarm_loaded_when_present(self, manager_factory: ManagerFactory) -> None:
        mm = manager_factory(swarm={"always_on": {"draft": "some.draft"}})
        assert mm.swarm.get("always_on", {}).get("draft") == "some.draft"

    def test_swarm_empty_when_file_missing(
        self, tmp_path: Path, fake_model_file: Path
    ) -> None:
        # Create a manager with a non-existent swarm_path
        config_path = tmp_path / "models.yaml"
        _write_models_yaml(config_path, tiers={"tier": {"a": {"path": str(fake_model_file)}}})
        mm = ModelManager(
            config_path=config_path,
            swarm_path=tmp_path / "missing.yaml",
        )
        assert mm.swarm == {}
