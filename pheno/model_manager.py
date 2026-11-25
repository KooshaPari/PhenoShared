"""Single-GPU model manager - always-on Qwen4B + 0.6B draft + on-demand swap."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess  # nosec B404
import time
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

from pheno.paths import CONFIG_DIR, STATE_DIR
from pheno.runtime_admission import validate_runtime_admission


class RuntimeAdmissionError(RuntimeError):
    """A launch was denied before any process or state mutation."""


@dataclass(frozen=True)
class PreparedLaunch:
    spec: ModelSpec
    cmd: tuple[str, ...]
    env: dict[str, str]
    device_uuid: str
    admission_sha256: str


@dataclass
class ModelSpec:
    name: str
    path: str
    port: int
    always_on: bool
    on_demand: bool = False
    runtime: str = "gpu"
    kv_ctx: int = 8192
    draft_for: str = ""
    draft_model: str = ""
    extra_args: list[str] = field(default_factory=list)
    launch_template: str = ""
    device_target: str = ""


class ModelManager:
    def __init__(
        self,
        config_path: Path | None = None,
        swarm_path: Path | None = None,
        *,
        admission_path: Path | None = None,
    ):
        self.config_path = config_path or CONFIG_DIR / "models.yaml"
        self.swarm_path = swarm_path or CONFIG_DIR / "local_swarm.yaml"
        self.state_path = STATE_DIR / "model_manager.json"
        self.raw = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
        self.swarm = (
            yaml.safe_load(self.swarm_path.read_text(encoding="utf-8"))
            if self.swarm_path.exists()
            else {}
        )
        self.swarm = self.swarm or {}
        self.binary = self._expand(
            self.raw.get("llama_server", {}).get("binary", "llama-server")
        )
        self.ik_flags = self.raw.get("llama_server", {}).get("ik_llama_flags", "")
        self.port_base = int(self.raw.get("llama_server", {}).get("port_base", 8080))
        self._procs: dict[str, subprocess.Popen[Any]] = {}
        self._spec_index: dict[str, ModelSpec] = {}
        self.admission_path = (
            admission_path or STATE_DIR / "runtime_admission_2026-07-19.json"
        )

    def _expand(self, s: str) -> str:
        if not s:
            return ""

        def _repl(match: re.Match[str]) -> str:
            return os.environ.get(match.group(1), match.group(2))

        return os.path.expandvars(re.sub(r"\$\{([^:}]+):-([^}]*)\}", _repl, s))

    def _extra_args(self, node: dict[str, Any]) -> list[str]:
        extra: list[str] = []
        for line in str(node.get("ik_llama_expert_offload") or "").strip().splitlines():
            if line.strip():
                extra.extend(shlex.split(line))
        return extra

    def _launch_template(self, spec: ModelSpec) -> dict[str, Any]:
        path = (
            CONFIG_DIR
            / "launch"
            / f"{spec.launch_template or spec.name.split('.', 1)[-1]}.yaml"
        )
        return (
            yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if path.exists()
            else {}
        )

    def list_models(self) -> list[ModelSpec]:
        if self._spec_index:
            return list(self._spec_index.values())
        specs: list[ModelSpec] = []
        port = self.port_base
        for tier_name, tier in (self.raw.get("tiers", {}) or {}).items():
            if not isinstance(tier, dict):
                continue
            for key, node in tier.items():
                if not isinstance(node, dict) or "path" not in node:
                    continue
                name = f"{tier_name}.{key}"
                runtime = str(node.get("runtime", "gpu"))
                draft_for = str(node.get("draft_for", ""))
                assign_port = runtime != "cpu" and not draft_for
                spec_port = port if assign_port else 0
                if assign_port:
                    port += 1
                specs.append(
                    ModelSpec(
                        name,
                        self._expand(node.get("path", "")),
                        spec_port,
                        bool(node.get("always_on")),
                        bool(node.get("on_demand")),
                        runtime,
                        int(node.get("kv_ctx", 8192)),
                        draft_for,
                        str(node.get("draft_model", "")),
                        self._extra_args(node),
                        str(node.get("launch_template", key)),
                        str(node.get("device_target", "")),
                    )
                )
        self._spec_index = {s.name: s for s in specs}
        return specs

    def get_spec(self, name: str) -> ModelSpec | None:
        return next((s for s in self.list_models() if s.name == name), None)

    def _resolve_draft_path(self, spec: ModelSpec) -> str:
        draft_name = spec.draft_model or self.swarm.get("always_on", {}).get(
            "draft", ""
        )
        draft = self.get_spec(draft_name) if draft_name else None
        return draft.path if draft else ""

    def _ik_flags_for_spec(self, spec: ModelSpec) -> str:
        return re.sub(r"-c\s+\d+", "", self.ik_flags or "").strip()

    def _append_draft_args(
        self, cmd: list[str], spec: ModelSpec, tpl: dict[str, Any]
    ) -> None:
        path = self._resolve_draft_path(spec)
        if not path or not Path(path).exists():
            return
        for part in tpl.get("draft_args") or [
            "-md",
            "{draft_path}",
            "--draft-max",
            "16",
        ]:
            cmd.extend(str(part).format(draft_path=path).split())

    def build_cmd(self, name: str) -> list[str]:
        spec = self.get_spec(name)
        if not spec:
            raise ValueError(f"Unknown model {name}")
        tpl = self._launch_template(spec)
        args_tpl = tpl.get("args") or []
        if args_tpl:
            subs = {
                "binary": self.binary,
                "path": spec.path,
                "port": str(spec.port),
                "kv_ctx": str(spec.kv_ctx),
                "ik_flags": self._ik_flags_for_spec(spec),
                "draft_path": self._resolve_draft_path(spec),
            }
            cmd: list[str] = []
            for part in args_tpl:
                cmd.extend(str(part).format(**subs).split())
            cmd.extend(spec.extra_args)
            self._append_draft_args(cmd, spec, tpl)
            return [c for c in cmd if c]
        cmd = [
            self.binary,
            "-m",
            spec.path,
            "--port",
            str(spec.port),
            "-c",
            str(spec.kv_ctx),
        ]
        if self._ik_flags_for_spec(spec):
            cmd.extend(self._ik_flags_for_spec(spec).split())
        cmd.extend(spec.extra_args)
        self._append_draft_args(cmd, spec, tpl)
        return cmd

    def load_state(self) -> dict[str, Any]:
        return (
            json.loads(self.state_path.read_text(encoding="utf-8"))
            if self.state_path.exists()
            else {"loaded": [], "always_on": [], "ports": {}}
        )

    def _resolve_device_uuid(self, target: str) -> str:
        if not target:
            raise ValueError("GPU model is missing an explicit device_target")
        result = subprocess.run(  # nosec B603 B607
            ["nvidia-smi", "--query-gpu=uuid,name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            check=False,
        )
        matches = []
        for line in result.stdout.splitlines():
            uuid, separator, name = line.partition(",")
            if separator and name.strip() == target:
                matches.append(uuid.strip())
        if result.returncode != 0 or len(matches) != 1:
            raise RuntimeError(
                f"device target {target!r} is not uniquely available via nvidia-smi"
            )
        return matches[0]

    def launch_env(self, name: str) -> dict[str, str]:
        spec = self.get_spec(name)
        if not spec:
            raise ValueError(f"Unknown model {name}")
        if spec.runtime == "cpu" or spec.draft_for:
            return os.environ.copy()
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = self._resolve_device_uuid(spec.device_target)
        env["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
        return env

    def save_state(self, state: dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _validate_runtime_admission(
        self, spec: ModelSpec, cmd: tuple[str, ...], device_uuid: str
    ) -> str:
        """Validate the exact current admission artifact; absence is never allow."""
        if not self.admission_path.is_file():
            raise RuntimeAdmissionError(
                "runtime admission evidence is missing or invalid"
            )
        tier, key = spec.name.split(".", 1)
        node = self.raw.get("tiers", {}).get(tier, {}).get(key, {}) or {}
        binding = node.get("runtime_admission")
        required = {
            "lane_id",
            "model_id",
            "candidate_id",
            "runtime_id",
            "device_id",
            "device_uuid",
            "cell_id",
            "artifact_sha256",
            "command_binary",
        }
        if (
            not isinstance(binding, dict)
            or set(binding) != required
            or any(
                not isinstance(binding[key], str) or not binding[key]
                for key in required
            )
        ):
            raise RuntimeAdmissionError(
                "model has no exact runtime admission semantic mapping"
            )
        try:
            value = validate_runtime_admission(
                json.loads(self.admission_path.read_text(encoding="utf-8")),
                root=CONFIG_DIR.parent,
            )
        except (OSError, ValueError, TypeError) as exc:
            raise RuntimeAdmissionError(
                "runtime admission evidence is missing or invalid"
            ) from exc
        lane_id = binding["lane_id"]
        lanes = [row for row in value.get("lanes", []) if row.get("lane_id") == lane_id]
        if len(lanes) != 1:
            raise RuntimeAdmissionError(
                "runtime admission lane is missing or non-unique"
            )
        lane = lanes[0]
        request = lane.get("request", {})
        expected_request = {
            key: binding[key]
            for key in ("candidate_id", "runtime_id", "device_id", "cell_id")
        }
        artifact = lane.get("artifact_binding", {}) or {}
        artifact_binding = artifact.get("binding", {}) or {}
        command_binary = Path(cmd[0]).name.lower() if cmd else ""
        configured_binary = Path(binding["command_binary"]).name.lower()
        try:
            artifact_sha256 = sha256(Path(spec.path).read_bytes()).hexdigest()
        except OSError as exc:
            raise RuntimeAdmissionError(
                "model artifact identity cannot be verified"
            ) from exc
        semantic_mismatch = (
            node.get("id") != binding["model_id"]
            or any(
                request.get(key) != expected
                for key, expected in expected_request.items()
            )
            or artifact.get("candidate_id") != binding["candidate_id"]
            or artifact.get("cell_id") != binding["cell_id"]
            or artifact.get("device_id") != binding["device_id"]
            or artifact.get("runtime") != binding["runtime_id"]
            or artifact_binding.get("content_sha256") != binding["artifact_sha256"]
            or artifact_sha256 != binding["artifact_sha256"]
            or device_uuid != binding["device_uuid"]
            or command_binary != configured_binary
        )
        lease = lane.get("endpoint_lease", {}) or {}
        if (
            lease.get("device_uuid") is not None
            and lease.get("device_uuid") != binding["device_uuid"]
        ):
            semantic_mismatch = True
        if (
            lease.get("artifact_sha256") is not None
            and lease.get("artifact_sha256") != binding["artifact_sha256"]
        ):
            semantic_mismatch = True
        runtime_binding = lane.get("runtime_binding", {}) or {}
        if runtime_binding.get("runtime") != binding["runtime_id"]:
            semantic_mismatch = True
        if semantic_mismatch:
            raise RuntimeAdmissionError("runtime admission semantic tuple mismatch")
        if (
            lane.get("decision") != "admitted"
            or lane.get("action_permitted") is not True
            or lane.get("authorization", {}).get("launch", {}).get("granted")
            is not True
        ):
            blockers = lane.get("blockers") or ["runtime_admission_denied"]
            raise RuntimeAdmissionError(
                f"runtime admission denied: {','.join(map(str, blockers))}"
            )
        if not device_uuid or not cmd:
            raise RuntimeAdmissionError(
                "runtime admission launch identity is incomplete"
            )
        return str(value["admission_sha256"])

    def _prepare_start(self, name: str) -> PreparedLaunch | dict[str, Any]:
        spec = self.get_spec(name)
        if not spec:
            raise ValueError(f"Unknown model {name}")
        if spec.runtime == "cpu" or spec.draft_for:
            return {
                "status": "skipped",
                "reason": "cpu-only or draft-attached model",
                "name": name,
            }
        if not spec.port:
            return {
                "status": "skipped",
                "reason": "no server port assigned",
                "name": name,
            }
        model_path = Path(spec.path) if spec.path else None
        if model_path is None or not model_path.is_file():
            return {
                "status": "skipped",
                "reason": f"GGUF missing: {spec.path}",
                "name": name,
            }
        cmd = tuple(self.build_cmd(name))
        env = self.launch_env(name)
        device_uuid = env.get("CUDA_VISIBLE_DEVICES", "")
        admission_sha256 = self._validate_runtime_admission(spec, cmd, device_uuid)
        if not isinstance(admission_sha256, str) or not re.fullmatch(
            r"[0-9a-f]{64}", admission_sha256
        ):
            raise RuntimeAdmissionError(
                "runtime admission validator returned no content identity"
            )
        return PreparedLaunch(
            spec=spec,
            cmd=cmd,
            env=env,
            device_uuid=device_uuid,
            admission_sha256=admission_sha256,
        )

    def _spawn_prepared(self, prepared: PreparedLaunch) -> dict[str, Any]:
        spec = prepared.spec
        proc = subprocess.Popen(
            list(prepared.cmd),
            stdout=subprocess.DEVNULL,  # nosec B603
            stderr=subprocess.DEVNULL,
            env=prepared.env,
        )
        self._procs[spec.name] = proc
        state = self.load_state()
        state.setdefault("loaded", [])
        if spec.name not in state["loaded"]:
            state["loaded"].append(spec.name)
        state.setdefault("ports", {})[spec.name] = spec.port
        state.setdefault("admissions", {})[spec.name] = {
            "admission_sha256": prepared.admission_sha256,
            "device_uuid": prepared.device_uuid,
        }
        self.save_state(state)
        time.sleep(1)
        return {
            "status": "started",
            "name": spec.name,
            "port": spec.port,
            "pid": proc.pid,
            "cmd": list(prepared.cmd),
            "admission_sha256": prepared.admission_sha256,
            "device_uuid": prepared.device_uuid,
        }

    def start(self, name: str, dry_run: bool = False) -> dict[str, Any]:
        prepared = self._prepare_start(name)
        if isinstance(prepared, dict):
            return prepared
        if dry_run:
            return {
                "status": "dry_run",
                "cmd": list(prepared.cmd),
                "name": name,
                "port": prepared.spec.port,
                "admission_sha256": prepared.admission_sha256,
                "device_uuid": prepared.device_uuid,
            }
        return self._spawn_prepared(prepared)

    def stop_on_demand(self) -> None:
        state = self.load_state()
        always = {s.name for s in self.list_models() if s.always_on}
        for name in list(self._procs):
            if name not in always:
                self._procs[name].terminate()
                del self._procs[name]
        state["loaded"] = [n for n in state.get("loaded", []) if n in always]
        self.save_state(state)

    def ensure_always_on(self, dry_run: bool = False) -> list[dict[str, Any]]:
        return [
            self.start(s.name, dry_run=dry_run)
            for s in self.list_models()
            if s.always_on and not s.draft_for
        ]

    def swap_to(self, name: str, dry_run: bool = False) -> dict[str, Any]:
        prepared = self._prepare_start(name)
        if isinstance(prepared, dict):
            return prepared
        if dry_run:
            return {
                "status": "dry_run",
                "cmd": list(prepared.cmd),
                "name": name,
                "port": prepared.spec.port,
                "admission_sha256": prepared.admission_sha256,
                "device_uuid": prepared.device_uuid,
            }
        self.stop_on_demand()
        return self._spawn_prepared(prepared)

    def status(self) -> dict[str, Any]:
        state = self.load_state()
        endpoints = self.swarm.get("endpoints", {})
        rows = []
        for name, spec in {s.name: s for s in self.list_models()}.items():
            if spec.runtime == "cpu" or spec.draft_for or not spec.port:
                continue
            short = name.split(".")[-1]
            rows.append(
                {
                    "name": name,
                    "port": spec.port,
                    "always_on": spec.always_on,
                    "on_demand": spec.on_demand,
                    "loaded": name in state.get("loaded", []),
                    "endpoint": endpoints.get(
                        short, f"http://127.0.0.1:{spec.port}/v1"
                    ),
                    "gguf_exists": bool(spec.path and Path(spec.path).exists()),
                    "draft_model": spec.draft_model or None,
                    "draft_path": self._resolve_draft_path(spec) or None,
                }
            )
        return {"state": state, "models": rows}
