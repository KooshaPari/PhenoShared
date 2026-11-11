# ADR 0001: Keep tray, menubar, and auto-update outside the current product scope

- Status: Accepted
- Date: 2026-07-10
- Decision owners: SessionLedger maintainers
- Related: `docs/ops/distribution.md`, `docs/ops/update-check.md`, issue #66

## Context

SessionLedger currently has two explicit runtime surfaces:

1. `sl-daemon`, which watches, compiles, stores, and serves session data.
2. `sl-viewer`, a user-launched desktop viewer for inspecting that data.

The product does not install a persistent desktop companion, claim ownership of
login startup, or require an always-running GUI process. Release artifacts are
portable and unsigned. Users can stop either process independently and remove
the extracted files without an installer-managed lifecycle.

Tray/menubar controls would introduce a third lifecycle surface whose primary
value is controlling a background application. SessionLedger already exposes
daemon health and operations through its HTTP API, CLI, and process-compose
workflow. A tray process would duplicate those controls while adding
platform-specific startup, permissions, icon state, crash recovery, and support
requirements.

Automatic updates would also create a trust boundary that the current unsigned
portable distribution does not satisfy. A safe updater needs signed update
metadata, signed platform binaries, rollback behavior, atomic replacement, and
clear coordination between the daemon and viewer. Downloading and replacing an
unsigned executable in the background would weaken the explicit checksum and
release-verification model.

## Decision

Tray integration, a macOS menubar companion, and automatic background updates
are **Soft / Not Applicable** for the current daemon-plus-viewer product.
Their absence is intentional product scope, not a missing requirement for the
portable release channel.

Updates remain user-initiated: users choose a GitHub Release, verify published
checksums (and the Sigstore bundle when available), stop the running viewer, and
replace the extracted binary. The repository may provide packaging and install
helpers, but those helpers must not imply a resident agent or silent updater.

**C11 L111:** operators may run `sl-daemon check-update` to compare the installed
version against the latest GitHub Release tag. That command is check-only — it
does not download or install updates. See [`docs/ops/update-check.md`](../ops/update-check.md).

## Consequences

- The viewer remains a conventional foreground application with no login item.
- The daemon remains independently managed by CLI, service tooling, or
  process-compose.
- Packaging work can focus on reproducible archives, checksums, signing, and
  installers without coupling it to a tray process.
- Users do not receive in-app update prompts or silent security updates; release
  notes and the GitHub Releases channel are the update notification path.

## Reconsider when

Revisit this decision only when at least one of these becomes a committed
product requirement:

- SessionLedger ships an installed, user-facing background service that needs
  discoverable desktop controls.
- User research shows that daemon status/control through existing interfaces is
  a material adoption blocker.
- Platform signing and notarization are active, and the release process can
  provide signature-verified update metadata, rollback, and atomic replacement.

Any proposal should separately justify tray/menubar UX and auto-update security;
shipping one does not automatically require the other.
