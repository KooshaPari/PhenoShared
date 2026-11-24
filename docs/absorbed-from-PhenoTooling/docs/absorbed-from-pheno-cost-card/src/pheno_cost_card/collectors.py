from __future__ import annotations

import json
import subprocess
from pathlib import Path


def gh_actions_minutes(repo: Path, month: str) -> float:
    """Collect GitHub Actions minutes for a repo/month.

    This reads a checked-in or generated billing export when present. The expected
    file is `.cost-card/gh-actions-minutes.json` with `{\"YYYY-MM\": minutes}`.
    """
    ledger = repo / ".cost-card" / "gh-actions-minutes.json"
    if not ledger.exists():
        return 0.0
    data = json.loads(ledger.read_text())
    return float(data.get(month, 0.0))


def lfm_token_ledger(repo: Path, month: str) -> float:
    """Collect LLM token spend in USD from a local ledger.

    The expected file is `.cost-card/lfm-token-ledger.json` with either
    `{\"YYYY-MM\": usd}` or `{\"YYYY-MM\": {\"usd\": usd}}`.
    """
    ledger = repo / ".cost-card" / "lfm-token-ledger.json"
    if not ledger.exists():
        return 0.0
    data = json.loads(ledger.read_text())
    value = data.get(month, 0.0)
    if isinstance(value, dict):
        return float(value.get("usd", 0.0))
    return float(value)


def du_storage(repo: Path) -> float:
    """Measure repository storage in GB using `du -sk`."""
    result = subprocess.run(
        ["du", "-sk", str(repo)],
        check=True,
        capture_output=True,
        text=True,
    )
    kb = float(result.stdout.split()[0])
    return kb / 1024 / 1024
