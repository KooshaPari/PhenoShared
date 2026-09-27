# Canonical engineering, shared consumption and outcome-driven optimization

**Phenotype · September 16, 2026 · Research and handoff v0.1**

## 1. Diagnosis

The problem is larger than inconsistent tool preferences. It is a broken chain between **intent, decision, source ownership, selected implementation, actual consumer use, and independently verified outcome**. A repository can mention the desired tool, contain its configuration, and still execute an old tool or fail to cover its own source. A shared capability can exist in several directories and still lack an identifiable release that a clean consumer can install.

The audit found concrete examples of these failure modes. They justify an executable decision-and-adoption layer, but not an indiscriminate migration script or another giant governance application.

### 1.1 Evidence that changes the plan

| Finding | What is directly visible | Interpretation and required caution |
|---|---|---|
| **F01 — conflicting Shared identities** | PhenoShared's README describes PhenoMLX/OMLX; root npm manifest names `phenodocs`; Cargo identifies a substrate workspace with absorbed Fabric, Registry and Infra domains. **[G01–G03]** | Establish component boundaries and writer/release authority. Multiple roots can be intentional; the conflicting presentation is not proof that every component is broken. |
| **F02/F03 — false-confidence typechecking** | Tracera repeats six `-p` flags in a single compiler invocation. Its “native typecheck contract” test asserts that exact command. **[G04, G05]** | A text assertion does not establish project coverage. A local TypeScript 5.8.3 fixture reproduced last-project selection; run this canary with Tracera's actual pinned compiler and every component. **[E01]** |
| **F04 — a check repairs source** | Tracera's `lint:stylelint` calls `lint:stylelint:fix` before checking. **[G04]** | Separate repair from verification. Explicit cache writes can be allowed; hidden source repair cannot be a prerequisite for claiming the original state passed. |
| **F05 — actual tool drift** | Tracera uses Oxlint/Oxfmt. HeliosLab's live scripts use Biome. OmniRoute's live lint command uses ESLint. **[G04, G06, G07]** | This is not merely search noise from historical documents. Still, preserve framework/plugin/upstream obligations until replacement coverage is demonstrated. |
| **F06 — tool provenance gaps** | PhenoDesign calls `oxfmt` without a direct declaration in the shown manifest; several tools use `latest`; `packageManager` is bare `bun`. **[G08]** | A lockfile or parent workspace can resolve these inputs. Require a cold installation and exact binary provenance instead of declaring failure from a manifest alone. |
| **F07 — Python dimensions conflated** | AgilePlus declares Python `>=3.14` while Ruff targets `py312`. Portage already uses uv, Ruff and ty but declares a `>=3.12` compatibility minimum. **[G09, G10]** | Minimum supported Python, lint syntax target, selected interpreter and runtime GIL state are separate facts. |
| **F08 — MCP is present, not absent** | AgilePlus and several Shared paths import FastMCP; Shared server READMEs refer to PhenoFastMCP. Similar server paths exist in separate trees. **[G17–G20]** | Resolve actual package source and writer ownership before making another wrapper. Similar excerpts are not enough to declare entire implementations duplicates. |
| **F09 — unresolved shared CI** | AgilePlus calls `phenotype-tooling/.github/workflows/sbom-monthly.yml@main`. The old provider name returns 404 through this connection. **[G15, G23]** | Resolve stable provider identity, access and workflow location. 404 does not distinguish deletion, access restriction or an unavailable rename path. |
| **F10 — optimization objective mismatch candidate** | Shared's Cargo release uses `opt-level="z"`, LTO and one codegen unit. **[G03]** | Size, throughput, tail latency and build time need different qualified profiles. Size optimization is not itself evidence of slower execution. |
| **F11/F12 — publication and consumption differ** | Registry's visible index text is dated May/June; a September 16 global handbook exists. Shared already declares docs/design dependencies. **[G02, G08, G11–G13]** | Repair authority and consumer proof, not just documentation volume. A dependency declaration is not proof of useful consumption. |
| **F13/F14 — local assumptions survive consolidation** | Infra's Lefthook hardcodes one package and ambient Python; Tracera chains seven postinstall patches; Shared's recent history contains a redaction sweep followed by URL repairs. **[G04, G14, G21]** | Account for tool resolution, scope, patches and semantic transformations. Neither “one hook file exists” nor “mass edit committed” closes these obligations. |

