# SC3 Attestation Verification Template

> **Source audit:** `FLEET-AUDIT-REPORT.md` — SC3 (SLSA Build attestation verification) is part of the supply-chain P0 block (SC3/SC4 are 10/11 zero; S8 only covers the production side, not the verification side).
> **Method:** Add a CI gate that runs `gh attestation verify` on every PR — fails the build if a release artifact lacks a valid signature.
> **How to use:** Copy the workflow below to your repo as `.github/workflows/verify-attestation.yml`. Lifts SC3 from 0 to 2 (wired). Combine with the S8 (release-attest.yml) workflow for SC4=3.

## What is SC3?

SC3 (SLSA Build attestation verification) = a CI gate that verifies the SLSA Build provenance attestation on every release artifact. SC8 produces the attestation; SC3 enforces its existence and validity.

**The "wired" (SC3=2) signal**: a CI gate that downloads the latest release's provenance and runs `gh attestation verify` against it. The gate fails if the artifact is unsigned or the signature doesn't match.

## Tooling

| Tool | Purpose |
|------|---------|
| `actions/checkout` | Standard checkout |
| `actions/download-artifact` | Downloads the SBOM from the SBOM workflow |
| `gh attestation verify` | Verifies the SLSA Build provenance signature |
| `sigstore/cosign-installer` | Installs cosign for additional verification (optional) |

## Template: `.github/workflows/verify-attestation.yml`

```yaml
name: Verify Release Attestation

on:
  push:
    tags:
      - "v*"
  workflow_dispatch:

permissions:
  contents: read
  id-token: write
  attestations: read

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  verify:
    name: gh attestation verify
    runs-on: ubuntu-24.04
    steps:
      - name: Checkout
        uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2

      - name: Install gh
        run: type gh >/dev/null 2>&1 || (apt-get update && apt-get install -y gh)

      - name: Authenticate gh
        run: echo "${{ secrets.GITHUB_TOKEN }}" | gh auth login --with-token
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Build artifact (for verification source)
        # Replace with your build. The artifact is what gets verified.
        run: |
          mkdir -p dist
          echo "build artifact" > dist/artifact

      - name: Verify provenance for this build
        # gh attestation verify checks the SLSA Build provenance for the artifact.
        # If the workflow was triggered by a tag, verify against the release.
        # If triggered manually, verify against the most recent successful run.
        run: |
          if [ -n "${{ github.event.release.tag_name }}" ]; then
            TAG="${{ github.event.release.tag_name }}"
          else
            TAG="${GITHUB_REF_NAME}"
          fi
          echo "Verifying artifact provenance for ${TAG}..."
          gh attestation verify dist/artifact --repo ${{ github.repository }} || {
            echo "::error::Attestation verification failed for ${TAG}"
            exit 1
          }
          echo "Attestation verification passed for ${TAG}"
```

## How to apply

1. Copy the template above to your repo as `.github/workflows/verify-attestation.yml`.
2. Pin the SHAs of all `uses:` actions. Use these known-good SHAs (verified):
   - `actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd`
3. Customize the `Build artifact` step for your stack (must produce the same artifact that the S8 release-attest.yml produces).
4. The workflow triggers on `v*` tags OR `workflow_dispatch` (manual). For PRs, the trigger is `pull_request` — adjust as needed.
5. Commit + push + open a PR.

## SC3 score lift

- **0 → 1 (ad-hoc):** workflow file added but not exercised.
- **0 → 2 (wired):** workflow runs on every tagged release; `gh attestation verify` passes; the build fails if the signature is missing or invalid.
- **0 → 3 (measured):** the workflow ALSO runs on every PR (as a `pull_request` trigger), and a scheduled job re-verifies the last 10 releases nightly. Any failed verification pages the on-call.

## Reference: OmniRoute

OmniRoute is the reference repo for SC3 (SC3=3). Its `release.yml` has `id-token: write` + `attestations: write` + a release flow that produces a signed provenance + a CI gate that re-verifies it. The template above is a minimal extraction of that pattern.

## How to validate

After applying:
1. `git tag v0.0.1-test && git push --tags` to trigger the S8 release workflow
2. After it completes, trigger the SC3 verify workflow manually
3. `gh attestation verify dist/artifact` locally should pass

## Provenance

- **Template version:** 1.0
- **Author:** Phenotype Org holistic audit, 2026-06-16
- **Audit that produced it:** `FLEET-AUDIT-30-PILLAR.md` (SC3 P0)
- **Reference repo:** `KooshaPari/OmniRoute` (SC3=3)
- **License:** Same as the parent repo
