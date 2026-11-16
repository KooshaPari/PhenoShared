# Python Ecosystem Audit

**Date:** 2026-05-05
**Scope:** `/Users/<REDACTED>/CodeProjects/Phenotype/repos`
**Repos scanned:** 23 Python repos with `pyproject.toml`

---

## AUDIT 1: Python Repos Inventory

### Repo Summary Table

| Repo | Python | tests/ | pytest | CI Workflows | mypy | ruff | pre-commit |
|------|--------|--------|--------|-------------|------|------|------------|
| agent-user-status | >=3.12 | yes | no | 6 | no | no | no |
| agileplus-mcp | >=3.12 | yes | yes | 1 | yes | yes | no |
| AuthKit | ? | yes | no | 10 | no | no | no |
| cheap-llm-mcp | >=3.12 | yes | yes | 10 | no | no | no |
| dispatch-mcp | >=3.13 | yes | yes | 1 | no | no | no |
| helios-router | >=3.12 | yes | yes | 16 | yes | yes | no |
| heliosBench | >=3.12 | yes | yes | 6 | no | yes | no |
| helioscope | >=3.14 | yes | yes | 54 | yes | yes | no |
| Httpora | >=3.12 | yes | yes | 7 | no | yes | no |
| McpKit | ? | yes | no | 6 | no | no | no |
| Parpoura | >=3.14 | yes | yes | 14 | yes | yes | no |
| phenodocs | >=3.14 | yes | no | 15 | no | no | yes |
| phenodocs-scorecard-remediation | >=3.14 | **no** | **no** | 15 | no | no | yes |
| PhenoMCP | >=3.14 | yes | no | 11 | no | no | no |
| phenoResearchEngine | >=3.10 | yes | no | 11 | no | no | no |
| PhenoRuntime | >=3.14 | yes | no | 16 | no | no | no |
| phenotype-omlx | >=3.10 | yes | yes | 4 | yes | yes | no |
| PolicyStack | ? | yes | no | 18 | no | no | no |
| portage | >=3.12 | yes | no | 29 | no | yes | no |
| python | >=3.14 | yes | no | 1 | no | no | no |
| QuadSGM | >=3.13 | yes | yes | 20 | yes | yes | no |
| thegent | >=3.13 | yes | yes | 25 | yes | yes | no |
| Tracera | >=3.13 | yes | yes | 38 | no | yes | no |

### Findings

- **8 repos lack pytest** in dependencies despite having `tests/` directories: `agent-user-status`, `AuthKit`, `McpKit`, `phenodocs`, `PhenoMCP`, `phenoResearchEngine`, `PhenoRuntime`, `PolicyStack`
- **1 repo has no tests dir at all**: `phenodocs-scorecard-remediation` (tooling/scripts repo, tests not expected)
- **6 repos use mypy** for type checking: `agileplus-mcp`, `helios-router`, `helioscope`, `Parpoura`, `phenotype-omlx`, `QuadSGM`, `thegent`
- **2 repos use pyright**: `QuadSGM`, `thegent`
- **uv.lock present in 15 repos** (modern lock file). No requirements.txt in most — uv is the dominant package manager.

---

## AUDIT 2: Security Scan — Vulnerability Patterns

### eval() Findings

| Repo | eval() Count | Type | Risk |
|------|-------------|------|------|
| phenotype-omlx | ~50 | `mx.eval()` (MLX framework) | **None** — framework call |
| phenotype-omlx | 1 | `embedding.py:353` comment | **None** — in comment |
| portage | ~10 | `ast.literal_eval()` | **None** — safe |
| portage | ~30 | `llm_eval()` function name | **None** — not Python eval() |
| QuadSGM | ~3 | test fixtures with hardcoded strings | **Low** |
| thegent | 0 | `record_eval()` method name | **None** — false positive grep |
| Tracera | 4 | `frontend/node_modules/gyp/input.py` | **Moderate** — vendored third-party |

**Confirmed unsafe eval() locations:**

1. `Tracera/frontend/node_modules/node-gyp/gyp/pylib/gyp/input.py:237` — uses `eval(build_file_contents, {"__builtins__": {}}, None)` on arbitrary file contents. **This is vendored third-party code** (`node-gyp`), not project code. The eval has restricted builtins but still evaluates untrusted data.
2. `Tracera/frontend/node_modules/node-gyp/gyp/pylib/gyp/input.py:902` — `eval(contents)` on matched gyp build file content.

