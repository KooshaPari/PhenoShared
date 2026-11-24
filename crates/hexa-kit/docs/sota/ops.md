# Ops — SOTA (HexaKit genesis)

## CI strategy

- Language template smoke: `scripts/scaffold-smoke.sh`, per-lang `task quality`
- Doc-only PRs: no `cargo build` required
- Template change: must pass smoke for affected languages

## Alternatives

| Approach | Verdict |
|----------|---------|
| Full workspace `cargo build` on every PR | Rejected — HDD/global lock cost |
| No CI on templates | Rejected |
| **Targeted smoke per changed template** | Chosen |
