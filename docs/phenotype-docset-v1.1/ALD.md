# Abstraction-layer design

ALD here means **Abstraction-Layer Design**, explicitly chosen for this package rather than claimed as an official AgilePlus acronym.

## Layer 0 — source facts

Git objects, filesystem captures, manifests, compiler indexes, native coverage/test reports, runtime observations, build artifacts and authenticated engine receipts. Preserve each producer's limits and exact identity. No global code graph is presumed complete from regex or grep output.

## Layer 1 — normalized observations

Adapters map source facts to portable records with source anchors, timestamps, tool versions, actor/visibility and failure states. Normalization does not discard original units, scopes, missing data or native error categories. Unicode/text normalization and redaction create separate derived objects with source links.

## Layer 2 — semantic entities and relationships

Repository, product, applet, package, source unit, interface, state object, capability, obligation, test, run, artifact, installation, claim and decision. Each relationship has provenance and applicability. A static reference, dynamic observation and inferred dependency remain distinguishable. A source entity can map to several product capabilities; one capability can span several repositories.

## Layer 3 — obligations and analysis

Apply accepted predicates: reachable required feature; public behavior documented; actual consumer source resolves; negative test produces failure; covered denominator meets floor; state survives migration; private evidence not published. Produce dissatisfaction and research hypotheses with uncertainty. LLM semantic interpretation proposes explanations; it does not override deterministic facts or accept its own authority.

## Layer 4 — bounded work

Convert accepted dissatisfaction into a task with parent outcome, required inputs, allowed changes, relevant oracles, affected consumers and rollback. The work graph is not the product model. Work can complete and disappear from active scheduling while the persistent capability remains.

## Layer 5 — human and agent projections

Render concise context packets, nested maps, comparison tables, specs, task views, CI verdicts and release notes from the same IDs. Scaled graph navigation expands only a bounded neighborhood or aggregate, with source-linked drilldown. A command-line query must expose the same semantics as the GUI without requiring a graphical session.

## Recursive composition

An applet combines domain logic, ports, adapters, state/permissions, lifecycle, surfaces and children. A composite applet can expose a smaller public boundary upward. Composition does not imply copying child state or dissolving trust boundaries. Direct function calls are preferable for qualified same-process paths; network/process/Wasm adapters require explicit overhead and isolation justification. Avoid automatic protocol promotion at every recursive level.

## Revision 1.1 — ecosystem-wide consumer impact

[Continuous ecosystem-first evolution](architecture/ECOSYSTEM-FIRST-EVOLUTION.md) applies to design, implementation, verification and delivery. External and owned reuse are both considered before handrolling. Current and committed consumers determine compatible behavior; plausible future consumers guide inexpensive seams, not speculative mandatory dependencies. Capability owners, adapters, consumer versions, cross-repo rollout and aggregate maintenance effects belong in each material change record. The repository write boundary does not narrow reasoning or expand authority. The proposed impact shape is `schemas/ecosystem-impact.schema.json`; it is structural evidence, not an approval or proof of parity.
