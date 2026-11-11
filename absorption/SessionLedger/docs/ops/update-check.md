# User-initiated update check (C11 L111)

Operational guide for checking whether a newer SessionLedger release exists on
GitHub. This path is **check-only** — it does not download, install, or replace
binaries. Automatic background updates remain out of scope per
[ADR 0001](../adr/0001-desktop-companion-scope.md).

## Posture (ADR 0001)

| Capability                                                  | Status           |
| ----------------------------------------------------------- | ---------------- |
| Auto-update / silent binary replacement                     | **Out of scope** |
| In-app update prompts                                       | **Out of scope** |
| User-initiated release availability check                   | **Active**       |
| Manual install from GitHub Releases + checksum verification | **Active**       |

When an update is available, operators still follow the manual path:

1. Stop running `sl-daemon` / `sl-viewer` processes.
2. Download the intended release archive from GitHub Releases.
3. Verify `SHA256SUMS` (and `SHA256SUMS.sigstore.json` when present).
4. Replace extracted binaries deliberately — no background agent performs this step.

See [`distribution.md`](distribution.md#release-integrity-signing-cosign) for
integrity verification and [`packaging/channels.md`](../../packaging/channels.md)
for install channels (`curl`/`irm`, portable archives, MSI/PKG).

## CLI: `sl-daemon check-update`

Compare the installed `sl-daemon` version (`--version` / `CARGO_PKG_VERSION`)
against the latest GitHub Release tag for the canonical repository.

```bash
sl-daemon check-update
sl-daemon check-update --json
sl-daemon check-update --repo KooshaPari/SessionLedger
```

### Exit codes

| Code | Meaning                                                       |
| ---- | ------------------------------------------------------------- |
| `0`  | Installed version is at or above the latest published release |
| `1`  | A newer release tag exists on GitHub                          |
| `2`  | Network, parse, or usage error                                |

### Output

Human-readable (default):

```text
update available: sl-daemon 0.1.0 → v0.2.0
Download from https://github.com/KooshaPari/SessionLedger/releases/tag/v0.2.0
Verify SHA256SUMS (and Sigstore bundle when present) before replacing binaries.
```

JSON (`--json`):

```json
{
  "status": "update_available",
  "installed": "0.1.0",
  "latest": "v0.2.0"
}
```

### Offline / hermetic testing

For CI and local smoke without network access, pin the latest tag:

```bash
sl-daemon check-update --latest v0.2.0
# or
SL_CHECK_UPDATE_LATEST=v0.2.0 sl-daemon check-update
```

## SelfCheck (machine proof)

Docs + script anchors only — no GitHub network required:

```powershell
pwsh ./scripts/update-check-check.ps1 -SelfCheck
```

Hermetic Rust wrapper:

```bash
cargo test --test update_check --locked
```

Blocking CI also runs `sl-daemon` unit tests and a CLI smoke with `--latest`.

## Related

- [ADR 0001 — tray/menubar/auto-update scope](../adr/0001-desktop-companion-scope.md)
- [`distribution.md`](distribution.md) — release channels and integrity verification
- [`scripts/install.ps1`](../../scripts/install.ps1) / [`scripts/install.sh`](../../scripts/install.sh) — manual pinned installs