The findings registry separates observation, interpretation, countercase, acceptance proof and owner role. The repository inventory is a discovery denominator—not an assertion that all discovered repositories are active or audited.

### 1.2 History is evidence, not a completion signal

The Tracera contract-test path history points to commit `d34adf39dfd979279acdfb23ca8f9a6b686d318c`, associated with PR 900 and a native/non-mutating typecheck repair in August. The current file still asserts the repeated-project command. That makes semantic verification more important than trusting a commit title. The five recent Shared commits also show that source-shaping work and URL repair are happening during the same period as handbook consolidation. **[G21, G22]**

This was targeted history inspection, not a complete ancestry, blame, merge-base or upstream-patch audit. The runbook specifies the remaining analysis explicitly.

## 2. Extend the existing authority; do not invent a competing one

The September 16 global handbook already requires ecosystem-first reuse, honest non-pass states, independent verification, immutable subject identity, and separate working/published/integrated/verified/packaged/installed/released/adopted states. It expressly says it is not a migration approval or permission grant. **[G13]**

The June stack policy already distinguishes capability boundaries from language buckets and prefers Rust, Zig and adopted Mojo cores, with scoped edge-language justification. That is existing decision material—not something to pretend never existed. Its “TypeScript 7 preview” wording and location/authority relationships need reconciliation with the newer handbook and current upstream facts. **[G12]**

The proposed integration is:

**Existing handbook principles → typed decision records → component profiles → generated configs/workflows/agent views → execution receipts → existing product graph and assessment records.**

PhenoShared can host most of the implementation. Registry is a logical indexing role; it must not become a second owner of every contract. Tracera remains the persistent canonical product/system model, including gaps and dissatisfaction, rather than being reduced to an audit-log sink. AgilePlus remains a bounded execution/work-management component. This packet is source material for those existing roles, not a proposal for an additional product named “canonicalization.”

Every incorporated record needs an authority pointer, revision, applicability selector, owner, selected solution, alternatives, acceptance tests and supersession rule. Do not silently convert a research suggestion or old assistant answer into an accepted decision.

## 3. The decision model

### 3.1 Canonical means one answer for a defined situation

It does not mean one implementation for every language, framework, device or workload. Define the decision key as:

`capability × consumer requirement × runtime/language × platform × deployment profile × constraints × policy revision`

A TS library, Vue docs renderer, Bun desktop application and Node-native upstream fork are different consumers. A CPU throughput library, a realtime audio callback, and a GPU host interface are different performance profiles. A single generic “use fastest technology” rule does not resolve any of those choices.

The decision record should carry both a selected default and the predicate for choosing an alternative. A tree makes routing explicit. A matrix exposes comparisons. The chosen solution makes ordinary work fast. These representations should be generated from one authoritative record set rather than maintained as three competing descriptions.

### 3.2 Keep state dimensions separate

**Decision state:** proposed, accepted, superseded, rejected, research-only.

**Applicability:** applicable, not-applicable-with-proof, unknown.

**Implementation disposition:** canonical implementation, supported profile variant, temporary exception, blocked by a capability gap, unassessed.

**Evidence stage:** declared, resolved, executed, independently verified, packaged, installed, adopted.

A scoped exception is not canonical adoption. A successful package build is not installation. A native binary name is not native compiler provenance. A generated page is not a useful docs experience. Never flatten these axes into one optimistic percentage.

### 3.3 Exception contract

A temporary exception identifies the component and path, violated decision, reason, actual alternative evidence, owner, expiry, migration trigger, acceptance test and exit condition. Expiry must cause an affected non-pass state—not silently refresh itself. A lasting intentional variant belongs in a supported profile with its own qualification; it must not live forever as a waiver.

The purpose is not to ask a human to approve every choice. Agents can apply accepted rules and existing authority autonomously. The purpose is to prevent an unreviewed deviation, unsupported backend or swallowed error from masquerading as the chosen solution.

### 3.4 Counterfactuals are required

For a material change, test at least the current baseline, an improved version of that baseline and a credible alternative. Ask how the proposed choice could be wrong: a hidden copy, cold-start penalty, missing rule, native-addon mismatch, worse tail latency, upstream maintenance tax, or increased total code. Record disconfirming observations, not just favorable screenshots and microbenchmarks.

## 4. Canonical tooling selections

The following are proposed operational rules for the user's stated directions. Their deployment status is **not deployed**. Exact production versions should be chosen through a qualified lock/toolchain release, not guessed from today's version strings.

