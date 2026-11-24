# Research

## Reference Pattern

The hwLedger docs-site already uses the target shape:

- `ShotGallery` with `/cli-journeys/keyframes/.../frame-###.png`
- `RecordingEmbed` with stable `tape` ids
- page-local narrative around the same evidence bundle

See:

- `hwLedger/docs-site/reference/cli.md`
- `hwLedger/vendor/phenotype-journeys/README.md`

## Governance Surface

The reusable local parity doc already covers shared MCP and desktop surfaces.
This work extends that same idea to docs evidence:

- `docs/governance/agent-local-parity.md`
- `docs/governance/security-policy.md`
- `docs/runbooks/windows-desktop-runner.md`

## Gap Identified

Many repos have docs and runbooks, but no canonical rule requiring journey
keyframes and recordings as first-class evidence. That makes traceability
inconsistent and makes docs harder to audit across repos.
