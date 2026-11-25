# Known Issues

| Severity | Repository/class | Issue | Gate |
|---|---|---|---|
| Critical | `omniroute-wtrees` | Airlock recorded one dirty item; local path and snapshot are absent | Recover or disprove payload |
| High | `Httpora-archive-2026-07-14` | Split canonical ownership | Map refs and consumers to both owners |
| High | `4sgm-archive2` | Empty, but sibling archive has incomplete parent ref parity | Complete QuadSGM lineage proof |
| Medium | two Airlock smoke repos | Nonempty infrastructure provenance | Retain run provenance before archive |
| Medium | `test-novars` | One nonempty README head | Classify/preserve test artifact |
| Medium | org-audit worktree | Audit content may be sensitive | Preserve refs, review/redact, deduplicate |
| Existing | ecosystem validator | `dispatch-mcp` is unreachable and several canonical repos have metadata drift | Separate registry-maintenance lane |
| Existing | `.gitleaks.toml` | Allowlist path `*.lock` is parsed as an invalid regex and panics gitleaks | Separate security-config fix |

Depletion documents calling shells deletable conflict with preservation manifests requiring local
payload searches. This session resolves that gate for thirteen empty shells only; it does not weaken
the five-check boundary policy.

The ecosystem-validator findings predate and do not arise from this documentation-only Wave 2
change. They prevent claiming a globally clean registry validation result.