| Area | Selected direction | Qualification and legitimate branch |
|---|---|---|
| JS/TS lint | **Oxlint** primary. | Map existing rules, custom plugin behavior, type-aware checks and framework rules. A residual runner owns only named missing obligations. **[W02]** |
| Formatting | **Oxfmt** for qualified supported formats. | Demonstrate semantic preservation and idempotence; unsupported languages/plugins get disjoint selectors, not two competing formatters. **[W03]** |
| TS CLI checking/building | **Qualified native TypeScript 7**, by resolved package/version. | The current native command is `tsc` for TypeScript 7 RC and later; `tsgo` was the preview command. Compiler-API and framework adapters are separate decisions. **[W01]** |
| JS installation | **Pinned Bun and frozen locks** for eligible first-party workspaces. | Package-manager, runtime and test-runner transitions are separate. Prove lifecycle scripts, workspace packing and cold consumer resolution. **[W07]** |
| JS runtime | **Prefer Bun where behavior is qualified.** | OmniRoute-style native/upstream constraints need real API/ABI/shutdown tests, not a string replacement of `node`. **[G07, W07]** |
| Python environment | **uv** owns interpreter/environment/dependency resolution. | Record selected interpreter build and lock; support multiple explicitly qualified profiles rather than ambient Python. **[W04]** |
| Python runtime | **CPython 3.14t target** for eligible owned execution. | Verify the build and actual GIL state after real imports. Unsupported extensions can re-enable the GIL. Do not force an unsafe GIL-off mode to satisfy a checkbox. **[W05]** |
| Python analysis | **Ruff** lint/format; **ty preferred after parity qualification**. | Existing mypy/framework/stub coverage stays explicitly scoped until replaced. This type-checker preference is a recommendation, not a claim that every repo has accepted it. **[G09, G10]** |
| Git hooks | **Lefthook**, one owned orchestrator. | Inspect effective configuration and installed hooks; run the same required checks in CI because local hooks can be bypassed. **[W08, W24]** |
| Python MCP | **Maintained standalone FastMCP**. | Keep PhenoFast integration thin. Qualify schema, transport, auth, cancellation, errors and shutdown. Main-branch docs can describe unreleased features. **[W06]** |
| Native-host MCP | **Qualified native SDK/profile when justified.** | Adding Python solely for brand consistency may violate the performance/deployment objective. The external contract remains shared. |
| Shared CI | **Reusable provider workflows/actions, immutable refs, thin generated callers.** | GitHub requires actual provider workflow files in `.github/workflows` and job-level reuse. Verify provider access and hosted execution. **[W09]** |
| Native release | **Separate outcome-specific profiles.** | Measure speed/size/latency/build tradeoffs; do not treat `opt-level="z"` or maximum optimization as universally optimal. **[W10]** |

### 4.1 Fix Tracera's checking semantics before treating a compiler migration as complete

Enumerate the exact projects and eligible source sets. Use one checked invocation per independent project or a correctly configured references/build graph with declared outputs. Do not concatenate repeated `-p` flags and assume union semantics. Add a unique deliberate type error in each project's isolated canary and require the **final** verification command to fail for every case. Include source currently omitted by globs, tests where appropriate, generated declarations, and cross-package references.

Retain the non-mutating intent. Redirect permitted build cache outputs explicitly; avoid banning a correct mode by name merely because an earlier implementation wrote to the checkout. The contract is coverage, correctness and side-effect boundaries—not a fixed command string.

### 4.2 Python 3.14t means more than an interpreter suffix

The runtime qualification has four independent obligations: the selected interpreter is the intended free-threaded build; actual application imports leave the GIL disabled; the dependency and FFI stack is thread-safe under its intended access patterns; and time/memory behavior satisfies the product's workload. Process-based parallelism, native libraries that already release the GIL, and an ordinary GIL build are useful comparison controls rather than enemies of the requested target. **[W05]**

A failed dependency import or GIL transition is a recorded compatibility gap. It must not be converted to a no-op stub, a passing empty test suite, or a silent runtime substitution. Resolve the underlying dependency or qualify a clearly bounded profile variant.

### 4.3 Avoid residual-tool deletion by grep

An ESLint plugin dependency can still supply a custom rule even when the entry point is Oxlint. `typescript` can be used through a compiler API as well as the CLI. `node` can be an intentional supported runtime, not a forgotten installer. Multiple locks can belong to genuinely isolated workspaces. The audit must trace roles before deleting names.

