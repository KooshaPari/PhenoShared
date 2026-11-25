# Q2 Quality Ratchet Template

> **Source audit:** `FLEET-AUDIT-REPORT.md` — Q2 (Quality eng ratchets) is P1 priority (9/11 audited repos at score 0).
> **Method:** Add a CI gate that fails if the test coverage (or complexity, or lint warnings) regresses from the current baseline. The ratchet only allows improvement.
> **How to use:** Copy the workflow below to your repo as `.github/workflows/ratchet.yml`, customize the metric (coverage / lint / complexity), commit, push. Lifts Q2 from 0 to 2 (wired).

## What is Q2?

Q2 (Quality eng ratchets) = CI gates that prevent quality regressions. Common ratchets:
- **Coverage ratchet:** coverage can only go UP. If it drops, build fails.
- **Lint warning ratchet:** number of `#[allow(...)]` or `eslint-disable` lines can only go DOWN.
- **Complexity ratchet:** cyclomatic complexity per function can only go DOWN (or stay under a threshold).
- **Duplication ratchet:** code duplication percentage can only go DOWN.

**The "wired" (Q2=2) signal**: at least one ratchet is enforced in CI, with a baseline file that the build reads + asserts against.

## Template: `.github/workflows/ratchet.yml`

The example below uses a coverage ratchet (the most common). Adapt the `command:` line for your stack.

```yaml
name: Quality Ratchet

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

permissions:
  contents: read

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  coverage-ratchet:
    name: Coverage ratchet
    runs-on: ubuntu-24.04
    steps:
      - name: Checkout
        uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2

      - name: Setup language
        # Adapt for your stack:
        # Rust: `dtolnay/rust-toolchain@stable`
        # Python: `actions/setup-python@v5 with python-version: '3.12'`
        # Node: `actions/setup-node@v4 with node-version: '20'`
        uses: actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020 # v4
        with:
          node-version: 20
          cache: 'npm'

      - name: Install
        run: npm ci

      - name: Run tests with coverage
        run: |
          # Adapt for your stack:
          # Rust: `cargo tarpaulin --workspace --out Stdout --ignore-tests`
          # Python: `pytest --cov=src --cov-report=json`
          # Node: `npm test -- --coverage --coverageReporters=json-summary`
          npm test -- --coverage --coverageReporters=json-summary 2>&1 | tee test-output.log

      - name: Read previous coverage
        id: prev
        run: |
          if [ -f .coverage-baseline ]; then
            echo "prev=$(cat .coverage-baseline)" >> $GITHUB_OUTPUT
          else
            echo "prev=0" >> $GITHUB_OUTPUT
          fi

      - name: Read current coverage
        id: curr
        run: |
          CURRENT=$(cat coverage/coverage-summary.json | jq '.total.lines.pct')
          echo "curr=$CURRENT" >> $GITHUB_OUTPUT
          echo "Current coverage: $CURRENT%"

      - name: Assert coverage ratchet
        run: |
          PREV=${{ steps.prev.outputs.prev }}
          CURR=${{ steps.curr.outputs.curr }}
          if (( $(echo "$CURR < $PREV" | bc -l) )); then
            echo "::error::Coverage regressed from ${PREV}% to ${CURR}%"
            exit 1
          fi
          echo "Coverage ratchet: ${PREV}% -> ${CURR}% (no regression)"

      - name: Update baseline on main
        if: github.ref == 'refs/heads/main' && github.event_name == 'push'
        run: |
          echo -n "${{ steps.curr.outputs.curr }}" > .coverage-baseline
          git add .coverage-baseline
          git commit -m "ci: bump coverage baseline to ${{ steps.curr.outputs.curr }}%" || true
          git push || true
```

## How to apply

1. Copy the template above to your repo as `.github/workflows/ratchet.yml`.
2. Adapt the `Setup language` and `Run tests with coverage` steps for your stack.
3. Pin the SHAs:
   - `actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd`
   - `actions/setup-node@1a4442cacd436585916f4bd0495db9b8a8a0d4d8` (v4)
4. Commit + push + open a PR.

## Q2 score lift

- **0 → 1 (ad-hoc):** workflow exists but coverage baseline not committed.
- **0 → 2 (wired):** workflow exists AND coverage baseline is committed AND the ratchet fails the build on regression.
- **0 → 3 (measured):** the ratchet also tracks complexity + lint warnings + duplication (multi-metric ratchet); the baseline is updated automatically on every merge to main; the workflow reports the trend in the PR comment.

## Reference: OmniRoute

OmniRoute is the reference repo for Q2 (Q2=2). It has a coverage ratchet enforced in CI (60/60/60/60 for statements/branches/functions/lines). The template above is a minimal extraction of that pattern.

## How to validate

After applying:
1. Push a trivial change; the ratchet should pass
2. Delete a test; commit + push; the ratchet should fail
3. Add the test back; the ratchet should pass again

## Provenance

- **Template version:** 1.0
- **Author:** Phenotype Org holistic audit, 2026-06-16
- **Audit that produced it:** `FLEET-AUDIT-30-PILLAR.md` (Q2 P1)
- **Reference repo:** `KooshaPari/OmniRoute` (Q2=2)
- **License:** Same as the parent repo
