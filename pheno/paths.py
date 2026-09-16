from __future__ import annotations

import os
from pathlib import Path

HOME = Path.home()
PHENO_ROOT = Path(__file__).resolve().parents[1]
OMNIROUTE_DB = HOME / ".omniroute" / "storage.sqlite"
OMNIROUTE_URL = os.environ.get("OMNIROUTE_URL", "http://localhost:20128")
TRAINING_DIR = HOME / ".omniroute" / "training"
BENCH_DIR = PHENO_ROOT / "bench" / "results"
STATE_DIR = PHENO_ROOT / "state"
CONFIG_DIR = PHENO_ROOT / "config"
EVAL_DIR = PHENO_ROOT / "eval"
EVAL_RESULTS_DIR = EVAL_DIR / "results"
EVAL_EXPERIMENTS_DIR = EVAL_DIR / "experiments"
TRACES_DIR = PHENO_ROOT / "traces"
FORGE_DIR = HOME / "forge"
AGENT_RUNNER_DIR = HOME / ".claude" / "tools" / "agent-runner"
FORGE_DISPATCH_DIR = HOME / ".claude" / "forge-dispatch"
CURSOR_PROJECTS = HOME / ".cursor" / "projects"

for d in (
    TRAINING_DIR,
    BENCH_DIR,
    STATE_DIR,
    EVAL_RESULTS_DIR,
    EVAL_EXPERIMENTS_DIR,
    TRACES_DIR,
):
    d.mkdir(parents=True, exist_ok=True)
