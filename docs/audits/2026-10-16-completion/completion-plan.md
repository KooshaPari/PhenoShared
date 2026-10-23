# Completion DAG, CVP/MVP and decisions

These are conditional engineering-effort ranges, not promised calendar dates or fabricated roadmap durations. No completion percentage or product grade is assigned. A useful bounded CVP demonstrates an actual user outcome; a usable MVP additionally has repeatable installation, recovery and clear support boundaries. Neither label waives existing stronger quality floors.

## Proposed dependency graph

    A: frozen inventory + owner/consumer decisions
      +-> B: Phinbox native contract repair -> C: install + native/web acceptance
      |                                      -> D: per-harness bridges
      +-> E: production placeholder reachability -> F: fail-closed/reuse repair
      +-> G: supported foundation consumer slice -> H: two-consumer acceptance
      +-> I: snapshot/sunset decisions (preserve until approved)
    C + D + F + H -> J: package-level supported release/install evidence

This document delivers the inventory/decision packet portion of A. Repairs and product acceptance remain pending. Existing owned implementations are the first reuse candidates; compare external facilities when a new parser/renderer/scheduler/crypto implementation would otherwise be introduced. No source moves, cross-repo modifications or retirements are performed here.

## Effort scenarios

Assumption: one engineer-day means 5-6 focused implementation/verification hours with existing source familiarity; reviewer capacity additional. Ranges include ordinary debugging, exclude unknown hardware/service/access failures. Owner starts clocks only after prerequisites and accepted scope are met.

| Node | Staffing and prerequisite | Conditional effort | Confidence / unknown gate |
|---|---|---|---|
| A remaining ownership reconciliation | Integration owner + product owners; manifest matrix available | 1-3 engineer-days for priority families; long tail unbounded until owners respond | medium; inventory is finite, intent decisions external |
| B Phinbox source-contract repair | 1 macOS/Rust+Swift engineer, schema fixtures and existing SDK | 2-5 engineer-days | medium; first clean native compile can reveal more errors |
| C Phinbox usable local CVP/MVP | same engineer + independent reviewer; B complete | 2-4 engineer-days | medium-low; signing/install/update/runtime currently UNKNOWN |
| D native harness integration | 1 adapter engineer, harness API owner/fixtures; C contract stable | 1-3 engineer-days per harness, 3 harnesses = 3-9; KCode separate 1-2 if required | low until exact native hook APIs and callback authority inspected |
| E reachability of real placeholders | shared owner + consumer owner | 1-2 engineer-days for HexaKit/router/eye-tracker priority triage | medium; downstream consumers may be external |
| F crypto bridge/synthetic-data repair | capability engineer + security/domain reviewer; E accepted | 2-5 for narrow fail-closed/reuse slice; eye-tracking model quality cannot be estimated from source alone | low; device/model/accuracy requirements decide scope |
| G one shared foundation CVP | owner + two consumer maintainers; API and ownership selected | 2-4 engineer-days | medium; dependency graph/build-cache isolation unknown |
| H independent consumer/negative proof | independent verifier, ready consumer fixtures | 1-3 engineer-days per capability slice | low-medium; each capability has its own denominator |
| I archive/pointer disposition | owners; provenance and consumer search | 0.5-2 engineer-days per disputed family | low; decision latency excluded; no autonomous deletion |
| J supported package release/install | package owner/reviewer, accepted native/consumer gates | 1-3 engineer-days per supported package profile | low; hosted/local/signing differences need receipts |

Serial Phinbox macOS usable slice B+C: 4-9 engineer-days under assumptions. Add three native harness bridges: 7-18 serial engineer-days, before unbounded external API blockers. Two engineers can overlap fixtures/adapters only after a stable contract, so do not simply divide by headcount. Whole-container production completion has no defensible aggregate estimate until unknown intent/consumers/profile counts are resolved. Prioritize funded/used capability slices instead of manufacturing a universal finish date for snapshots and libraries.

## Acceptance journeys

| Slice | Positive user/consumer witness | Required negative controls / usability gate |
|---|---|---|
| Phinbox local CVP | Originating agent queues; tray count/list/native/web agree; structured answer returns once | Root/port override, invalid field, cancel/defer/expiry, duplicate answer, restart, helper absent |
| Phinbox MVP | Clean install starts supported components; update preserves pending state; operator can recover failed callback | No false approval; state/version compatibility, uninstall scope, profile separation and accessibility/native interaction |
| Substrate/Gateway | Real configured engine/provider task, persisted output, cancellation and recovery | Fake route cannot masquerade as live result; upstream errors/429/timeouts and missing binary |
| Fabric/ShareCLI | Owned capability/process route plus resource isolation and cleanup | Stale lease/PID, unrelated process ownership, resource limit, partial-start recovery |
| FocalPoint/connector | Durable rule/event and authenticated provider sync | Expired credentials, duplicate cursor, replay/restart, API failure; color library does not count as app |
| AgilePlus | Real feature/WP state change and configured real dispatch with audit trail | Explicit stub mode labelled, governance rejection and audit tamper detection; live status via MCP |
| PhenoCompose | Supported Podman plan/apply/status/down and provenance | Unsupported health/publication/NVMS profiles reject before mutation; ownership of teardown |
| Library CVP | One clean unrelated consumer, API contract and failure semantics | Corrupt input, unavailable backend, cancellation/race as applicable; mock-only tests insufficient |
| Library MVP | Two pinned consumers, install/update/recovery and package-specific support policy | Independent suite floors and qualified negative oracles; no lockstep workspace release requirement |
| Eye tracking | Real frame/model -> measured calibrated gaze | Synthetic/no-face cases explicitly identified; independent accuracy truth; no capture in this task |

Required QA families retain existing 85%+ independent accepted floors and critical-obligation completeness. No unrun suite is green. New tests must challenge actual semantic defects, not mirror source. Source audit flags are not measured coverage or runtime certification.

## Sunset and intent register (proposals only)

| Candidate | Decision required | Default until accepted | Wakeup/acceptance condition |
|---|---|---|---|
| Duplicate AgilePlus/MLX/Fabric/provider copies | Which source owns each capability and which copies serve current consumers? | Preserve; no competing changes | Owner + consumer map and donor SHA |
| Swift vs external desktop shell | Keep supported macOS native client, share contract, or explicitly replace UI? | Preserve Swift; repair contract before rewriting | Named shell owner, functional parity/installation/data proof |
| Pine NanoVMS/PlayCua scaffolds | Committed supported capability or retained design seam? | library-only/unknown, no product claim | Real consumer and bounded acceptance or owner-approved pointer/archive label |
| HexaKit placeholder crypto | Which consumers call exported symbols; reuse canonical crypto or withdraw API? | Flag unsupported; prioritize fail-closed review | Reachability, vetted implementation and negative fixtures |
| Eye-tracker synthetic fallback | Diagnostic/demo profile vs real accessibility feature? | No real accuracy claim | Actual model integration and independent accuracy acceptance |
| .broken/untracked tests | Repair supported gates or retain historical evidence? | Preserve, do not count passing | Exact owner/change provenance and meaningful execution |
| Donor/recovery archives and one-file pointers | Historical custody versus accepted future work? | Preserve provenance; no scheduling by name alone | Owner decision, consumer search, retention policy |
