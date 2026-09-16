# Publishing pheno-harness

## Layout: split repos (active)

| Repo | URL | Contents |
|------|-----|----------|
| **pheno-harness** | https://github.com/<REDACTED>/pheno-harness | Code, config, eval, scripts |
| **pheno-specs** | https://github.com/<REDACTED>/pheno-specs | AgilePlus SPEC-001–016, research digest |

Specs mount as git submodule at `agileplus-specs/`. Pin in `specs.lock`.

### Clone with specs

```bash
git clone --recurse-submodules https://github.com/<REDACTED>/pheno-harness.git
# or after plain clone:
git submodule update --init --recursive
```

```powershell
git clone --recurse-submodules https://github.com/<REDACTED>/pheno-harness.git
# or after plain clone:
git submodule update --init --recursive
```

### Bump spec pin

```bash
cd agileplus-specs
git pull origin main
cd ..
git rev-parse HEAD:agileplus-specs  # update specs.lock ref
git add agileplus-specs specs.lock
git commit -m "Bump pheno-specs submodule"
```

## pheno-harness contents

| Path | Purpose |
|------|---------|
| `agileplus-specs/` | Submodule → pheno-specs |
| `config/` | Runtime YAML/JSON |
| `scripts/` | Operator automation |
| `eval/`, `verifier/`, `traces/` | Measurement and RLVR |
| `specs.lock` | Pinned spec commit |

## First publish checklist

1. Review `.gitignore` — no secrets, no `jobs/` Harbor artifacts.
2. Copy ChatGPT exports to `pheno-specs/sources/raw/` (in specs repo).
3. Verify `specs.lock` matches submodule HEAD.
4. Push both repos; tag `v0.1.0-spec-baseline` on pheno-specs.

```powershell
# pheno-specs (specs only)
cd C:\Users\koosh\pheno-specs
git tag v0.1.0-spec-baseline
git push origin v0.1.0-spec-baseline

# pheno-harness (code + submodule pointer)
cd C:\Users\koosh\pheno-harness
git push -u origin main
git tag v0.1.0-harness-baseline
git push origin v0.1.0-harness-baseline
```

## What stays local (not in git)

- `~/.omniroute/storage.sqlite` and training JSONL
- `~/forge/.credentials.json`
- `jobs/harbor/` TB2 run artifacts
- GGUF weight paths (`PHENO_*` env vars)

## Continuation workflow for new machines

1. `git clone --recurse-submodules` pheno-harness (or `git submodule update --init --recursive`)
2. Install OmniRoute + Forge; restore credentials locally
3. `uv pip install -e ".[harbor,dev]"` (or `pip install -r requirements.txt` + editable install) — see [docs/guides/INSTALL.md](guides/INSTALL.md)
4. Read `AGENTS.md` + `agileplus-specs/index/spec.md`
5. Smoke: `bash scripts/smoke_install.sh`
6. Phase 0: `bash scripts/install_phase0.sh` or `.\scripts\install_phase0.ps1`
7. Docker for Harbor TB2 (wrappers under `harbor/` are Windows `.ps1`; Unix: `harbor run …`)

## License

Add `LICENSE` before public publish.
