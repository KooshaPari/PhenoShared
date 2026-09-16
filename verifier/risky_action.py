"""Pre-execution gate: watch LLM-proposed actions before risky side effects.

The gate extracts a proposed shell command from agent output, classifies its
risk tier, and checks secrets, allowlist, dry-run, verifier, and human-approval
requirements per ``config/risky_action_gate.yaml``.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from pheno.paths import CONFIG_DIR


@dataclass
class GateResult:
    """Outcome of a risky-action gate evaluation.

    Attributes:
        ok: Whether the proposal passes the gate.
        tier: Risk tier (low/medium/high/critical/none/disabled).
        action: Extracted shell command if any.
        checks: Per-check boolean outcomes.
        errors: Human-readable error strings.
        meta: Diagnostic metadata (mode, required checks).

    """

    ok: bool
    tier: str
    action: str
    checks: dict[str, bool] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the gate result to a JSON-compatible dict.

        Returns:
            Dict with all fields preserved.

        """
        return {
            "ok": self.ok,
            "tier": self.tier,
            "action": self.action,
            "checks": self.checks,
            "errors": self.errors,
            "meta": self.meta,
        }


def _load_gate_config() -> dict[str, Any]:
    """Load the risky-action gate config.

    Returns:
        Parsed gate config dict, or ``{"enabled": False}`` if missing.

    """
    path = CONFIG_DIR / "risky_action_gate.yaml"
    if not path.exists():
        return {"enabled": False}
    data: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    return dict(data) if isinstance(data, dict) else {}


def extract_proposed_command(text: str) -> str | None:
    """Best-effort extraction of a shell command from agent output.

    Checks JSON tool arguments, fenced bash blocks, and ``$ `` prompts.

    Args:
        text: Raw agent output text.

    Returns:
        Extracted command string or None if no action is proposed.

    """
    if not text:
        return None
    # JSON tool arguments
    m = re.search(r'"command"\s*:\s*"([^"]+)"', text)
    if m:
        return m.group(1)
    m = re.search(r'"bash"\s*:\s*"([^"]+)"', text)
    if m:
        return m.group(1)
    # fenced bash
    m = re.search(r"```(?:bash|sh|shell)\s*\n([\s\S]*?)```", text, re.I)
    if m:
        return m.group(1).strip().splitlines()[0] if m.group(1).strip() else None
    # inline run_terminal_cmd style
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("$ "):
            return line[2:].strip()
    return None


def _tier_for_command(cmd: str, cfg: dict[str, Any]) -> str:
    """Classify a command into a risk tier using blocklist and tier examples.

    Args:
        cmd: Extracted shell command.
        cfg: Loaded gate config.

    Returns:
        Risk tier string.

    """
    cmd_l = cmd.lower().strip()
    for entry in cfg.get("pattern_blocklist", []):
        pat: str = str(entry.get("regex", ""))
        if pat and re.search(pat, cmd, re.I):
            return str(entry.get("tier", "high"))
    low: list[str] = cfg.get("risk_tiers", {}).get("low", {}).get("examples", [])
    if any(x.replace("_", " ") in cmd_l or x in cmd_l for x in low):
        return "low"
    medium: list[str] = cfg.get("risk_tiers", {}).get("medium", {}).get("examples", [])
    if any(x.replace("_", " ") in cmd_l or x in cmd_l for x in medium):
        return "medium"
    # writes / installs default medium
    if re.search(
        r"\b(rm|mv|cp|chmod|pip|npm|docker|curl|wget|git push|git commit)\b", cmd_l
    ):
        return "high"
    return "medium"


def _check_secrets(cmd: str, cfg: dict[str, Any]) -> tuple[bool, str | None]:
    """Check a command against secret patterns.

    Args:
        cmd: Proposed shell command.
        cfg: Loaded gate config.

    Returns:
        Tuple of (ok, error_message).

    """
    for pat in cfg.get("secret_patterns", []):
        if re.search(str(pat), cmd):
            return False, f"secret pattern matched: {str(pat)[:40]}"
    return True, None


def _check_allowlist(cmd: str, cfg: dict[str, Any]) -> tuple[bool, str | None]:
    """Check absolute paths in a command against the workspace allowlist.

    Args:
        cmd: Proposed shell command.
        cfg: Loaded gate config.

    Returns:
        Tuple of (ok, error_message).

    """
    allow: dict[str, Any] = cfg.get("path_allowlist", {})
    if not allow.get("deny_absolute_outside_roots"):
        return True, None
    # Absolute paths outside known roots on Windows/Unix
    roots: list[str] = []
    for r in allow.get("workspace_roots", []):
        expanded = Path(
            str(r)
            .replace("${HOME}", str(Path.home()))
            .replace("${PHENO_ROOT}", str(CONFIG_DIR.parent))
        )
        roots.append(str(expanded.resolve()).lower())
    for m in re.finditer(r"(?:[A-Za-z]:\\|/)[^\s\"']+", cmd):
        p = m.group(0).strip("\"'")
        # skip URL-derived // (e.g. http://example.com -> //example.com)
        if p.startswith("//"):
            continue
        # also skip if this slash is part of :// in original cmd
        start = m.start()
        if start >= 2 and cmd[start - 2 : start] == ":/":
            continue
        if "://" in p:
            continue
        try:
            resolved = str(Path(p).resolve()).lower()
        except OSError:
            continue
        if roots and not any(resolved.startswith(root) for root in roots):
            return False, f"path outside allowlist: {p}"
    return True, None


