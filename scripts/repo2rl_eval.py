#!/usr/bin/env python3
"""Run Harbor eval on Repo2RL / local datasets; export rewards for tuning loop."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pheno.harbor_util import harbor_exe, litellm_model, omniroute_env
from pheno.paths import CONFIG_DIR, EVAL_RESULTS_DIR, PHENO_ROOT


def _harbor_exe() -> str:
    return harbor_exe()


def _expand(s: str) -> str:
    return os.path.expandvars(s.replace("${PHENO_ROOT}", str(PHENO_ROOT)))


def _resolve_harbor_tasks_dir(dataset_dir: Path) -> Path:
    """Repo2RL HF pulls use dataset/tasks/<name>/; Harbor expects task children directly."""
    tasks = dataset_dir / "tasks"
    if tasks.is_dir() and any(tasks.iterdir()):
        return tasks
    return dataset_dir


def _litellm_model(model: str) -> str:
    return litellm_model(model)


def _omniroute_env() -> dict[str, str]:
    return omniroute_env()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--dataset-dir", type=Path, default=None, help="Local Harbor task dir"
    )
    p.add_argument(
        "--agent", default="oracle", help="oracle | terminus-2 | codex | claude-code"
    )
    p.add_argument("--model", default="Main", help="Model for terminus-2 via OmniRoute")
    p.add_argument("--n-tasks", type=int, default=1)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    cfg = yaml.safe_load((CONFIG_DIR / "repo2rl.yaml").read_text(encoding="utf-8"))
    dataset_dir = args.dataset_dir
    if not dataset_dir:
        ref = cfg["reference_pull"][0]
        dataset_dir = Path(_expand(ref["local_dir"]))

    if not dataset_dir.exists() or not any(dataset_dir.iterdir()):
        print(f"Dataset missing: {dataset_dir}. Run: python scripts/repo2rl_setup.py")
        return 1

    tasks_dir = _resolve_harbor_tasks_dir(dataset_dir)
    harbor = _harbor_exe()
    # Harbor/Portage requires this environment token for Podman's compatibility API.
    cmd = [
        harbor,
        "run",
        "-p",
        str(tasks_dir),
        "-a",
        args.agent,
        "--env",
        "docker",
        "--n-concurrent",
        "1",
        "-l",
        str(args.n_tasks),
        "-o",
        str(PHENO_ROOT / "jobs" / "harbor"),
        "-y",
    ]
    harbor_model = (
        _litellm_model(args.model) if args.agent == "terminus-2" else args.model
    )
    if args.agent == "terminus-2":
        cmd.extend(["-m", harbor_model])

    env = _omniroute_env()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    if args.agent == "terminus-2" and not env.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY missing — set env or configure ~/forge/.credentials.json")
        return 1

    print("Command:", " ".join(cmd))
    if args.dry_run:
        return 0

    r = subprocess.run(cmd, cwd=PHENO_ROOT, env=env)
    stdout_tail = ""

    result = {
        "timestamp": datetime.now(UTC).isoformat(),
        "dataset_dir": str(dataset_dir),
        "tasks_dir": str(tasks_dir),
        "agent": args.agent,
        "model": args.model,
        "harbor_model": harbor_model if args.agent == "terminus-2" else args.model,
        "returncode": r.returncode,
        "stdout_tail": stdout_tail,
    }
    EVAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = EVAL_RESULTS_DIR / "repo2rl_eval_latest.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    reward_log = Path(_expand(cfg["integration"]["reward_export"]))
    reward_log.parent.mkdir(parents=True, exist_ok=True)
    with reward_log.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"kind": "harbor_run", **result}) + "\n")

    print(f"Wrote {out}")
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
