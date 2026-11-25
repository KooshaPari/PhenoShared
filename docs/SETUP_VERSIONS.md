# Setup Versions

> Required tool versions for the pheno-harness development environment.
>
> Canonical pins live in `pyproject.toml`, `requirements.txt`, and the
> engine bootstrap config. This file is the **consolidated index** that
> DAG-91 mandates; the per-file sources stay the source of truth.

## Required Tools

| Tool           | Version      | Source                                                 |
|----------------|--------------|--------------------------------------------------------|
| Python         | `>=3.12`     | `pyproject.toml` → `requires-python`                   |
| Node.js        | not pinned   | no `package.json`/`package-lock.json` in repo          |
| Rust           | not pinned   | no `rust-toolchain.toml` in repo                       |
| Xcode / clang  | not pinned   | macOS 14+ assumed (host policy in `AGENTS.md` §2)      |
| uv / pip       | any current  | `uv.lock` is the resolver; `pip>=24` for `pyproject`   |

A `.python-version`, `.nvmrc`, or `.node-version` file is **not** present
in this repo. Python is pinned via `pyproject.toml` only.

## Python Packages

Mirrors `requirements.txt` and `pyproject.toml`. Canonical sources:

- `pyproject.toml` `[project] dependencies`
- `pyproject.toml` `[project.optional-dependencies]`
- `requirements.txt` (flat mirror of core + `harbor` extras)

Core:

| Package        | Pin         |
|----------------|-------------|
| `pyyaml`       | `>=6.0`     |
| `requests`     | `>=2.31`    |

`harbor` extras:

| Package           | Pin        |
|-------------------|------------|
| `harbor`          | `>=0.6.0`  |
| `repo2rlenv`      | `>=0.8.0`  |
| `huggingface_hub` | `>=0.20.0` |

`dev` extras: `pytest>=7.0`.
`shared` extras: `phenotype-shared @ file://../repos/shared`.

## Engines (DAG-91 — WSL/Fedora 44 dual-GPU lane)

Pins for the local inference engines used by `pheno-serve-dev`. These
are the values DAG-91 (`docs/plans/2026-08-05-pheno-harness-WBS-PERT-100.md`
task #91) calls out as the acceptance contract for the WSL/Fedora 44
operator guide.

| Engine | Pin target  | Notes                                              |
|--------|-------------|----------------------------------------------------|
| vLLM   | `0.5.x`     | secondary slot (SGLang preferred per ADR 0006)     |
| SGLang | `0.4.x`     | primary slot on 3090 Ti (per `pheno_serve.yaml`)   |

The engine pins do **not** live in `pyproject.toml` because vLLM and
SGLang are installed via the WSL bootstrap
(`scripts/install_wsl_pheno_serve.sh` +
`scripts/install_wsl_pheno_serve.ps1`) onto the LLM host (§2.2 of
`AGENTS.md`), not the macOS dev workstation.

## Node Packages

There is no `package.json` in this repo, so no Node dependency pins are
tracked here. CI does not require Node. If Node tooling is added later,
add a `package.json` and link it from this section.

## Verifying Your Setup

Run from the repo root:

```sh
# 1. Python interpreter matches the pyproject pin
python3 --version                  # expect Python 3.12.x or newer

# 2. Resolver-level pins are honored
grep -E 'requires-python' pyproject.toml

# 3. Core Python packages are present at-or-above the floor
.venv/bin/python -m pip freeze | grep -E '^(pyyaml|requests|harbor|repo2rlenv|huggingface_hub|pytest)==' \
  || python3 -m pip freeze | grep -E '^(pyyaml|requests|harbor|repo2rlenv|huggingface_hub|pytest)=='

# 4. Engines (on the LLM host, not this Apple Silicon dev workstation)
vllm --version                     # expect 0.5.x
python3 -c "import sglang; print(sglang.__version__)"   # expect 0.4.x
```

Any drift means re-bootstrap from the pinned source (see References).

## References

- `AGENTS.md` §2 (hosts) and §6 (cron) — host + scheduler context.
- `pyproject.toml` — canonical Python package pins + `requires-python`.
- `requirements.txt` — flat pip mirror of core + `harbor` extras.
- `renovate.json` — automated dependency-update policy.
- `docs/plans/2026-08-05-pheno-harness-WBS-PERT-100.md` — DAG-91 entry:
  *"add `documentation` for vLLM 0.5 + SGLang 0.4 version pins"*.
- `scripts/install_wsl_pheno_serve.sh`,
  `scripts/install_wsl_pheno_serve.ps1` — WSL/Fedora 44 engine bootstrap.
- `docs/guides/INSTALL.md` — install runbook (extras + shared wheel).
- `docs/adrs/0006-pheno-serve-dev-bootstrap.md` — local-serving decision
  (SGLang primary, vLLM secondary on the 3090 Ti).
