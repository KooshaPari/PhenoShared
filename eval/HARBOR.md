# Harbor — Terminal Bench (local, heterogeneous GPUs)

[Harbor](https://github.com/laude-institute/harbor) runs agent benchmarks (including Terminal Bench) in isolated containers. This repo wires a **local-only** setup with one concurrent trial by default, using the Docker-compatible Podman API and the pinned local task export when available.

**Relationship:** `pheno-harness` is a **consumer/wrapper** of Harbor. The Phenotype Harbor product fork is **[portage-TEMP](https://github.com/<REDACTED>/portage-TEMP)** (`repos/portage`). Do not duplicate that product here — see [docs/guides/PORTAGE_AND_HARBOR.md](../docs/guides/PORTAGE_AND_HARBOR.md). Default install uses **PyPI** `harbor>=0.6`; use the fork only when you need fork-only features.

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| **Docker-compatible engine** | Podman machine or Docker Desktop; `docker info` must return within the launcher timeout |
| **Harbor 0.18.0** (pinned locally) | Resolved from the validated uv cache executable; or `pip install harbor` / `uv pip install -e ".[harbor]"` from this repo |
| **GPU** | Not required for oracle sanity; agent runs may need local LLM endpoints separately |

### Install Harbor (PyPI — default for this repo)

```bash
# from pheno-harness venv
uv pip install -e ".[harbor]"
# or
pip install harbor
harbor --version
```

```powershell
pip install harbor
# CLI may land under %APPDATA%\Python\Python3xx\Scripts\harbor.exe — add to PATH if needed
```

### Install Harbor (portage-TEMP fork — optional)

Only when you need fork features (e.g. LLM bridge). From the portage checkout:

```bash
# see portage/portage-TEMP README — do not copy sources into pheno-harness
uv sync
./scripts/build_rust.sh --only llm-bridge   # if required
uv run harbor --help
```

Python 3.14 worked without falling back to 3.12 on the original Windows operator host. If install fails on another machine, try:

```powershell
py -3.12 -m pip install harbor
```

## Verified on this host (2026-07-16)

| Check | Result |
|-------|--------|
| `harbor --version` | **0.18.0** from the validated local uv cache |
| `harbor --help` | OK — commands: `run`, `dataset`, `download`, `job`, `trial`, … |
| Docker-compatible Podman API | Recovered and used by bounded local pilots |
| Bounded local pilots | LFM and Ornith each completed one scoreable task with reward `0.0`; representative six-task pilot remains pending bootstrap verification |

## Dataset slug (Terminal Bench 2.1)

Harbor registry query (`harbor registry` / Supabase `dataset` table) as of **2026-06-13**:

| Slug | Tasks | Notes |
|------|-------|--------|
| **`terminal-bench@2.0`** | 89 | Latest Terminal Bench in Harbor registry |
| `terminal-bench-sample@2.0` | 10 | Sample subset |
| `terminal-bench-pro@1.0` | 200 | Extended public set |
| **`terminal-bench@2.1`** | — | **Not published** — `harbor download terminal-bench@2.1` → `Dataset terminal-bench@2.1 not found` |

**Use the pinned local `terminal-bench@2.0` export** at `D:\WSL\eval-cache\harbor-terminal-bench-2.0\terminal-bench` on this host. The lock and `config/tbench20_representative_subset.json` provide the task and tree hashes; registry resolution is fallback-only.

List registry datasets locally:

```powershell
python -c "import asyncio; from harbor.registry.client.harbor.harbor import HarborRegistryClient; asyncio.run(HarborRegistryClient().list_datasets())"
```

Or: `harbor datasets list` (points to the Hub UI).

## Terminal Bench 2.0 — per-model leaderboard (honest eval)

Goal: **≥80% mean** on full **89-task** holdout via **terminus-2** only (no oracle, no DPO on these tasks).

```powershell
# Probe which OmniRoute routes work right now
python scripts/probe_omniroute_models.py --force

# Full matrix (sequential — ~12h per model at n_concurrent=1)
python scripts/run_tbench_model_matrix.py --all --resume --n-tasks 89

# Single model pilot
python scripts/run_tbench_model_matrix.py --model kc/minimax/minimax-m3 --n-tasks 10

# Leaderboard
python scripts/tbench_scoreboard.py --export
```

Config: `config/harbor_tbench_models.yaml`  
Results: `eval/results/tbench_model_scores.json`  
State: `state/tbench_matrix.json`  
Holdout guard: `training/eval_holdout.yaml`

Integrity: `n_attempts=1`, holdout excluded from `nightly_dpo` / distill. Oracle sanity (`run_tbench_local.ps1`) is **not** on the model leaderboard.

## Route matrix — non-firepass cloud + local + Main router

Separate from firepass Kimi runs. Measures **quality (TB2 mean)**, **TPS proxy**, and **$/run** with a composite score (40% accuracy / 30% speed / 30% cost). References OmniRoute `Main` router weights in `config/combo_main.json`.

**Prerequisites:** OmniRoute on `:20128`, local swarm (`scripts/start_local_swarm.ps1`) for `local_direct` routes, Docker for Harbor.

```powershell
# Probe routes (OmniRoute cloud, llama-server local, Main combo)
python scripts/probe_tbench_routes.py --force

# Pilot 3 tasks per route kind
python scripts/run_tbench_route_matrix.py --route-kind omniroute_cloud --pilot --force
python scripts/run_tbench_route_matrix.py --route-kind local_direct --pilot --force
python scripts/run_tbench_route_matrix.py --include-combo --pilot --force

# Full holdout per model
python scripts/run_tbench_route_matrix.py --all --resume --n-tasks 89 --force

# Scoreboard (composite ranking)
python scripts/tbench_route_scoreboard.py --export
```

Config: `config/harbor_tbench_routes.yaml`  
Results: `eval/results/tbench_route_scores.json`  
State: `state/tbench_routes_matrix.json`

Route kinds:
- `omniroute_cloud` — individual cloud models (MiniMax, Qwen, Kimi via OmniRoute, non-firepass)
- `local_direct` — llama-server ports 8080–8084 (TPS baseline, $0)
- `omniroute_combo` — `Main` combo (cost/latency router optimizer)

---

`config/harbor.yaml` — local docker-only job:

- `environment.type: docker`
- `n_concurrent_trials: 1` (3090 Ti — avoid parallel container builds)
- `agents: [oracle]` for sanity / gold-path checks
- `datasets: terminal-bench@2.0`

## Run

Start a Docker-compatible Podman machine or Docker Desktop, then:

```powershell
cd C:\Users\koosh\pheno-harness

# Representative six-task local pilot
.\harbor\run_tbench_local.ps1

# Full dataset after sanity passes
.\harbor\run_tbench_local.ps1 -Full

# Manual equivalent against the pinned local export
harbor run -c config/harbor.yaml -p D:\WSL\eval-cache\harbor-terminal-bench-2.0\terminal-bench -a harness.harbor.terminus_safe:SafeTerminus2 --n-concurrent 1 --n-tasks 1 -y
```

Results land under `jobs/harbor/` (see `jobs_dir` in config).

## Harbor CLI reference

```text
harbor --version          # 0.18.0
harbor run                # alias for harbor job start
harbor run -c PATH        # JobConfig YAML/JSON
harbor run -p PATH        # pinned local task export
harbor run -a oracle -n 1 # oracle agent, 1 concurrent trial
```

Key flags: `--env docker` (default), `--n-tasks N`, `-y` (auto-confirm host access prompts).

## Windows notes

- Set `PYTHONIOENCODING=utf-8` if Harbor/Rich throws `UnicodeEncodeError` on cp1252 consoles (the run script sets this).
- Harbor is not on PATH by default after user install; `run_tbench_local.ps1` resolves `%APPDATA%\Python\Python314\Scripts\harbor.exe`.

## Troubleshooting

| Error | Fix |
|-------|-----|
| `dockerDesktopLinuxEngine` pipe missing / `docker ps` hangs | Start Docker Desktop; wait until `docker info` succeeds (~10s on this host) |
| `Docker daemon is not running` (Harbor preflight) | Harbor runs `docker info` with a **10s timeout**; warm up Docker first or retry after engine is ready |
| `Cannot create a file when that file already exists: .cache` | `~/.cache` is a symlink — ensure the target exists, e.g. `mkdir E:\caches\dotcache\harbor` |
| `harbor` not recognized | Use full path to `harbor.exe` or add Python Scripts to PATH |
| `terminal-bench@2.1 not found` | Use `@2.0` or watch Harbor Hub for 2.1 release |
| Unicode console errors | `$env:PYTHONIOENCODING='utf-8'` |
