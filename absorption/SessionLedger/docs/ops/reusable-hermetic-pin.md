# Reusable hermetic build workflow pin

SessionLedger calls the in-repo reusable hermetic build slice from
[`.github/workflows/hermetic.yml`](../../.github/workflows/hermetic.yml).

## Current pin

| Field                        | Value                                                                                                                                   |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Workflow                     | `KooshaPari/SessionLedger/.github/workflows/reusable-hermetic-build.yml`                                                                |
| Commit SHA                   | `042c46e74751a378097086bcc89942dfa4bf4b04`                                                                                              |
| Caller job                   | `hermetic.yml` → `sl-daemon-offline-container`                                                                                          |
| `builder_image_digest` input | `sha256:16381cf25d89fd5dc8a904ff4a7b8d4660a856ed9738b8a7e879d816439ce2a5` (must match [`hermetic-builder.json`](hermetic-builder.json)) |

The `uses: …@<sha>` ref must be a full 40-character commit SHA. Do not use
`@main`, branch names, or moving tags. The digest input must match the immutable
GHCR manifest recorded in `hermetic-builder.json`.

## Caller provenance contract

1. **Workflow definition pin** — `hermetic.yml` calls
   `reusable-hermetic-build.yml` at the SHA recorded in this document so the
   isolated container rebuild steps are an immutable supply-chain input.
2. **Builder image pin** — the `builder_image_digest` workflow input must equal
   `hermetic-builder.json` → `builder_image_digest` (also mirrored in
   `reusable-hermetic-pin.json`).
3. **SelfCheck** — `scripts/reusable-provenance-check.ps1 -SelfCheck` asserts
   the pin table, caller wiring, and reusable workflow body stay aligned without
   cargo or network.

This is partial reusable-workflow provenance evidence (C06 L53). It does **not**
claim SLSA Build Level 3 signing for nested workflow calls or protected release
Environments.

## Bump procedure

1. Merge changes to `.github/workflows/reusable-hermetic-build.yml` on `main`.
2. Copy the merge commit's full SHA into:
   - `jobs.sl-daemon-offline-container.uses` in `.github/workflows/hermetic.yml`
   - the table above and `docs/ops/reusable-hermetic-pin.json` → `workflow_commit_sha`
3. If the GHCR builder digest changed, update `builder_image_digest` in
   `hermetic-builder.json`, the caller `with:` block, and this document.
4. Run `pwsh ./scripts/reusable-provenance-check.ps1 -SelfCheck` before merge.
