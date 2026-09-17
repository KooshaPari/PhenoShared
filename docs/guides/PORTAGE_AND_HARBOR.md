# Portage / Harbor relationship

**pheno-harness is a consumer and thin wrapper — not a Harbor fork.**

| Layer | Repo | What it is |
|-------|------|------------|
| **Harbor product** | [<REDACTED>/portage-TEMP](https://github.com/KooshaPari/portage-TEMP) (local checkout often `repos/portage`) | Fork of the Harbor framework (eval sandboxes, datasets, RL rollouts, optional Rust LLM bridge) |
| **Upstream Harbor** | [laude-institute/harbor](https://github.com/laude-institute/harbor) / PyPI `harbor` | Published package; `pip install harbor` / `uv tool install harbor` |
| **This repo** | `pheno-harness` | OmniRoute operator stack: configs, RLVR verifiers, bench skeleton, **wrapper scripts** that invoke Harbor CLI |

## Do not duplicate the product

- Do **not** vendor Harbor / portage sources into this repo.
- Prefer depending on PyPI `harbor>=0.6` (see `pyproject.toml` extra `[harbor]`) for TB2 jobs.
- Use a local **portage-TEMP** checkout only when you need fork-only features (e.g. `harbor-llm-bridge`). Install that fork from its own README (`uv sync` + optional Rust build) — then point PATH / `uv run harbor` at that environment.

## What lives under `harbor_cli/` here

PowerShell job wrappers and configs only:

- `harbor_cli/run_tbench_local.ps1` — oracle sanity / full TB2 via `harbor run`
- `harbor_cli/run_tbench_models.ps1`, `run_tbench_routes.ps1`, `run_agent_eval.ps1`
- Job YAML: `config/harbor.yaml`, `config/harbor_tbench_*.yaml`

**Note:** As of v0.11, the `harbor/` directory was renamed to `harbor_cli/`
to eliminate a Python namespace package shadow that was masking the real
`harbor` package import. The CLI wrappers are unchanged in content.

Operator docs: [eval/HARBOR.md](../../eval/HARBOR.md).

## Eval / RLVR stack in this repo

| Path | Role |
|------|------|
| `bench/` | Multi-suite benchmark harness (`python -m bench`) |
| `bench/runner/` | Back-compat re-exports + restored `model_adapter` / `executor` for tests |
| `verifier/` | RLVR rewards + risky-action gate (P0 paths fail loud — no scaffold pass) |
| `eval/` | Pillars, Harbor bridge notes, playground |
| `scripts/run_tbench_*.py` | OmniRoute Main / route matrices calling Harbor |
| `scripts/harbor_consumer_dry_run.py` | Optional PyPI `harbor` import/CLI dry-run (no framework fork) |

These orchestrate and score; Harbor (or portage-TEMP) owns containerized trials.

### Harbor consumer dry-run

```bash
uv pip install -e ".[harbor]"
python scripts/harbor_consumer_dry_run.py            # import check
python scripts/harbor_consumer_dry_run.py --require-cli  # also `harbor --help`
```

## Install choice (summary)

```text
Need TB2 oracle / terminus-2 on Docker?
  └─ pip/uv install harbor (PyPI)          ← default for this repo
Need portage-TEMP fork features?
  └─ clone portage-TEMP; uv sync there     ← do not copy into pheno-harness
```
