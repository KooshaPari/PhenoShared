# PhenoShared: completion, usability and remaining intent

Observation: 2026-10-16 Pacific. Frozen source: `1448514e5692d8de6e40be8c7b67c6b5168f9fe2`, independently matched to GitHub `main`. This is a documentation delivery, not a product-completion declaration. Local metadata/source inspection fits this workstation; no heavy builds, app launches, screenshots, recordings or process kills were performed.

**Phinbox's Swift implementation is present. Its native workflow has broken source contracts.** Rust owns daemon, tray, MCP/CLI, web forms and native popup dispatch; Swift owns the inbox window and form widgets. Repairing/discovering this work is materially different from starting another desktop application.

**PhenoShared is a pooled foundation and preservation home.** Its package inventory includes production-shaped code, libraries, explicit unsupported profiles, snapshots, examples and unfinished implementations. File counts and root compilation cannot certify usable products. Several observed production APIs return synthetic or empty results; others correctly refuse unsupported operations. Those cases are separated below.

## Read in this order

| Document | Decision it supports |
|---|---|
| [Goals and usability](goals-and-usability.md) | What each named family intends, actual journey, maturity limits and next proof |
| [Phinbox gaps and harness bridges](phinbox-bridges.md) | Existing native work, concrete regressions, per-harness authority contract |
| [Completion DAG and acceptance](completion-plan.md) | Bounded CVP/MVP targets, dependencies, staffing/time assumptions and sunset decisions |
| [Evidence and method](evidence.md) | Source links, what was inspected, unknowns, audit limitations |
| [Holding areas](holding-areas.md) | Every tracked top-level directory, children, classification and custody |
| [Root artifacts](root-artifacts.md) | Every root file and custody disposition |
| [Crate custody 1](crate-custody-01.md), [2](crate-custody-02.md) | Every first-level crate directory, even without a build manifest |
| [Package matrix 1](component-matrix-01.md), [2](component-matrix-02.md), [3](component-matrix-03.md), [4](component-matrix-04.md), [5](component-matrix-05.md) | Every recognized package/build declaration with intent and provisional class |
| [Measured inventory](inventory-summary.json) | Exact frozen denominator and parse errors; no completion score |

## Interpreting state

- `runnable`: a verified complete journey on a named installed profile. **No family earns this grade from this source-only audit.**
- `partial`: source supports part of a journey, but a concrete gap or missing qualification remains.
- `library-only`: reusable API source, not an end-user product; real consumer qualification is separate.
- `archive`: preserved donor/recovery snapshot; not presumed active or safe to delete.
- `pointer`: reference/manifest/document without a complete implementation at that location.
- `unknown`: intent, owner, reachability or behavior has not been established. An explicit appendix row is a queue item, not fake understanding.

The complete inventory is structurally exhaustive at the frozen revision. Semantic inspection is deeper for Phinbox and representative high-impact family paths, not every function of every package. All non-reviewed components stay provisional/unknown. Root membership is an exact manifest fact, not a disposition for packages outside that workspace. Installed usability, passing tests, independent acceptance, coverage, releases and current consumers remain separate evidence gates.

## Ownership

This audit writes only PhenoShared. PhenoApps and registry are external relationships, not inspected or modified here. A desktop shell in another repository does not erase the Swift client preserved here. Source lineage is per component: the whole repository must not be called a fork merely because it includes forks or absorbed copies. Preserve product-specific owners for Fabric, FocalPoint, MLX, ShareCLI and other consumers; PhenoShared owns shared-contract integration, not every product policy.
