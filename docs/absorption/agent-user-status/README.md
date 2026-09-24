# Absorption — <REDACTED>/agent-user-status → phenotype-tooling/crates/agent-user-status

**Status:** ABSORBED 2026-07-17
**Source repo:** `<REDACTED>/agent-user-status` @ `112287548359ba5c18ff1e7b047c8334f050532f` (2026-06-20)
**Absorbing repo:** `<REDACTED>/phenotype-tooling`
**Absorbing branch:** `salvage/phenotype-tooling-workspace-2026-07-15`
**Absorbing commit:** `29ce5dd4d7baecd4920e5ccedca744eee5422a10`
**Registry row:** `repo-agent-user-status` flipped `AFFIRM/active` → `ABSORB/absorbed`
**Source archive status:** `isArchived=true` (verified via `gh repo view` post-`gh repo archive -y`)

## Source profile

- 615 KB Python project, primary language Python (`>=3.12`), license MIT
- 35 Python source files (`src/agent_user_status/`) + 1 stdio MCP server (`src/mcp/`)
- 12 Swift files in `src/native/macos/` (native monitor bundle, NOT a Swift Package workspace root)
- 6 installable console scripts: `agent-user-status`, `agent-imessage`, `agent-user-statusd`,
  `agent-user-status-cursor-tracker`, `agent-user-status-webcam-eye-tracker`, `agent-imessage-mcp`
- 91 pytest unit tests in `tests/unit/`
- Zero required runtime deps; macOS webcam tracker is an optional `[eye]` extra
  (mediapipe/numpy/opencv-contrib-python/pyobjc-framework-Cocoa)

## Why phenotype-tooling

The original auto-generated audit pointed at `<REDACTED>/Agentora` (Rust agent-orchestration
workspace), but the Python source cannot embed in Agentora without breaking its `[workspace]`
semantics. `phenotype-tooling` already hosts Python subpackages via the `crates/phench`
precedent — Python package embedded under `crates/` WITHOUT registering in
`[workspace.members]`. The source's purpose (local user-status / iMessage / MCP-server
runtime for coding agents) is a developer-tooling concern.

## Verification

- `python3 -m compileall -q src/` → exit 0
- `python3 -c "import agent_user_status.bootstrap, agent_user_status.statusd,
  agent_user_status.agent_imessage"` → OK on Python 3.14.6
- `python3 -m pytest tests/ -q` → **91 passed in 6.40s**
- `agent_user_status.cursor_tracker` correctly fails on non-macOS hosts because
  `pyobjc-framework-Cocoa` is macOS-only (listed under `[eye]` optional extra)

## Restore command

```bash
gh repo clone <REDACTED>/agent-user-status /tmp/agent-user-status-restore
```

## Audit / boundary references

- `audits/absorption-justifications/agent-user-status-2026-07-17.md` (registry-side)
- `docs/boundary/agent-user-status.md` (boundary doc — to follow)
- `crates/agent-user-status/ABSORPTION.md` (target-side provenance marker)

## Verification status (2026-09-24)

The destination is **cross-repo**: `absorbing_repo` is `KooshaPari/phenotype-tooling`,
not this tree. The registry row wrote `absorbing_path` repo-relative
(`crates/agent-user-status/`), which `scripts/audit/registry-invariant.sh` reads
as a local-path claim and therefore flags as a violation. The field is now
repo-qualified (`phenotype-tooling/crates/agent-user-status/`) — the gate's
`external_qualified` form for "that repo, this path" — which classifies it
**unverifiable** (counted, non-gating). It is NOT marked OK: the gate cannot
test another repo's tree from here.

Best-available evidence, from the sibling clone `../phenotype-tooling` whose
refs are current to `origin/main` 2026-09-14:

- `git log --all -- crates/agent-user-status` returns nothing — no fetched ref
  has ever touched that path.
- Claimed absorbing commit `29ce5dd4d7baecd4920e5ccedca744eee5422a10` is absent
  from the clone.
- Branch `salvage/phenotype-tooling-workspace-2026-07-15` is absent.
- The target-side provenance marker `crates/agent-user-status/ABSORPTION.md`
  listed under "Audit / boundary references" above does not exist there.
- `origin/main`'s 2026-07-14..07-20 window contains only dependency bumps — no
  salvage merge.

`git fetch` on 2026-09-24 returns `Repository not found` over SSH: the deploy
key is scoped to PhenoShared only (see `docs/absorption/ABSORPTION-LINEAGE.md`
§2.3), which makes a private-but-intact repo indistinguishable from a deleted
one from this host.

**Consequence:** the absorption claim is currently contradicted by the best
available proxy but not provable either way. It stays in the unverifiable
bucket and closes only on account-wide GitHub credentials (re-auth `gh`, or an
account-level SSH key), after which one `git ls-remote` + `git fetch` settles it.

**End of absorption record.**
