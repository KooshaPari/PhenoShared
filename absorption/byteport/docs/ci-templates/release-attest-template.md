# SC4 Provenance Metadata Template

> **Source audit:** `FLEET-AUDIT-REPORT.md` — SC4 (build provenance metadata) is the last of the 6 biggest P0 pillars (priority 30, 10/11 repos at score 0).
> **Method:** Enhance the S8 release workflow to publish provenance to the GitHub attestations API. The attestation becomes queryable via `gh attestation verify` and visible on the repo's "Attestations" tab.
> **How to use:** Modify the existing `.github/workflows/release-attest.yml` (added by the S8 wave) to use the official `actions/attest-build-provenance` action which automatically publishes to the GitHub attestations API. Lifts SC4 from 0 to 2 (wired).

## What is SC4?

SC4 (build provenance metadata) = the SLSA Build provenance attestation is published in a discoverable location with metadata (build timestamp, source repo, workflow run, etc.). The GitHub attestations API satisfies this: every attestation has a `gh attestation verify <artifact>` URL and a transparency log entry.

**The "wired" (SC4=2) signal**: the S8 release workflow uses the official `actions/attest-build-provenance` action (not a custom one). The attestation is queryable via the repo's "Attestations" tab.

**The "measured" (SC4=3) signal** (OmniRoute has this): the attestation is also published to a transparency log (e.g., Rekor via sigstore), and a CI gate re-verifies the latest 10 releases nightly.

## Template: enhanced release-attest.yml

Replace the S8 template's `Attest build provenance` step with the official GitHub Action. Here's the enhanced version:

```yaml
name: Release + SLSA Build Attestation

on:
  push:
    tags:
      - "v*"
  workflow_dispatch:
    inputs:
      version:
        description: "Release version (e.g., v1.6.8)"
        required: true
        type: string

permissions:
  contents: read
  id-token: write
  attestations: write  # required for SC4 — grants the action access to write attestations

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  build:
    name: Build + Attest
    runs-on: ubuntu-24.04
    steps:
      - name: Checkout
        uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2

      - name: Build artifact
        # Replace with your actual build step.
        # For Rust: `cargo build --release`
        # For Python: `python -m build`
        # For Node: `npm run build`
        # For Go: `go build -o dist/ ./...`
        run: |
          echo "TODO: replace with your build"
          mkdir -p dist
          echo "build artifact" > dist/artifact

      - name: Attest build provenance (SC4 wired signal)
        # The official GitHub Action for SLSA Build L3 provenance.
        # Pin to a specific SHA from https://github.com/actions/attest-build-provenance/releases
        # v1.3.0 = 35a8f9717e7a2adb1c2c3b2ac88961ba9c230e98
        uses: actions/attest-build-provenance@e8998f949152b193b063cb0ec769d69d929409be # v2
        with:
          subject-name: ${{ github.repository }}
          subject-digest: sha256:$(sha256sum dist/artifact | awk '{print $1}')
          push-to-registry: false  # SC4 wired: just publish to GitHub attestations API

      - name: Upload artifact
        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02 # v4
        with:
          name: ${{ github.event.inputs.version || github.ref_name }}-artifact
          path: dist/
```

## How to apply

1. **Find the existing release-attest.yml** that the S8 wave added to your repo.
2. **Replace** the `Attest build provenance` step with the official `actions/attest-build-provenance` action.
3. **Add `attestations: write`** to the `permissions:` block (already present in the S8 template, but verify).
4. Pin SHAs:
   - `actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd`
   - `actions/attest-build-provenance@35a8f9717e7a2adb1c2c3b2ac88961ba9c230e98` (v1.3.0)
   - `actions/upload-artifact@65c4c4a1ddee5b72f698fdd0de8ccd5686b70862` (v4.6.0)
5. **Commit + push + open a PR.**

## SC4 score lift

- **0 → 1 (ad-hoc):** attestation is produced but not via the official action.
- **0 → 2 (wired):** the official `actions/attest-build-provenance` action is used; the attestation is published to the GitHub attestations API.
- **0 → 3 (measured):** the attestation is also published to a transparency log (Rekor via sigstore), and a CI gate re-verifies the latest 10 releases nightly.

## Reference: OmniRoute

OmniRoute is the reference repo for SC4 (SC4=3). Its `release.yml` has `id-token: write` + `attestations: write` + a release flow that publishes provenance to the GitHub attestations API and to Rekor. The template above is a minimal extraction of that pattern.

## How to validate

After applying:
1. `git tag v0.0.1-test && git push --tags` to trigger the workflow
2. GitHub UI → repo → "Insights" tab → "Attestations" should show the new attestation
3. `gh attestation verify dist/artifact` (local CLI) should pass

## Provenance

- **Template version:** 1.0
- **Author:** Phenotype Org holistic audit, 2026-06-16
- **Audit that produced it:** `FLEET-AUDIT-30-PILLAR.md` (SC4 P0)
- **Reference repo:** `KooshaPari/OmniRoute` (SC4=3)
- **License:** Same as the parent repo
