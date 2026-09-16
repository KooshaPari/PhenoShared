"""Explicit, local-only lifecycle planning for one-model serving slots.

The controller never resolves Hugging Face identifiers.  A start operation
requires a pre-existing local model directory, preventing accidental downloads
during evaluation setup.
"""

from __future__ import annotations

import os
import re
import subprocess  # nosec B404
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pheno.serve.config import ServeConfig
from pheno.serve.registry import ProfileRegistry


@dataclass(frozen=True)
class LaunchPlan:
    """One resolved engine launch (alias, command, model path, slot)."""

    alias: str
    engine: str
    slot: str
    command: list[str]
    model_path: Path


def _expand(value: str) -> str:
    """Expand ``${VAR:-default}`` style placeholders using ``os.environ``."""

    def replace(match: re.Match[str]) -> str:
        """Resolve one ``${VAR:-default}`` placeholder against ``os.environ``."""
        return os.environ.get(match.group(1), match.group(2))

    return os.path.expandvars(re.sub(r"\$\{([^:}]+):-([^}]*)\}", replace, value))


class SlotController:
    """Build and execute explicit local engine launches.

    Launching remains opt-in.  The default command path is a dry-run, and every
    non-SGLang profile must provide a local model path plus an explicit engine
    executable through the environment or profile metadata.
    """

    def __init__(self, config: ServeConfig):
        self.config = config
        self.registry = ProfileRegistry(config)
        self.slots: dict[str, dict[str, Any]] = config.raw.get("engine_slots", {}) or {}

    def plan(self, alias: str) -> LaunchPlan:
        """Build a LaunchPlan for the named profile alias (refuses network-backed models)."""
        profile = self.registry.get(alias)
        raw_path = _expand(str(profile.raw.get("model_path", ""))).strip()
        if not raw_path:
            raise ValueError(
                f"{profile.alias} has no local model_path; refusing a network-backed launch"
            )
        model_path = Path(raw_path).expanduser()
        if not model_path.is_dir():
            raise ValueError(f"local model_path does not exist: {model_path}")

        slot_name = str(profile.raw.get("engine_slot", ""))
        slot = self.slots.get(slot_name, {}) if slot_name else {}
        if slot_name:
            if profile.alias not in slot.get("aliases", []):
                raise ValueError(
                    f"{profile.alias} is not permitted in slot {slot_name}"
                )
            if slot.get("residency") != "one_model_at_a_time":
                raise ValueError(
                    f"slot {slot_name} must declare one_model_at_a_time residency"
                )

        base_url = str(slot.get("base_url", profile.base_url or "")).rstrip("/")
        port = base_url.rsplit(":", 1)[-1].removesuffix("/v1")
        if not port.isdigit():
            raise ValueError(f"unable to derive port from slot base_url: {base_url}")
        engine = profile.engine.lower().replace("-", "_").replace(".", "_")
        if engine == "sglang":
            command = [
                "python",
                "-m",
                "sglang.launch_server",
                "--model-path",
                str(model_path),
                "--host",
                "127.0.0.1",
                "--port",
                port,
            ]
        elif engine == "vllm":
            executable = _expand(
                str(profile.raw.get("executable", "${PHENO_VLLM_EXECUTABLE:-vllm}"))
            )
            command = [
                executable,
                "serve",
                str(model_path),
                "--host",
                "127.0.0.1",
                "--port",
                port,
            ]
        elif engine == "llama_cpp":
            executable = _expand(
                str(
                    profile.raw.get("executable", "${PHENO_LLAMA_SERVER:-llama-server}")
                )
            )
            command = [
                executable,
                "-m",
                str(model_path),
                "--host",
                "127.0.0.1",
                "--port",
                port,
            ]
        elif engine == "tensorrt_llm":
            executable = _expand(
                str(
                    profile.raw.get(
                        "executable", "${PHENO_TRTLLM_EXECUTABLE:-trtllm-serve}"
                    )
                )
            )
            command = [
                executable,
                str(model_path),
                "--host",
                "127.0.0.1",
                "--port",
                port,
            ]
        else:
            raise ValueError(
                f"{profile.alias} uses unsupported launch engine {profile.engine!r}"
            )
        return LaunchPlan(
            alias=profile.alias,
            engine=profile.engine,
            slot=slot_name,
            model_path=model_path,
            command=command,
        )

    def start(self, alias: str, dry_run: bool = True) -> dict[str, Any]:
        """Execute or dry-run a launch plan for the given alias."""
        plan = self.plan(alias)
        result: dict[str, Any] = {
            "status": "dry_run" if dry_run else "started",
            "alias": plan.alias,
            "engine": plan.engine,
            "slot": plan.slot,
            "model_path": str(plan.model_path),
            "command": plan.command,
        }
        if not dry_run:
            proc = subprocess.Popen(plan.command)  # nosec B603
            result["pid"] = proc.pid
        return result
