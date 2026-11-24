# High-level design

## One product model, several authoritative systems

Tracera's role is a persistent reconciled product/system graph: capabilities, components, intent, state, interfaces, constraints, satisfaction and change. Repository-local files remain authoritative for their declared specifications; Git remains authoritative for observed source; actual test runners produce results; actual work engines own work transitions. No importer may rewrite another system's state just to make a graph look consistent.

The architecture has five cooperating planes:

| Plane | Responsibility | Must not do |
|---|---|---|
| Acquisition | Read Git/files/APIs, compiler indexes, tool reports and authorized captures | Execute arbitrary repository prompts as instructions |
| Model and provenance | Stable identities, versioned relations, claims, decisions, ownership and lineage | Invent missing rationale or erase contradictions |
| Analysis and assurance | Reachability, impact, requirement coverage, meaningful gates, dissatisfaction | Convert a static guess or simulated result into measured fact |
| Work integration | Emit bounded proposals and ingest real scoped engine receipts | Become a second mutable AgilePlus database |
| Presentation | CLI/API/MCP/PhenoDocs/product graph UI and reports | Make generated views independently authoritative |

## Local-first implementation strategy

Start with repo-local portable records and a small qualified ingestion path. Exact source search and language-semantic indexes precede embeddings. A simple transactional store plus indexed search is often a sufficient first backing; a graph engine is selected by demonstrated query and scaling need, not branding. Keep storage ports explicit enough to preserve exportability without writing a universal storage abstraction.

Use incremental acquisition keyed to immutable revisions/artifacts. A changed file invalidates derived claims based on its inputs and affected contracts; it does not require a complete narrative rewrite of every repository. Local dirty-state observations are overlays with their own identity, never falsely attached to the last committed SHA.

## Boundaries and deployment

A product pair can use the records without a running Tracera server. The server can ingest and query multiple subjects while enforcing per-subject visibility and write permissions. Static/public documentation receives only approved sanitized projections. Private raw prompts, credentials, native traces and unredacted screenshots remain inside their authorized boundary.

Adapters can expose compiler indexes, test/coverage reports, work receipts, package metadata and runtime events. They retain native semantics and raw-reference provenance. An unsupported field stays unsupported; all adapters must not pretend to expose the same completeness.

## Fault behavior

Failures in one source must not erase the prior known-good snapshot or imply absence. Partial acquisitions retain a manifest of success/failure/skips. Duplicate events are idempotent where the source identity permits it. Unknown outcomes are reconciled before mutation retries. Expensive analyses may be asynchronous only inside the implemented runtime with real queues/receipts; this document does not claim such a runtime already exists.

## Integration witness

Import one real product; establish actual source/profile identity; map a user capability to implementation and a failed or missing obligation; propose a bounded repair; ingest real verification evidence; update the product graph; restart and recover. This thin path should work before ten teams implement mutually incompatible extensions.

## Revision 1.1 — ecosystem-wide consumer impact

[Continuous ecosystem-first evolution](architecture/ECOSYSTEM-FIRST-EVOLUTION.md) applies to design, implementation, verification and delivery. External and owned reuse are both considered before handrolling. Current and committed consumers determine compatible behavior; plausible future consumers guide inexpensive seams, not speculative mandatory dependencies. Capability owners, adapters, consumer versions, cross-repo rollout and aggregate maintenance effects belong in each material change record. The repository write boundary does not narrow reasoning or expand authority. The proposed impact shape is `schemas/ecosystem-impact.schema.json`; it is structural evidence, not an approval or proof of parity.
