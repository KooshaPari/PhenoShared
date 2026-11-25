# Desktop Safeguards Merge Train Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a provenance-bound, reproducible desktop NVIDIA Qwen3.5 agentic MVP without weakening the current fail-closed execution boundary. Merge the reviewed safeguards, make offline evidence validation enforceable in hosted CI, establish a real owner-issued execution authority, then obtain fresh dual-runtime and harness evidence sufficient for the seven promotion gates.

**Architecture:** `pheno-harness` remains the evidence producer and verifier, not the authority issuer. A no-launch desktop preflight binds topology and artifacts to the lane contract. An external owner must issue a separately verifiable, time-bounded authorization that binds a window, the canonical contract digest, the preflight digest, runtime, and endpoint. The wrappers verify policy, preflight, and authority before contacting an endpoint. Benchmark results flow through the existing benchmark envelope and the Tracera-compatible OTLP/evidence seam rather than a new telemetry database.

**Tech Stack:** Python 3.11, PyYAML, pytest, PowerShell, GitHub Actions, GitHub CLI, OpenTelemetry/OTLP, existing benchmark envelope, Tracera ingestion, optional Langfuse OTLP consumer.

---

## Current truth and non-negotiable invariants

- `config/desktop_nvidia_qwen35_lane.yaml` is `planning_only`; all execution permissions remain false.
- `scripts/run_desktop_lane_eval.py` and `scripts/run_desktop_agentic_fixture.py` remain dry-run by default. Under `--execute`, they must reject inactive policy, invalid preflight, and missing owner-issued authority before endpoint discovery, HTTP, subprocesses, or model execution.
- `scripts/start_dual_gpu_stack.ps1`, `scripts/run_dual_gpu_smoke.ps1`, and `harbor_cli/run_tbench_local.ps1` stay fail-closed. A caller-selected `WindowId`, a preflight record, or a self-issued Harbor sidecar is provenance only, never authority.
- Keep all linked worktrees, branches, stashes, and closed PR refs. Reconstruct focused successor PRs from current `origin/main`; never force-push, reset, clean, prune, or merge stale history wholesale.
- macOS inference remains paused. This plan adds only offline validation, hosted CI, contracts, and authorized desktop evidence work.

## Audit-backed boundary findings (2026-08-21)

- `phenotype-registry/BOUNDARY_OWNERS.md` is the living boundary SSOT, and its accepted `docs/adr/ADR-005-agileplus-governance-boundary.md` assigns Registry the ecosystem DAG/ADR boundary and AgilePlus the spec lifecycle. Neither designates a desktop execution issuer or benchmark-evidence owner. The authority gap is real and must be solved by governance, not by pheno-harness code.
- The existing evidence path is Helios benchmark envelope -> `Tracera::benchmark_run_to_issue` -> `persist_issues` -> evidence and trace links. `Tracera/docs/sessions/20260722-agent-harness-portfolio/artifacts/helios-tracera-handoff.md` marks its signature as a placeholder and requires CI revalidation; do not represent this as compliance-grade ingestion.
- Current PRs #103, #104, #106, and this plan PR #107 have GitHub-hosted failure records with zero steps, no assigned runner, and absent job logs. They are host-admission evidence, not source-test evidence, until a job actually executes.
- Langfuse has no discovered local integration in the bounded source audit. Treat it as an optional sink evaluation after the existing envelope/Tracera seam is proven, not as a new platform dependency.
- The Tracera focused contract target is presently not reproducible under `cargo test --locked`: Cargo reports that it must update `Cargo.lock`. Keep the checkout clean; first isolate and review the lockfile resolution as its own dependency-maintenance change, then run the focused `benchmark_contract_tests` target in that reviewed state.

## Phase 0 - merge the reviewed safeguards