The opposite mistake is equally bad: “it might be needed” is not a permanent exception. Require an exact use, actual behavior and an exit criterion where replacement is intended.

## 5. Shared architecture: thin products without a shared monolith

### 5.1 What the product should own

A product should normally own its distinctive domain behavior, composition, content/configuration, and product-specific acceptance tests. Common auth integration, telemetry, protocol glue, versioning, configuration loaders, docs plumbing, design primitives, release workflows, and ordinary infrastructure adapters should usually come from qualified shared or external capabilities.

Do not force a raw line-count target. A product can legitimately contain substantial domain logic. A wrapper can hide enormous runtime or maintenance cost in dependencies. Generated bindings and tests can add many useful lines. The target is **less duplicated, hand-maintained commodity behavior across the whole system**, not merely fewer visible files in each application.

### 5.2 Narrow capabilities, not one compulsory import

Treat PhenoShared as a collection of separately consumable capability packages with clear exports, optional features and dependency direction. A docs renderer should not pull a GPU stack. A policy client should not import the complete orchestration engine. A landing page should not need the entire desktop component runtime. A native CLI should not require a Python installation merely to reach a tiny protocol feature unless that is an intentional qualified boundary.

A useful structure is logical rather than an instruction to create these exact folders:

- Foundation contracts and language-neutral data types.
- Runtime capabilities, grouped by domain rather than language buckets.
- Thin bindings/adapters for supported runtimes.
- Docs/design/landing production capabilities.
- Toolchain/configuration/CI/release packages.
- Contract suites, consumer fixtures and policy data.

Do not duplicate upstream implementation merely to place a Phenotype name around it. Use the external library directly when no shared semantics are needed. Add a wrapper only for an actual policy, compatibility, telemetry, lifecycle or domain boundary.

### 5.3 A consumption edge needs proof

For each provider/consumer edge record:

`provider capability → exact source/release → distribution artifact → consumer resolution → entry point → exercised behavior → retained evidence`

Classify the edge as runtime, build-time, test-time, code generation, documentation, design asset, configuration, workflow, or intended future consumption. A planned edge is not installed reuse. A package import alone is not enough when a local copy can shadow the imported behavior.

The acceptance fixture installs the provider artifact in an isolated consumer without sibling checkouts or developer-global tools, exercises the relevant contract, and proves that removing or changing the provider affects the expected behavior. Also prove that changing an unrelated optional capability does not expand the consumer dependency closure unexpectedly.

### 5.4 Do not collapse distinct kinds of integration

Cross-consumption can be shared implementation, protocol interoperability, common contracts, data transformations, component composition, renderable assets, or coherent user journeys. It does not require an iframe or visibly embedded second application. Nor does a seamless UI automatically prove shared semantics underneath. Record and test the actual integration mode.

## 6. PhenoDocs, landings and design need product contracts

### 6.1 PhenoDocs

The current manifest already exposes a docs federation concept and references shared docs/design packages. That is a starting point, not sufficient acceptance. **[G02, G08]**

Define PhenoDocs as a **versioned documentation production and consumption system**. Its shared scope includes renderer/theme integration, navigation composition, version and locale routing, source attribution, search indexing boundaries, generated API references, executable examples, broken-link checks, preview/publish plumbing, and machine-readable discovery.

Product teams retain the meaning: explanations, task flows, API/domain concepts, troubleshooting, examples and release-specific facts. Central copies must be generated projections with source revision and invalidation rules. A copied Markdown warehouse with no freshness contract is not the target.

The qualification fixture should contain two materially different consumers: for example a library/API reference and a desktop/product guide. It must prove clean rendering, versioned URLs, code-example execution, theme consumption, navigation/link correctness, accessibility, and source lineage. It must also fail when a referenced version or input disappears.

### 6.2 Landings

A landing is more than a README render. Share the product descriptor, supported scene/component slots, token origin, navigation/CTA schema, media pipeline, metadata generation and delivery/measurement plumbing. Keep product narrative and distinctive interaction intentional.

Validate actual destinations, installed or demo state, responsive layout, keyboard behavior, loading/error/offline states, reduced-motion behavior where relevant, and asset/version provenance. Shared infrastructure should enable authored spatial/interactive experiences, not make every product a clone of one generic template. That is consistent with the current handbook's explicit scene and interaction direction. **[G13]**

