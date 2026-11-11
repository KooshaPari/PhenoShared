# SessionLedger Contributing Guide

## Prerequisites

- Rust stable toolchain (latest stable)
- Cargo (bundled with Rust)
- pre-commit for local repository hooks

## Build

```bash
cargo build
```

## Testing

**IMPORTANT**: sl-daemon must be tested in isolation because sl-viewer depends on webkit2gtk-sys which cannot resolve on macOS. Run:

```bash
cargo test -p sl-daemon
```

Property tests run with the normal root test suite. Before submitting changes to
dedup, merge, ingestion, or OKF code, repeat the focused suite locally:

```bash
for run in 1 2 3; do PROPTEST_CASES=64 cargo test --test properties; done
```

A failed test is not retried to turn CI green. Preserve the proptest seed or
regression case from the failure output, open an issue for any confirmed flake,
and quarantine a test only with an owner, linked issue, and removal deadline.
The CI repeat is a short detection signal; it does not replace a root-cause fix.
Use the [flake tracker](docs/ops/flake-tracker.md) to record confirmed flakes
and any temporary quarantine.

The `fuzz-smoke` CI job runs the committed corpus for 10 seconds per target.
Soft sustained cadence (nightly / dispatch, 120 s / target) and crash corpus
triage live in [`docs/ops/fuzz-cadence.md`](docs/ops/fuzz-cadence.md). Longer
local campaigns use `cargo fuzz run okf_roundtrip` (or `jsonl_ingest`).

## Native WebView accessibility smoke

After a desktop viewer change that affects landmarks, status regions, Help, or
Search recovery, run the checklists in
[`docs/a11y/status-regions-and-native-smoke.md`](docs/a11y/status-regions-and-native-smoke.md)
and [`docs/a11y/screen-reader-smoke.md`](docs/a11y/screen-reader-smoke.md), then
record a machine-readable pass:

```powershell
# Prefer a worktree-local target when building the viewer in parallel lanes:
$env:CARGO_TARGET_DIR = "$PWD/target-w23-c09"
# cargo run -p sl-viewer … (desktop feature) — exercise the checklist, then:
pwsh -NoProfile -File scripts/record-native-webview-smoke.ps1 `
  -Outcome pass `
  -ScreenReader NVDA `
  -OutPath docs/ops/fixtures/native-webview-smoke.local.json

# Optional: attach to a running daemon for live-daemon parity probes
# (see docs/a11y/status-regions-and-native-smoke.md#live-daemon-native-webview-parity):
pwsh -NoProfile -File scripts/record-native-webview-smoke.ps1 `
  -Outcome pass `
  -AttachDaemon `
  -DaemonUrl http://127.0.0.1:8080 `
  -ScreenReader NVDA `
  -OutPath docs/ops/fixtures/native-webview-smoke.local.json
```

Commit only intentional evidence under audit packages; keep
`native-webview-smoke.local.json` untracked unless an audit asks for it. The
checked-in sample is
[`docs/ops/fixtures/native-webview-smoke.sample.json`](docs/ops/fixtures/native-webview-smoke.sample.json).

## Inclusive Language Checks

Run the lightweight seed gate before documentation-heavy changes:

```powershell
pwsh -NoProfile -File scripts/inclusive-language-check.ps1
```

The script scans Markdown under `docs/` plus `CONTRIBUTING.md` for a small
deny-list. It is intentionally dependency-free so CI can add it as a warning or
blocking check later.

Vale is also configured as a warning-level style for the same scope. After
installing Vale locally, run:

```powershell
vale docs CONTRIBUTING.md
```

Use the PowerShell script as the seed gate today. Upgrade the Vale style over
time with project-specific substitutions, then wire `vale docs CONTRIBUTING.md`
into CI as an optional warning before making it blocking.

## Local Hooks

Install local hooks once per checkout:

```bash
pre-commit install
```

The hook set includes gitleaks secret scanning for staged changes. CI also runs
TruffleHog alongside gitleaks in [`.github/workflows/security.yml`](.github/workflows/security.yml).
To run gitleaks manually before committing, stage the intended files and run:

```bash
pre-commit run gitleaks
```

When changing environment documentation, keep [`.env.example`](.env.example)
complete for local runtime keys (including the `SL_API_KEY` placeholder) and
run the light gate:

```powershell
pwsh -NoProfile -File scripts/env-example-check.ps1
```

