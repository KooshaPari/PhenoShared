# Topic and lifecycle taxonomy

GitHub topics are discovery projections, not release tags, issue labels, architectural proof or destructive permissions. Rich fields belong in the accepted subject/catalog record; generate a small useful subset of public topics. Do not put private operational details in public topic strings.

## Proposed independent facets

| Facet | Example values | Rule |
|---|---|---|
| Lifecycle | active, incubating, maintenance, paused, reference, tombstoned | One accepted lifecycle; uncertainty explicit in the record |
| Role | product, sdk, library, runtime, tool, protocol, adapter, fork, catalog, docs | Primary role plus justified secondary roles; not a generic pile |
| Domain | product-model, work-governance, coding-agent, inference, game, media, compute, device-control | Use actual user/domain meaning |
| Surface | gui, cli, mcp, api, daemon, library | Actual intended/implemented distinction in structured fields |
| Platform | macos, windows, linux, web, mobile | Supported/proposed levels stay in profile records |
| Ownership | canonical-source, maintained-fork, generated-projection, historical-reference | Source/release responsibility, not repository popularity |
| Work horizon | current-viable-product, research, maintenance | Keep transient progress out of topics; link the real work record |

Use valid lowercase hyphenated topic names such as `domain-product-model`, `surface-mcp`, `role-runtime`. Prefixes help facet queries but should not replace common discovery terms. Do not write metadata from this proposal until approved and refreshed.

## Why current broad tags are weak

The preceding observation saw Tracera tagged active/devtools/library/tool and Civis tagged engine/product/research/simulation. Those are inherited metadata examples, not a fresh topics audit. They obscure product-model and game-first identity. KCode's active/devtools/engine/tool also does not expose owned-fork or coding-agent semantics. The solution is meaningful facets, not maximal topic count or another rename.

## Completeness and quality checks

Verify immutable IDs and aliases; exactly one accepted lifecycle; no contradictory public role; supported platform evidence linked; explicit fork/upstream identity; private data withheld; no tags falsely asserting shipped/verified state; public discovery links work. Changes require a diff and an owner, not automatic interpretation of a model's fresh classification.
