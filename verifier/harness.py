"""Verifier harness — JSON/tool/patch/test checks for RLVR-AF (Phase 3).

.. deprecated::
    This bespoke verifier is deprecated as of 2026-07-21. The canonical
    verifier is ``portage/src/harbor/verifier/`` which writes reward to
    ``/logs/verifier/reward.txt`` (or ``reward.json``) per the Harbor
    contract. Migration target for the RLVR-AF factor itself is the
    ``harbor-pheno`` extension package
    (``portage/packages/harbor-pheno/src/harbor_pheno/rlvr_af.py``).

This module exposes ``VerifierHarness`` and the typed result ``VerifierResult``
(aliased as ``Verdict`` for task 54 narrowing).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pheno.paths import CONFIG_DIR, TRAINING_DIR
from verifier.risky_action import check_proposal


@dataclass
class VerifierResult:
    """Result of verifying a single trace.

    Attributes:
        trace_id: Identifier extracted from the trace.
        role: Normalized role string.
        ok: Whether required checks and error list indicate pass.
        checks: Per-check boolean outcomes.
        errors: Human-readable error strings.
        meta: Diagnostic metadata (tokens, caps, escalation).

    """

    trace_id: str
    role: str
    ok: bool
    checks: dict[str, bool] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the result to a JSON-compatible dict.

        Returns:
            Dict with all fields preserved.

        """
        return {
            "trace_id": self.trace_id,
            "role": self.role,
            "ok": self.ok,
            "checks": self.checks,
            "errors": self.errors,
            "meta": self.meta,
        }


# Task 54 narrowing alias: Verdict is the canonical typed result.
Verdict = VerifierResult


def _load_caps() -> dict[str, dict[str, int]]:
    """Load output/context caps per role.

    Returns:
        Mapping of role to caps dict, empty if config is absent.

    """
    caps_path = CONFIG_DIR / "context_caps.yaml"
    if not caps_path.exists():
        return {}
    raw: dict[str, Any] = yaml.safe_load(caps_path.read_text(encoding="utf-8")) or {}
    roles: Any = raw.get("roles", {})
    return dict(roles) if isinstance(roles, dict) else {}


def _check_json(text: str) -> tuple[bool, str | None]:
    """Validate that text contains parseable JSON.

    Args:
        text: Model response text, possibly fenced.

    Returns:
        Tuple of (ok, error_message). Error is None on success.

    """
    text = text.strip()
    if not text:
        return False, "empty response"
    # fenced ```json block or raw object/array
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    payload = m.group(1).strip() if m else text
    try:
        json.loads(payload)
        return True, None
    except json.JSONDecodeError as e:
        return False, str(e)


def _check_tool_call(text: str) -> tuple[bool, str | None]:
    """Detect a tool-call structure in text.

    Args:
        text: Model response text.

    Returns:
        Tuple of (ok, error_message).

    """
    patterns = [
        r'"tool"\s*:',
        r'"name"\s*:\s*"[^"]+"\s*,\s*"arguments"',
        r"<tool_call>",
    ]
    if any(re.search(p, text) for p in patterns):
        return True, None
    return False, "no tool call structure detected"