### 6.3 Design authority

Use one token/component source and a controlled extension mechanism. Do not count a copied palette as continuous consumption. Test that a supported upstream token change reaches the intended consumer artifact, that local overrides are named and bounded, and that unrelated products do not become coupled through accidental global CSS or state.

## 7. Canonicalize patterns, not only tools

The larger pattern matrix in `pattern-matrix.json` covers the questions below. These are proposed defaults and branch conditions, not claims that the current ecosystem lacks each capability.

| Question | Default | Branch that justifies another choice |
|---|---|---|
| Local library or service? | Local typed boundary when lifecycle and ownership permit. | Independent deployment, fault/trust boundary, shared lifecycle or remote access requires a service. |
| New domain implementation? | Improve the current owner or use a qualified dependency. | No suitable implementation or a measured/required advantage outweighs ownership and migration costs. |
| Protocol? | Existing typed in-process interface; preserve supported public contracts. | C ABI for native interop, a generated RPC contract for remote typed calls, or an HTTP API where its consumers require it. |
| Durable state? | One explicit owner and minimal persistence for required semantics. | Multiple writers, consistency/durability or scale requirements warrant a different qualified data system. |
| Cache? | No cache without a specific repeated-cost problem. | Define key, version, permissions, eviction and invalidation before adding one. |
| Retry? | No blind retry of non-idempotent effects. | Transient failure plus idempotency/deduplication and a bounded deadline permits retry. |
| Workflow engine? | Small trigger + durable dedupe/journal + scoped action when enough. | Durable long-lived coordination, compensation, fan-out or replay requirements justify an existing workflow engine. |
| Concurrency? | Bounded tasks with explicit cancellation and resource budgets. | Increase parallelism only when the constrained resource and tail-latency behavior improve. |
| Error contract? | Typed failure category, origin, retryability and safe context. | Domain-specific extensions remain compatible; never return success-shaped defaults on failure. |
| Generated code/config? | One source and deterministic generator. | Handwritten extension seams are explicit; edits to derived views are rejected or regenerated. |
| Test evidence? | Independent required families and real denominators. | Profile-scoped not-applicable status requires proof, not an empty suite. |
| Release done? | Package, install and exercise outside the source checkout. | Role-specific equivalent for library/CLI/service; do not invent a GUI just to satisfy packaging. |

For a file-watch/cron-to-agent workflow, the canonical minimal workflow is: normalize the event, prove input readiness, deduplicate by stable identity, evaluate scope/policy, acquire a bounded claim, execute the agent with constrained actions, validate its proposed effect, apply authorized effects idempotently, record outcome, and retry only through explicit failure semantics. A cron trigger does not remove the need for a journal or side-effect control; it can still be the right trigger.

The policy should also cover API evolution, authentication/authorization, secret/config resolution, process lifecycle, telemetry, model/tool budgets, serialization, feature flags, schema migrations, backup/restore, release rollouts and human-facing quality. `pattern-matrix.json` makes these concrete routing questions rather than leaving them hidden in per-project conventions.

## 8. Maximum exploration, measured production promotion

### 8.1 The three objectives are related, not interchangeable

“Exotic” expands the candidate space. “Novel” invites architectural and algorithmic improvement, not just a new language. “Outcome” decides what should survive in the product. Maximizing the number of installed toolchains is not the same as maximizing any useful product outcome.

The existing language tier should be a default and ownership aid, not a reason to reject a measured superior implementation. Conversely, a promising language feature or vendor benchmark does not qualify an ecosystem-wide migration.

### 8.2 A workload-specific frontier