Do not commit real API keys. Secret rotation and header handling are summarized
in [`SECURITY.md`](SECURITY.md#api-keys-and-secret-rotation).

## Shell completions (sl-daemon)

`sl-daemon` uses `clap_complete`. Committed scripts live in
[`crates/sl-daemon/completions/`](crates/sl-daemon/completions/) (bash, zsh,
fish, PowerShell). After changing the CLI surface, regenerate them:

```bash
cargo run -p sl-daemon -- completions bash > crates/sl-daemon/completions/sl-daemon.bash
cargo run -p sl-daemon -- completions zsh > crates/sl-daemon/completions/_sl-daemon
cargo run -p sl-daemon -- completions fish > crates/sl-daemon/completions/sl-daemon.fish
cargo run -p sl-daemon -- completions powershell > crates/sl-daemon/completions/sl-daemon.ps1
```

Install into your shell:

```bash
sh scripts/install-sl-daemon-completions.sh zsh
pwsh -NoProfile -File scripts/install-sl-daemon-completions.ps1 -Shell powershell
```

Top-level and subcommand `--help` output includes richer examples (`serve`,
`export`, `search`, `tag`, `archive`, `restore`, `replay`, `validate`,
`completions`). See [`crates/sl-daemon/README.md`](crates/sl-daemon/README.md#shell-completions).

## Branch Discipline

- Always create feature branches off main
- Never commit directly to main
- Use conventional-commits style for commit messages

## PR Workflow

- Create one focused PR per change
- Ensure all tests pass (0-failed)
- Verify no regressions
- CI runs Linux-only (per billing constraints)
- Reference the existing [qgate.yml](.github/workflows/qgate.yml) quality gate
- The reusable `quality-gate.yml` call is pinned to a phenotype-tooling commit
  SHA (not `@main`); see [docs/ops/qgate-pin.md](docs/ops/qgate-pin.md) before
  bumping the pin

## Developer Certificate of Origin (DCO)

All contributions must be signed off under the [Developer Certificate of Origin](https://developercertificate.org/).
Each commit must include a `Signed-off-by:` trailer matching the commit author:

```bash
git commit -s -m "your message"
```

By signing off, you certify that you have the right to submit the work under this
repository's dual MIT OR Apache-2.0 license. PRs should confirm the DCO checkbox
in the pull request template.

## Cryptographic commit signing (GPG / SSH)

DCO sign-off is **not** a substitute for Git commit signatures. Configure signing
before your first commit on a feature branch:

**GPG**

```bash
git config --global user.signingkey <KEY_ID>
git config --global commit.gpgsign true
git commit -S -s -m "your message"
```

**SSH** (Git 2.34+)

```bash
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519_sign.pub
git config --global commit.gpgsign true
git commit -S -s -m "your message"
```

Publish your public key to GitHub (GPG key or SSH **signing** key). Maintainers
enable **Require signed commits** on `main`; see
[`docs/ops/commit-signing.md`](docs/ops/commit-signing.md) and
[ADR 0004](docs/adr/0004-commit-signing-policy.md).

Verify locally:

```powershell
pwsh -NoProfile -File scripts/commit-signing-check.ps1 -Ref HEAD -Count 5
```

## Source provenance (signed commits + CODEOWNERS)

SessionLedger's **source provenance** policy SSOT covers cryptographic commit
signatures, [`CODEOWNERS`](CODEOWNERS) review expectations, and human org gates
(branch protection, maintainer 2FA) that cannot be verified from checkout alone.
See [`docs/ops/source-provenance.md`](docs/ops/source-provenance.md).

Hermetic policy smoke (no GitHub API):

```powershell
pwsh -NoProfile -File scripts/source-provenance-check.ps1 -SelfCheck
pwsh -NoProfile -File scripts/branch-protection-check.ps1 -PolicyOnly
```

Live branch protection remains a maintainer Settings control; the scripts above
document anchors and do not claim org Settings are enforced from the tree.

## Maintainer 2FA (org hygiene)

Merge-capable maintainers must use GitHub **2FA** and prefer hardware security keys.
Policy and the human attestation path:
[`docs/ops/maintainer-2fa.md`](docs/ops/maintainer-2fa.md).
Org enforcement cannot be verified from checkout; local docs smoke:

```powershell
pwsh -NoProfile -File scripts/maintainer-2fa-check.ps1 -SelfCheck
```

## Governance

This repository follows governance guidelines defined in ~/.claude/CLAUDE.md at a high level.