def _check_patch(text: str, repo_root: Path | None) -> tuple[bool, str | None]:
    """Dry-apply a unified diff via ``git apply --check`` (P0 — no scaffold pass).

    Args:
        text: Model response containing a patch.
        repo_root: Repository root to apply against.

    Returns:
        Tuple of (ok, error_message).

    """
    if not repo_root or not repo_root.exists():
        return False, "repo_root missing for patch check"
    diff = text
    m = re.search(r"```(?:diff|patch)?\s*([\s\S]*?)```", text)
    if m:
        diff = m.group(1)
    if "@@" not in diff and "---" not in diff:
        return False, "no unified diff found"
    if not (repo_root / ".git").exists():
        return False, "repo_root is not a git checkout; cannot dry-apply patch"
    proc = subprocess.run(
        ["git", "apply", "--check", "-"],
        input=diff,
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        return False, proc.stderr.strip() or "git apply --check failed"
    return True, None


def _check_tests(cmd: list[str] | None, cwd: Path | None) -> tuple[bool, str | None]:
    """Run the trace's test command. Missing cmd fails loud (P0 — no silent pass).

    Args:
        cmd: Command list to execute.
        cwd: Working directory for the command.

    Returns:
        Tuple of (ok, error_message or tail output).

    """
    if not cmd:
        return False, "test_cmd required but missing"
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if proc.returncode != 0:
        tail = (proc.stdout + proc.stderr)[-500:]
        return False, tail
    return True, None


class VerifierHarness:
    """Run verifiable checks on a model trace or response.

    Attributes:
        config_path: Path to ``rlvr_config.yaml``.
        config: Loaded verifier config.
        role_caps: Per-role token caps.

    """

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize the harness from config.

        Args:
            config_path: Optional override path. Defaults to
                ``training/rlvr_config.yaml`` relative to repo root.

        """
        self.config_path = (
            config_path
            or Path(__file__).resolve().parents[1] / "training" / "rlvr_config.yaml"
        )
        self.config: dict[str, Any] = self._load_config()
        self.role_caps: dict[str, dict[str, int]] = _load_caps()

    def _load_config(self) -> dict[str, Any]:
        """Load verifier config from YAML.

        Returns:
            Parsed config dict with sensible defaults if file is missing.

        """
        if not self.config_path.exists():
            return {"verifiers": {}, "pass_threshold": 0.75}
        data: Any = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
        return dict(data) if isinstance(data, dict) else {}

    def verify_trace(self, trace: dict[str, Any]) -> VerifierResult:
        """Verify a single trace dict and return a typed result.

        Args:
            trace: Trace dict produced by the harness or training loop.
                Expected keys include ``id``/``trace_id``, ``role``,
                ``response``/``completion``/``output``, ``repo_root``,
                ``test_cmd``, and model routing fields.

        Returns:
            ``VerifierResult`` (alias ``Verdict``) with checks, errors, and meta.

        """
        trace_id = str(trace.get("id") or trace.get("trace_id") or "unknown")
        role = str(trace.get("role") or trace.get("header_role") or "patch").lower()
        response = str(
            trace.get("response")
            or trace.get("completion")
            or trace.get("output")
            or ""
        )
        caps: dict[str, int] = self.role_caps.get(role, {})
        meta: dict[str, Any] = {
            "output_tokens": trace.get("tokens_out")
            or trace.get("output_tokens")
            or len(response) // 4,
            "context_tokens": trace.get("tokens_in")
            or trace.get("context_tokens")
            or 0,
            "baseline_context_tokens": trace.get("baseline_context_tokens")
            or trace.get("tokens_in")
            or 0,
            "output_cap": caps.get("max_output", trace.get("output_cap", 1200)),
            "context_budget": caps.get(
                "max_context", trace.get("context_budget", 32768)
            ),
            "expected_escalation": trace.get("expected_escalation"),
            "actual_escalation": trace.get("actual_escalation") or trace.get("model"),
        }
        vcfg: dict[str, Any] = self.config.get("verifiers", {})
        checks: dict[str, bool] = {}
        errors: list[str] = []

        if vcfg.get("json", {}).get("enabled", True):
            ok, err = _check_json(response)
            checks["json_valid"] = ok
            if not ok and err:
                errors.append(f"json: {err}")

        if vcfg.get("tool", {}).get("enabled", True):
            ok, err = _check_tool_call(response)
            checks["tool_valid"] = ok
            if not ok and err and role in ("retrieve", "plan", "patch"):
                errors.append(f"tool: {err}")

        repo = trace.get("repo_root")
        repo_path = Path(str(repo)) if repo else None
        if vcfg.get("patch", {}).get("enabled", True) and role in ("patch", "debug"):
            ok, err = _check_patch(response, repo_path)
            checks["patch_applies"] = ok
            if not ok and err:
                errors.append(f"patch: {err}")

        raw_test_cmd: Any = trace.get("test_cmd")
        test_cmd: list[str] | None = None
        if isinstance(raw_test_cmd, list):
            test_cmd = [str(x) for x in raw_test_cmd]
        elif isinstance(raw_test_cmd, str):
            test_cmd = raw_test_cmd.split()
        else:
            test_cmd = None
        if vcfg.get("tests", {}).get("enabled", True):
            ok, err = _check_tests(test_cmd, repo_path)
            checks["tests_pass"] = ok
            if not ok and err:
                errors.append(f"tests: {err}")

        expected = meta.get("expected_escalation")
        actual = meta.get("actual_escalation")
        if expected is not None:
            checks["correct_escalation"] = str(expected).lower() in str(actual).lower()
        else:
            checks["correct_escalation"] = False

        if vcfg.get("risky_action", {}).get("enabled", True):
            pre_ok = all(
                checks.get(k, True)
                for k in ("json_valid", "tool_valid", "patch_applies", "tests_pass")
            )
            gate = check_proposal(response, verifier_ok=pre_ok)
            checks["risky_action_gate"] = gate.ok
            meta["risky_action_tier"] = gate.tier
            meta["risky_action"] = gate.action
            if not gate.ok:
                errors.extend(f"risky_action: {e}" for e in gate.errors)

        float(self.config.get("pass_threshold", 0.75))
        required: list[str] = vcfg.get("required_checks", ["json_valid", "tests_pass"])
        ok = all(checks.get(k, True) for k in required) and len(errors) == 0

        return VerifierResult(
            trace_id=trace_id,
            role=role,
            ok=ok,
            checks=checks,
            errors=errors,
            meta=meta,
        )

    def verify_jsonl(self, path: Path) -> list[VerifierResult]:
        """Verify all traces in a JSONL file.

        Args:
            path: Path to a JSONL file where each line is a trace dict.

        Returns:
            List of ``VerifierResult`` records.

        """
        results: list[VerifierResult] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            trace: dict[str, Any] = json.loads(line)
            results.append(self.verify_trace(trace))
        return results

    def find_traces(self, glob: str = "traces_*.jsonl") -> list[Path]:
        """Find trace JSONL files under ``TRAINING_DIR``.

        Args:
            glob: Glob pattern for trace files.

        Returns:
            Sorted list of matching paths.

        """
        return sorted(TRAINING_DIR.glob(glob))