| Candidate | First useful experiment | Main disconfirming question |
|---|---|---|
| Zig | Allocation-sensitive native/FFI or SIMD path. **[W11]** | Does it beat the optimized current implementation after safety, ABI and packaging costs? |
| Odin | Simulation/graphics/asset processing with explicit layout. **[W12]** | Is the advantage actually data-layout work that could be adopted more cheaply in the current language? |
| Nim | Native utility/domain transform using metaprogramming. **[W13]** | Do runtime, memory-model and interop obligations erase the implementation benefit? |
| Julia | Numerical simulation, planning or optimization slice. **[W14]** | Do specialization, startup and boundary costs fit the real request distribution? |
| Pony | Actor-oriented scheduler/control experiment. **[W15]** | Does the model improve correctness or useful concurrency once operational integration is included? |
| Mojo | CPU/GPU numeric slice. **[W16]** | Is the required target/toolchain/distribution supported and beneficial now? |
| CUDA + CUTLASS/CuTe | A demonstrated NVIDIA hot path with a good vendor/library baseline. **[W19]** | Are speedups still present across required shapes/devices after transfer and launch overhead? |
| Triton | A tiled tensor kernel that current compiled operations do not serve well. **[W17]** | Are compile cost, shape coverage and full-request behavior favorable? |
| ISPC | CPU batch/vector transform. **[W20]** | Does explicit SPMD beat current auto-vectorized code at actual batch sizes? |
| TileLang | Another tile/kernel search space for the same GPU workload. **[W21]** | Is a better isolated kernel offset by integration or target restrictions? |
| Futhark | An array-parallel algorithm. **[W22]** | Does host integration and supported operation coverage fit the product? |
| Halide | An image/video/array pipeline. **[W23]** | Does schedule search improve the entire pipeline, including memory and transfer costs? |

**Trident is not silently normalized to Triton.** The identified `kakaobrain/trident` is a real Triton-based ML library, but its repository has been archived since October 16, 2023. It may be useful research material; intended identity, a maintained successor or a narrowly owned port must be resolved before treating it as a current production default. **[W18]**

This is a researched seed set, not an exhaustive list of all beneficial languages or libraries. The selection process stays open: every performance/correctness/capability gap can introduce a candidate with a precise hypothesis and evidence source. Current-language algorithm changes, better external libraries and removal of work remain mandatory controls.

### 8.3 Promotion objective

First enforce hard requirements: correctness, numerical tolerance, security/trust boundaries, supported targets, required features and delivery constraints. Then compare the remaining candidates on a Pareto frontier rather than a made-up universal score.

Measure at least end-to-end p50/p95/p99, useful throughput, startup/compilation, peak and steady memory, transfer/copy volume, build/test duration, artifact/dependency size, agent repair burden, integration cost and ongoing maintenance. Use only dimensions relevant to the workload, but record what was omitted.

A useful accounting identity is:

`total cost = implementation + integration + migration + qualification + operations over the chosen horizon + expected maintenance/rework`

For a native/GPU extraction, a useful latency decomposition is:

`request time = queue + host work + serialization/FFI/copies + device transfer + launch + kernel + return/synchronization`

A faster kernel can lose end-to-end. A slightly faster path can still be valuable at large volume. Do not impose an arbitrary “must be 20% faster” rule or let noisy 1% differences drive a rewrite. Compare uncertainty, repeated trials, actual request distributions and the applicable horizon.

### 8.4 Experiments that merit doing early

The Shared size-profile question is a cheap experiment before changing languages. Tracera checking and docs build latency are useful tooling baselines. A genuinely measured high-cost serialization, routing, numerical or media path is a candidate for a bounded language/kernel tournament. The concurrent agent/game/audio environment should be represented where it affects the product; an idle-machine microbenchmark is not enough for a realtime promise.

The packet does not name a production performance winner. None of these ecosystem workloads was benchmarked here.

## 9. Missing-capability audit

Do not audit only selected tools. Audit the presence, consumption and correctness of the following obligations: component/source identity; reproducible bootstrapping; config and secret resolution; required lint/type/security coverage; mutation-resistant instruments; real unit/integration/E2E/mutation denominators; API/schema compatibility; dependency graph direction; source/consumer release binding; hook/CI equivalence; licensed/upstream patch maintenance; packaging and clean installation; telemetry and budgets; cancellation/backpressure/idempotency; docs/search/versioning; design/accessibility/interaction; data durability and restore; target-specific performance; and lifecycle/rollback authority.

Each cell is **present-and-qualified, present-unqualified, absent-with-evidence, not-applicable-with-proof, or unknown**. Search nonmatches are unknown until the eligible inventory and actual execution paths have been inspected. A generated catalog is not implementation. A test counter is not a coverage denominator. A failed or skipped measurement is not a pass.

The September handbook's independent unit/integration/E2E/mutation floors are 85%, with 100% of critical obligations selected and passing. Preserve those semantics and its reviewed denominators rather than averaging a weak family away. The synthetic receipt checker illustrates those rules but does not authenticate any supplied data or implement the full product assessment system. **[G13]**

## 10. Distribution and drift control