- [ ] **0.1 Rebase assessment, not mutation.** Fetch `origin/main`, run `git merge-tree` for PR #106, and inspect the PR file list. If it is non-conflicting, retain its existing branch; if it conflicts, reconstruct only the four reviewed safeguards on a fresh current-main branch and close the superseded draft with a provenance comment.
  - Files: `scripts/run_desktop_lane_eval.py`, `scripts/run_desktop_agentic_fixture.py`, `scripts/desktop_contract.py`, `scripts/desktop_execution_preflight.py`, plus their desktop tests.
  - Verify: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3.11 -m pytest -q tests/test_desktop_agentic_fixture.py tests/test_desktop_lane_eval.py tests/test_desktop_evidence.py tests/test_desktop_execution_policy.py`; `python3.11 scripts/validate_desktop_evidence.py`; `git diff --check`.

- [ ] **0.2 Hosted admission triage.** Record the exact GitHub check state and runner-level reason for PR #106. Classify a job with no runner, no step log, and the payment/spending-limit annotation as hosted-admission failure, not a source test failure. Do not retry or alter source merely to chase an unstarted job.
  - Evidence: PR check URLs, job annotation, and the locally verified command bundle from 0.1.
  - Exit condition: either GitHub starts the normal checks, or the PR records a stable externally-owned billing blocker.

- [ ] **0.3 Merge #106 through protection.** Resolve genuine review threads, use normal review/auto-merge only after required checks actually run and pass, and record the merge SHA. Do not admin-bypass branch protection.
  - Exit condition: merged SHA is reachable from `origin/main`, or a precise hosted blocker remains recorded.

## Phase 1 - make the offline boundary continuously enforceable

- [ ] **1.1 Merge PR #103 after #106.** It adds the selected no-launch desktop suites to `.github/workflows/ci.yml` and tests that the command remains offline. Rebase/reconstruct only if the #106 merge causes a real conflict.
  - Files: `.github/workflows/ci.yml`, `tests/test_desktop_ci.py`.
  - Verify: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3.11 -m pytest -q tests/test_desktop_ci.py`; `actionlint .github/workflows/ci.yml`; `git diff --check`.

- [ ] **1.2 Make the canonical evidence validator a CI assertion.** Extend the CI job so it runs `scripts/validate_desktop_evidence.py` and asserts the intentional current state: `valid=true`, `status=blocked`, `passed_gates=5`, `total_gates=7`. Keep the test environment free of SSH, PowerShell, WSL, `nvidia-smi`, and inference commands.
  - Files: `.github/workflows/ci.yml`, `tests/test_desktop_ci_validator.py`.
  - Verify: parse workflow YAML, run the selected tests, run the validator locally, and assert no prohibited command token is in the extracted pytest command.