### Shell Injection Findings

- `portage/adapters/coding/usaco/template/tests/judges/usaco_utils.py:357` — sets `os.system = None` as a **sandboxing measure** for test isolation. This is intentional and safe. The `os.environ` assignment above it is also benign.

### subprocess() Findings (High Volume — Needs Review)

| Repo | subprocess refs | Files | Note |
|------|----------------|-------|------|
| thegent | 2145+ | 60+ | Largest user; test harnesses, CLI wrappers |
| portage | 287 | many | Benchmark runner, test fixtures |
| Tracera | 266 | many | Build/test harnesses |
| helioscope | 126+ | many | Dev tooling, npm builds |
| PolicyStack | 95+ | many | CLI wrappers |
| phenotype-omlx | 73+ | many | Build scripts |
| helios-router | 56+ | many | Benchmark runners |
| agent-user-status | 118+ | many | MCP tool wrappers |

**Most subprocess usage is in test/benchmark/build tooling.** Review the following production-use subprocess calls for shell injection risk:
- `helioscope/install_native_deps.py` — runs system package installation commands
- `PolicyStack/policy_lib.py` — runs linting/validation commands
- `portage/harbor/` — runs benchmark execution commands

---

## AUDIT 3: Dependency Staleness

**Note:** pip-based staleness checks were not run (would require per-repo virtualenv activation). Static analysis findings:

- **phenodocs-scorecard-remediation** — `dependencies = []`, no runtime deps. Only pre-commit in dev.
- **dispatch-mcp** — pins exact upper bounds (`mcp>=1.0.0,<1.2.0`, `httpx>=0.27.0,<0.29.0`). Good practice.
- **phenodocs** — uv-managed. `agents.lock`, `uv.lock`, `bun.lock` present — three package managers in one repo.
- **phenodocs-scorecard-remediation** — same three lock files, uv with no deps.
- **helioscope** — has `flake.lock` (Nix), `uv.lock`, `Cargo.lock`, `MODULE.bazel.lock` — four lock files.

### Dependency Tool Fragmentation Risk

Repos using 3+ package managers/lock files:
- `phenodocs` — uv, bun, agents
- `phenodocs-scorecard-remediation` — uv, bun, agents
- `Tracera` — uv, bun
- `thegent` — uv, bun
- `helioscope` — uv, Cargo, Nix, Bazel

---

## AUDIT 4: Type-Checking Coverage

| Repo | mypy | pyright | Status |
|------|------|---------|--------|
| agileplus-mcp | yes | no | strict mypy |
| helios-router | yes | no | strict mypy |
| helioscope | yes | no | strict mypy |
| Parpoura | yes | no | strict mypy |
| phenotype-omlx | yes | no | strict mypy |
| QuadSGM | yes | yes | dual type checking |
| thegent | yes | yes | dual type checking |
| (rest) | no | no | **No type checking** |

**Coverage gap:** 16 of 23 Python repos have no type checking at all. These include high-activity repos like `heliosBench`, `Httpora`, `PolicyStack`, `portage`, `Tracera`, `phenoResearchEngine`.

---

## Risk Summary

| Severity | Finding | Affected Repos |
|----------|---------|---------------|
| High | No pytest despite tests/ dir | agent-user-status, AuthKit, McpKit, phenodocs, PhenoMCP, phenoResearchEngine, PhenoRuntime, PolicyStack |
| Medium | vendored `eval()` on untrusted data (third-party) | Tracera (node-gyp) |
| Medium | No type checking (16 repos) | See table above |
| Low | subprocess in production code (shell injection surface) | helioscope, PolicyStack, portage, helios-router |
| Low | eval() in test fixtures (controlled inputs) | QuadSGM, thegent, Parpoura |
| Info | uv + bun + agents lock fragmentation | phenodocs, phenodocs-scorecard-remediation |
| Info | 8+ repos missing ruff (linting) | agent-user-status, AuthKit, cheap-llm-mcp, dispatch-mcp, McpKit, PhenoMCP, phenoResearchEngine, PhenoRuntime, PolicyStack, python |