A decision is incomplete until agents can consume it and changes propagate safely. Publish a qualified policy/toolchain/config release, not a pile of copied snippets. The release identifies tool versions and binary provenance, schema/config content, workflow commit refs, supported profiles, mandatory fixtures and compatibility changes.

Consumers select a policy release in a component manifest. The agent-facing instructions, effective lint/format/type settings, hook commands, CI callers, and human matrices are generated projections. A check detects disagreement; an explicit repair command regenerates them. Do not have a gate silently repair itself.

Use staged consumer promotion. Update a representative consumer first, then the bounded affected set, then wider adoption. Immutable pinning must be paired with an update mechanism; otherwise it simply makes drift permanent. A stale policy release, missing export, unavailable provider, unsupported target or expired exception must be visible in existing product/assessment records.

For GitHub workflows, package-level storage can be the authoring source, but the provider must expose an actual workflow under `.github/workflows`. Consumer `uses` values must be supported literal refs, with verified permissions and access. A successfully parsed YAML file is not proof that GitHub can invoke it. **[W09]**

## 11. Execution order without governance paralysis

There are three concurrent tracks: comprehension/identity, qualification/instruments, and useful delivery/simplification. The current handbook already makes clear that no perfect atlas must precede all useful repair. **[G13]**

The ten work packages in `migration/work-packages.json` form a DAG. The first useful assignments are:

**Instrument lane:** repair Tracera's multi-project check and independent negative controls. This is bounded and can progress while ownership mapping continues.

**Authority/consumption lane:** resolve Shared's root component map and the current reusable-workflow provider. Establish an actual installable/exported provider and one cold consumer before mass migration.

**Toolchain lane:** qualify OXC/native TypeScript/Bun and uv/3.14t against representative supported profiles. Do not mix runtime changes, formatter changes and domain rewrites into one unreviewable diff.

**Product pilots:** migrate a bounded Tracera/HeliosLab surface; qualify docs/design consumption in real consumers; qualify one existing FastMCP service. Keep the upstream-heavy OmniRoute runtime matrix separate from straightforward first-party tooling cleanup.

**Performance lane:** run a small bounded tournament against a measured bottleneck and the size-profile hypothesis. Do not start a wholesale language rewrite to manufacture activity.

Shared manifests, lockfiles and release state need an integration writer/lease. Read-only investigations and isolated implementation slices can run in parallel. Work should be assigned by capability and acceptance target, not mechanically one agent per repository.

## 12. Metrics that would mean something

Measure known applicable decisions resolved to a qualified implementation, verified provider/consumer edges, canonical version adoption by profile, unresolved/expired exceptions, commodity code duplicated across products, clean install success, consumer compatibility failures, actual release-to-installed lineage, and outcome regressions.

Report the denominator and unknown count. The 46 discovered repositories are not a valid denominator for “Lefthook adoption” until active eligible checkouts and subcomponents are classified. A positive dependency edge is not a unit of delivered value. Fewer repositories, more tests, more policy files and more languages are not success metrics by themselves.

For code reduction, compare both product-local code and total shared + adapter + generator + migration burden. Count dependencies and build fan-out separately. A successful extraction removes duplicated ownership while preserving useful behavior and reducing total maintenance or increasing measured capability.

## 13. Completion and limits of this handoff

This packet provides a concrete decision set, profiles, pattern branches, research hypotheses, source-grounded findings, work packages, schemas, an agent prompt, a continuation runbook and small tested reference tools. It is usable now as a bounded implementation assignment.

It does **not** certify the whole ecosystem. The connected review covered selected current files in nine repositories, targeted searches, a small history sample, relevant retrieved context and primary public documentation. Some long responses were truncated. Container DNS prevented a full remote clone. No exact current product build, hosted workflow run, installed-consumer verification or production performance comparison was executed.

The required next evidence is explicit: full source/lineage mapping, exact toolchain release qualification, real consumer conformance, hosted reuse and installed artifact checks. Agents should close those cells, not relabel this research packet as a completed fleet migration.

---

## Source map

The human-readable [source index](SOURCE-INDEX.md) and machine-readable `audit/sources.json` resolve all references. The latter retains URLs or Library identities, source paths, observed Git blob identities where available, pinned commits where actually requested, acquisition scope and limits. A blob SHA is not a commit SHA. A mutable source URL is not immutable evidence by itself. Local experiment output is retained separately under `verification/`.