- [ ] **1.3 Merge PR #104 after #106.** Preserve the documentation correction that historical helper repeats are diagnostic and non-promotable, and that caller window IDs and Harbor sidecars are not execution authority. Resolve its open reviewer thread only after the behavior it describes is reachable from `main`.
  - Files: `docs/sessions/20260802-desktop-nvidia-mvp/*`, `tests/test_desktop_evidence_docs.py`.
  - Verify: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3.11 -m pytest -q tests/test_desktop_evidence_docs.py`; confirm the merged docs match the reviewed semantics.

## Phase 2 - authority ownership and verifiable authorization

- [ ] **2.1 Name the authority owner through the existing governance boundary.** Inspect phenotype-registry ownership records, AgilePlus feature governance, and the current desktop specification. Record one owner repository, maintainer role, immutable revision, and approval channel. Do not make pheno-harness, Harbor, or a wrapper self-authorize.
  - Evidence required: owner declaration accepted in its canonical repository and linked from the desktop plan.
  - Exit condition: an accountable owner and immutable authority contract location exist.

- [ ] **2.2 Define the owner-issued authority contract.** The owner contract must include `window_id`, lane contract SHA-256, preflight byte SHA-256, runtime, endpoint identity, model/revision identity, issue time, expiry, issuer identity, and a verification mechanism. Define explicit rejection cases for wrong digest, expired record, untrusted issuer, wrong runtime or endpoint, and replayed window.
  - Tests: positive fixture, one fixture per rejection reason, and a verifier test that has no network or desktop dependency.
  - Exit condition: versioned schema and verifier acceptance criteria are reviewed in the owner repository.

- [ ] **2.3 Consume, do not create, authority in pheno-harness.** Add a small authority verifier adapter to both wrappers. It accepts a supplied owner artifact, verifies all bindings locally, and remains before endpoint probing. It must not generate keys, sign records, issue leases, or set the lane policy active.
  - Files: new narrowly-scoped verifier under `scripts/`, `scripts/run_desktop_lane_eval.py`, `scripts/run_desktop_agentic_fixture.py`, tests under `tests/test_desktop_*`.
  - Verify: active-policy test matrix for valid authority and every rejection case; mocked endpoint proves rejected records make zero outbound calls.

## Phase 3 - reproducible topology and artifact provenance

- [ ] **3.1 Complete producer/consumer preflight binding.** Require the no-launch preflight record to bind canonical contract path/digest, artifact-manifest digest, physical helper/primary identity, free memory, runtime port availability, runtime mapping, host identity, and bounded freshness. Reject incompatible overrides before endpoint probing.
  - Files: `scripts/start_dual_gpu_stack.ps1`, `scripts/desktop_execution_preflight.py`, desktop wrapper tests.
  - Verify: producer-shaped JSON fixtures accepted; wrong role/index/port/path/hash/mapping/freshness rejected; existing no-launch producer remains readable by both consumers.

- [ ] **3.2 Add explicit artifact allowlisting.** Store the reviewed model/runtime/binary identity manifest in a tracked, human-reviewable location. Validate SHA-256 and byte count in no-launch preflight before any launch authorization is considered.
  - Files: desktop provenance manifest, PowerShell preflight, Python validator, fixtures.
  - Verify: missing, mismatched, and extra artifact fixtures fail; correct fixture proves no bytes are written and no process is launched.

- [ ] **3.3 Preserve runtime namespace clarity.** Keep physical `nvidia-smi` indices distinct from WSL/vLLM and Windows llama.cpp logical visibility. Add a regression fixture encoding helper=physical 0 and primary=physical 1, with explicit runtime-local mappings.
  - Verify: `tests/test_desktop_runtime_mapping.py` plus no-launch launcher tests.

## Phase 4 - experiment design, benchmark quality, and evidence integrity

- [ ] **4.1 Freeze the experiment card before an authorized run.** Record model revision, quant artifact, tokenizer revision, prompts/tasks, sampling parameters, warmup policy, measurement windows, resource sampling method, pass/fail thresholds, and expected output schema. Hash every input manifest.
  - Files: canonical benchmark/evidence envelope and run-specific immutable manifest.
  - Verify: schema validation rejects missing revisions, unpinned datasets, non-finite values, duplicate task IDs, and attempt/run identifier mismatch.

- [ ] **4.2 Execute bounded helper and primary repeatability.** Only after 2.2, 2.3, and 3.1-3.3 pass and a live authority artifact is present, run isolated helper and primary repetitions with no fallback. Capture device/runtime/model provenance for every attempt.
  - Acceptance: both runtimes satisfy the defined repeated-run count, every attempt binds the same authority window and source contract, and any fallback fails the result rather than being silently substituted.

- [ ] **4.3 Run harness-integrated evaluation.** Invoke the Portage/Harbor-compatible task adapter only after the authorization scope explicitly includes it. Produce a signed or otherwise verifier-bound `pheno.perf.v1` result and the authorization sidecar; never treat the sidecar as authority.
  - Acceptance: task-level success, replay/provenance identifiers, latency/memory/quality result fields, and a trace/evidence reference are all present.

- [ ] **4.4 Validate the seven promotion gates.** Run `scripts/validate_desktop_evidence.py` against a fresh complete envelope. Require all seven gates, not merely integrity. Independently review source reachability, artifact hashes, topology, repeatability/no-fallback, and Harbor/eval authorization.
  - Exit condition: validator reports `valid=true`, `status=ready`, `passed_gates=7`, `total_gates=7`; otherwise publish a blocked report with unmet gates.

## Phase 5 - observability and research ecosystem convergence

- [ ] **5.1 Reuse the benchmark envelope as the trace root.** Audit existing Tracera `benchmark_run_to_issue` ingestion and HeliosCLI envelope support. Map run/session/attempt/evidence identifiers to OpenTelemetry trace attributes without copying raw prompts, secrets, or model weights into telemetry.
  - Files to inspect first: `Tracera/crates/tracera-server/src/ingest.rs`, the HeliosCLI harness envelope, and `artifacts/benchmark_run.schema.json`.
  - Verify: focused Tracera contract test in an idle build slot; malformed causality, status, and replay hashes reject.

- [ ] **5.2 Instrument at process boundaries, not inside every library.** Add spans for preflight validation, authority verification, endpoint discovery, run start/finish, evaluation verdict, and evidence publication. Use a stable resource identity and trace correlation attributes from the benchmark envelope.
  - Verify: local in-memory/exporter test proves no prompt/secret field is emitted and the trace carries run/session/attempt identifiers.

- [ ] **5.3 Evaluate Langfuse as an optional OTLP sink, not a second source of truth.** First prove the existing OpenTelemetry exporter can send the bounded trace vocabulary to a collector. Then test Langfuse only in an isolated environment using secrets injection, retention review, redaction rules, and a disabled-by-default configuration. Do not add a direct legacy ingestion client.
  - Rationale: OTLP retains backend flexibility, and Langfuse documents OTLP as the supported ingestion path.
  - Acceptance: no credentials in repository or CI logs; exporter disabled by default; one sanitized fixture trace visible in the selected sink; Tracera/evidence remains the canonical promotion record.

- [ ] **5.4 Create a research-scorecard generator.** Generate one machine-readable, non-promoting status report from contract, preflight, benchmark evidence, evaluation result, trace link, and Git commit reachability. Distinguish `planning`, `blocked`, `evidence_complete`, and `promoted`; never infer promotion from a green unit suite.
  - Verify: fixtures cover every state, stale evidence, wrong commit, and missing trace link.

- [ ] **5.5 Evaluate Inspect as a bounded evaluator adapter.** Use Inspect's agent bridge and tool-approval configuration only in a sandboxed experiment that targets the existing OpenAI-compatible evaluation endpoint. Translate its task/score/log output into the existing benchmark envelope; do not replace Portage, Harbor, or the benchmark contract.
  - Acceptance: one fixture task executes with an explicit tool-approval policy, produces a stable run/session/attempt mapping, and round-trips through schema validation without exposing prompts, credentials, or unredacted tool payloads.

## Phase 6 - portfolio consolidation without losing semantic work

- [ ] **6.1 Classify recovery surfaces before integration.** For each active repository, export branch/worktree/stash metadata, compare semantic patch IDs against current `origin/main`, classify as `merged`, `novel`, `superseded`, `experimental`, or `unknown`, and retain the original ref regardless of outcome.
  - Priority repositories: `pheno-harness`, `phenotype-omlx`, `Portage`, `Tracera`, `OmniRoute`, `AgilePlus`, and `phenotype-registry`.
  - Acceptance: each candidate has source ref, merge-base, changed paths, test evidence, owner, and disposition reason.

- [ ] **6.2 Reconstruct only purpose-owned current-main PRs.** For a semantic candidate, identify a requirement, user-facing outcome, tests, and the owning code path; reproduce the minimal diff on current `origin/main`, request review, and merge through protection. Leave historical branch/ref intact after merge.

- [ ] **6.3 Make the cockpit an index, not authority.** Update the existing cockpit only from checked-in/PR evidence. Each work item must show intent, owner, source ref, outcome, current state, verification, blocker, and successor. Do not duplicate AgilePlus lifecycle state or fabricate live telemetry.

## External gates and explicit operator actions

- [ ] **E1 Restore GitHub Actions admission.** A billing manager must resolve failed payment or raise/adjust the Actions spend policy, then rerun a single draft PR workflow. GitHub documents that Actions is metered and a configured stop-usage budget can prevent further usage. This is an account action, not a source change.
- [ ] **E2 Designate the authority issuer.** The designated governance owner must approve the signed/verifiable contract from Phase 2. No caller-provided window ID, preflight, or Harbor sidecar may substitute for this decision.
- [ ] **E3 Provide an authorized desktop window.** After E1/E2 and all offline gates, the authority issuer provides a non-expired artifact bound to the exact preflight/runtime/model. Only then may Phase 4 run live desktop work.

## Dependency DAG

```text
GitHub billing admission
          |
          v
       PR #106
       /      \\
      v        v
   PR #103    PR #104
      |          |
      +----+-----+
           v
   continuous offline guard

owner designation -> authority contract -> wrapper verifier
       |                                      |
       +-> provenance manifest -> preflight --+
                                                v
                               authorized bounded repeats
                                                |
                                                v
                           Portage/Harbor evaluation + OTLP trace
                                                |
                                                v
                              7/7 validator + independent review
```

## Completion evidence

The MVP is not complete until: the reviewed safeguard and CI/documentation PRs are merged; hosted checks actually run; an external owner has issued a verifiable authority; a fresh dual-runtime preflight and allowlisted artifacts bind to that authority; repeated helper and primary runs complete without fallback; harness evaluation emits a complete evidence envelope; the seven promotion gates pass; and an independent review verifies source, artifact, runtime, and trace provenance.