def _dry_run_proposal(cmd: str) -> tuple[bool, str | None]:
    """Attempt a real dry-run when the command family supports one (P0).

    Supported:
      - ``git apply`` / ``git apply <file>`` → ``git apply --check``
      - ``docker ...`` → ``docker --help`` reachability (binary present)
    Unsupported / unavailable dry-runs fail loud — never scaffold True.

    Args:
        cmd: Proposed shell command.

    Returns:
        Tuple of (ok, error_message).

    """
    cmd_l = cmd.lower().strip()
    if re.search(r"\bgit\s+apply\b", cmd_l):
        # Prefer --check against an explicit patch path if present.
        m = re.search(r"git\s+apply(?:\s+--check)?\s+(\S+\.(?:patch|diff))", cmd, re.I)
        if m:
            patch_path = Path(m.group(1))
            if not patch_path.exists():
                return False, f"dry_run: patch file not found: {patch_path}"
            proc = subprocess.run(
                ["git", "apply", "--check", str(patch_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if proc.returncode != 0:
                return False, proc.stderr.strip() or "dry_run: git apply --check failed"
            return True, None
        return (
            False,
            "dry_run: git apply requires a local .patch/.diff path for --check",
        )
    if re.search(r"\bdocker\b", cmd_l):
        if not shutil.which("docker"):
            return False, "dry_run: docker not available on PATH"
        # Reachability only — do not execute the proposed container command.
        proc = subprocess.run(
            ["docker", "version", "--format", "{{.Client.Version}}"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if proc.returncode != 0:
            return False, proc.stderr.strip() or "dry_run: docker not reachable"
        return True, None
    # Read-only / no dry-run surface — report unavailable rather than fake success.
    if re.search(
        r"\b(rm|mv|cp|chmod|pip|npm|curl|wget|git\s+push|git\s+commit)\b", cmd_l
    ):
        return False, "dry_run: no safe dry-run available for this command family"
    return True, None


def check_proposal(
    text: str,
    *,
    verifier_ok: bool | None = None,
    human_approved: bool = False,
) -> GateResult:
    """Watch a model proposal before executing a risky action.

    Args:
        text: Raw agent output that may contain a proposal.
        verifier_ok: Whether the verifier passed before the proposal.
        human_approved: Whether a human has approved the tier.

    Returns:
        ``GateResult`` with tier, checks, and errors.

    """
    cfg: dict[str, Any] = _load_gate_config()
    if not cfg.get("enabled", True):
        return GateResult(
            ok=True, tier="disabled", action="", checks={"gate_disabled": True}
        )

    cmd = extract_proposed_command(text)
    if not cmd:
        return GateResult(
            ok=True,
            tier="none",
            action="",
            checks={"no_action_proposed": True},
            meta={"mode": cfg.get("default_mode")},
        )

    tier = _tier_for_command(cmd, cfg)
    tier_cfg: dict[str, Any] = cfg.get("risk_tiers", {}).get(tier, {})
    required: list[str] = tier_cfg.get("requires", [])

    checks: dict[str, bool] = {}
    errors: list[str] = []

    checks["output_parseable"] = bool(cmd)
    if "output_parseable" in required and not checks["output_parseable"]:
        errors.append("could not parse proposed action")

    # explicit blocklist check (distinct from secret check)
    block_ok = True
    block_err: str | None = None
    for entry in cfg.get("pattern_blocklist", []):
        pat = str(entry.get("regex", ""))
        if pat and re.search(pat, cmd, re.I):
            block_ok = False
            block_err = f"blocklist {entry.get('id', 'unknown')}: {pat[:40]}"
            break
    checks["pattern_blocklist_clear"] = block_ok
    if not block_ok and block_err:
        errors.append(block_err)

    ok_secret, err_secret = _check_secrets(cmd, cfg)
    # keep secret check separate (not clobbering blocklist)
    checks["secret_clear"] = ok_secret
    if not ok_secret and err_secret:
        errors.append(err_secret)

    ok_path, err_path = _check_allowlist(cmd, cfg)
    checks["path_in_allowlist"] = ok_path
    if not ok_path and err_path:
        errors.append(err_path)

    ok_dry, err_dry = _dry_run_proposal(cmd)
    checks["dry_run_when_available"] = ok_dry
    if "dry_run_when_available" in required and not ok_dry:
        errors.append(err_dry or "dry_run unavailable")

    if "verifier_pass" in required:
        checks["verifier_pass"] = verifier_ok is True
        if verifier_ok is not True:
            errors.append("verifier did not pass before risky action")

    if "human_approve" in required or tier_cfg.get("block_autonomous"):
        checks["human_approve"] = human_approved
        if not human_approved:
            errors.append(f"tier {tier} requires human approval")

    ok = all(checks.get(k, True) for k in required) and len(errors) == 0
    return GateResult(
        ok=ok,
        tier=tier,
        action=cmd,
        checks=checks,
        errors=errors,
        meta={"mode": cfg.get("default_mode"), "required": required},
    )
