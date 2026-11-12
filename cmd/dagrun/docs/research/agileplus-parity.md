# AgilePlus Atomic-Acceptance Parity: absorbed `crates/agile-plus` vs standalone main @ `8699676312dfcd787435221a7926a407af920fc6`

**Date:** 2026-11-12
**Repo under audit:** `/Users/kooshapari/CodeProjects/Phenotype/repos/PhenoShared` (branch `style/rustfmt-phinbox-native`, HEAD `63134dfe98bb6ab1176335a83b44b4cc9f07e5ec`)
**Reference:** `KooshaPari/AgilePlus` @ `8699676312dfcd787435221a7926a407af920fc6` (main), read via `gh api`
**Mode:** read-only forensic. No mutation, no test execution.

---

## 1. Headline verdict

**The atomic-acceptance slice is ABSENT from the current PhenoShared tree. It is not renamed, not re-homed, and not partially ported. Every layer of it — domain command, application service, sqlite transaction/receipt, HTTP route, gRPC service, and all four atomic-acceptance test suites — is missing from both the workspace-member `crates/agileplus-*` crates and the staged `crates/agile-plus/` snapshot.**

The only name-adjacent local artifact, `crates/acceptance-contract/`, is a **different concept** (a declarative probe/scorecard engine from `phenotype-tooling`) and must not be counted as parity.

One genuinely-related file is carried: `crates/agile-plus/crates/agileplus-domain/tests/acceptance_traceability_integration_test.rs` (384 lines locally). It concerns **traceability**, not atomic acceptance, and it exists upstream too — at a larger, newer revision (13,388 B upstream vs 384 local lines).

---

## 2. Reference shape: what standalone `8699676` actually contains

Atomic acceptance is a six-layer vertical slice. Every path below was read from the recursive git tree of `8699676` (`truncated=false`, 5,324 tree entries) and the domain/application/HTTP/gRPC/sqlite sources were fetched via `gh api repos/KooshaPari/AgilePlus/contents/<path>?ref=8699676` (raw).

| # | Layer | Exact path @ `8699676` | blob sha (12) | bytes |
|---|---|---|---|---|
| 1 | Domain command + correctness oracle | `crates/agileplus-domain/src/domain/acceptance.rs` | `48e684a899e4` | 6,098 |
| 2 | Domain port (transactional boundary) | `crates/agileplus-domain/src/ports/terminal_acceptance.rs` | `d73cb54edc7b` | 694 |
| 3 | Application service (read-only preflight) | `crates/agileplus-application/src/use_cases/acceptance.rs` | `48923f76c7fc` | 2,129 |
| 4 | Application service (write path) | `crates/agileplus-application/src/use_cases/accept_feature.rs` | `4e88a4496ce1` | 663 |
| 5 | Sqlite transaction + receipt repo | `crates/agileplus-sqlite/src/repository/acceptance/mod.rs` | `92eb4b8e27fa` | 21,655 |
| 6 | Sqlite migration (receipt table) | `crates/agileplus-sqlite/src/migrations/030_atomic_acceptance.sql` | `c8a845bcbbf9` | 885 |
| 7 | HTTP routes | `crates/agileplus-api/src/routes/acceptance.rs` | `2647f50be88f` | 5,777 |
| 8 | gRPC service | `crates/agileplus-grpc/src/acceptance.rs` | `fc0a11de68a4` | 11,446 |
| 9 | gRPC server bootstrap | `crates/agileplus-grpc/src/acceptance_server.rs` | `12e1200c96bf` | 1,382 |
| 10 | Test — HTTP | `crates/agileplus-api/tests/atomic_acceptance_http.rs` | `42a3c9341a68` | 14,236 |
| 11 | Test — sqlite | `crates/agileplus-api/tests/atomic_acceptance_sqlite.rs` | `567debe4baa1` | 8,901 |
| 12 | Test — gRPC | `crates/agileplus-grpc/tests/atomic_acceptance_rpc.rs` | `59f684b8b586` | 9,784 |
| 13 | Test — sqlite repo | `crates/agileplus-sqlite/tests/atomic_acceptance.rs` | `79de1addcec8` | 8,551 |
| 14 | Test fixture | `crates/agileplus-sqlite/tests/atomic_acceptance/fixture.rs` | `52b48fb98365` | 5,952 |
| 15 | Test — traceability (also local) | `crates/agileplus-domain/tests/acceptance_traceability_integration_test.rs` | `7c9b0e5532cc` | 13,388 |

Supporting upstream artifacts (context, not code): `docs/adr/0010-acceptance-contract-progression-gates.md`, `docs/adr/0019-acceptance-authority-terminal-gates.md`, `verification/ATOMIC_ACCEPTANCE_BOUNDARY_2026-10-02.md`, `verification/ATOMIC_ACCEPTANCE_GATE_2026-10-03.md`, `verification/SPECIFICATION_ACCEPTANCE_CONTRACT.md`.

### 2.1 Semantics of the slice (from the fetched sources)

**Domain command** (`domain/acceptance.rs`) — `AcceptFeatureCommand { request_id, feature_id, actor, expected_governance_version }` with `#[serde(deny_unknown_fields)]` and a `validate()` that rejects `feature_id <= 0`, blank/oversized `request_id`/`actor`, and control characters. `actor` is documented as "supplied by the authenticated transport, not a policy override" — i.e. the transport is the identity authority. Also defines `AcceptedCandidate { wp_id, assignment_id, attempt_id, evaluation_id, candidate_ref, worktree_path }`, `FeatureAcceptanceReceipt`, `AcceptanceOutcome`, and the pure `validate_candidate(...)` correctness oracle.

**Domain port** (`ports/terminal_acceptance.rs`) — `TerminalAcceptancePort::commit_terminal_acceptance(&TerminalAcceptanceMutation { feature_id, wp_ids_to_complete, audit_entries })`. The doc comment is explicit: "Correctness/governance preflight happens before this reaches persistence; the adapter commits these writes atomically." Persistence is deliberately fenced off from the preflight.

**Application layer** — `use_cases/acceptance.rs::require_feature_acceptance` is a **read-only preflight** over `StoragePort + ExecutionRecordPort` that resolves each WP's active Assignment → latest Evaluation → criteria → criterion results → attempts, then calls the shared pure oracle. It refuses vacuous acceptance ("terminal acceptance cannot be vacuous"). `use_cases/accept_feature.rs::accept_feature` is a thin write path: validate the command, delegate to `storage.accept_feature_atomic(command)`. The comment captures the security property: "Callers cannot supply a boolean governance pass or separately write terminal state."

**Sqlite** — `migrations/030_atomic_acceptance.sql` creates `feature_acceptance_receipts` with `request_id TEXT PRIMARY KEY`, FK to `features(id)`, `command_json`, `receipt_json`, `committed_at`, plus two triggers: `acceptance_receipts_no_update` and `acceptance_receipts_no_delete`, both `RAISE(ABORT, ...)`. Receipts are **immutable and append-only at the database level**, and the PK on `request_id` gives idempotency. The repository adapter (`repository/acceptance/mod.rs`, 21,655 B — the largest single piece) implements the atomic commit + receipt write.

**HTTP** (`api/routes/acceptance.rs`) — `POST /{slug}/accept` and `GET /{slug}/acceptance-receipt`. Header comment: "Authenticated terminal acceptance, distinct from governance-only `/validate`." The receipt GET returns "a historical committed receipt; does not assert current applicability" — receipts report committed history, not perpetual applicability.

**gRPC** — `grpc/src/acceptance.rs` (11,446 B) plus `acceptance_server.rs`, which serves an `AgilePlusCoreService` over tonic with a graceful shutdown, and degrades to a stub error under `agileplus_proto_stubs` when protobuf generation was skipped.

---

## 3. Local tree: what PhenoShared actually carries

Three candidate homes were checked.

### 3.1 `crates/agile-plus/` — a staged **recovery snapshot** of the standalone repo (NOT a workspace member)

This directory is a whole-repo snapshot (it retains `.github/`, `ADR.md`, `AGENTS.md`, `kitty-specs/`, `docs/`, `.kittify/`, `_branches.txt`, `AUDIT_INDEX.md`, `.work-audit/`). It declares its own `[workspace]` with an explicit "Active members" list, so it is **not** a member of the PhenoShared root workspace (confirmed: `crates/agile-plus` does not appear in the root `Cargo.toml` members list; only `crates/agileplus-*` and `crates/acceptance-contract` do).

Its 52-crate layout matches the standalone's, but at an **older upstream revision**:

- `crates/agile-plus/crates/agileplus-domain/src/domain/` → `api_key, audit, backlog, cycle, device_node, epic, event, feature, governance, metric, mod, module, project, proptest_enums, service_health, snapshot, state_machine, story, sync_mapping, user, work_package` — **no `acceptance.rs`**.
- `crates/agile-plus/crates/agileplus-application/src/use_cases/` → `advance_feature, create_epic, create_feature, create_story, mod, persist_synced_stories, transition_story, triage` — **no `acceptance.rs`, no `accept_feature.rs`**.
- `crates/agile-plus/crates/agileplus-api/src/routes/` → 18 route modules, **no `acceptance.rs`**.
- `crates/agile-plus/crates/agileplus-sqlite/src/repository/` → 15 modules, **no `acceptance/` subdirectory**.
- `crates/agile-plus/crates/agileplus-sqlite/src/migrations/` → ends at `026_feature_labels.sql`; **no `030_atomic_acceptance.sql`**.
- `crates/agile-plus/crates/agileplus-grpc/src/` → `conversions, event_bus, lib, proxy, server, streaming, work_items` — **no `acceptance.rs`**.
- Carried: `crates/agile-plus/crates/agileplus-domain/tests/acceptance_traceability_integration_test.rs` (384 lines) — the traceability test, present upstream at a larger revision.

The migration ceiling (`026`) versus upstream's `030_atomic_acceptance.sql`, plus upstream's dated verification docs (`2026-10-02` / `2026-10-03`), establishes that the atomic-acceptance work landed in the standalone **well after** this snapshot was taken — consistent with `crates/ABSORPTION_MANIFEST.md`, which records that `agileplus-*` staging copies were made on 2026-06-17 and that the standalone repo is the canonical owner.

### 3.2 `crates/agileplus-*` — the workspace-member split crates (no atomic acceptance)

These are the crates that actually build as part of PhenoShared. None carries the slice:

| Local path | Contents | Atomic acceptance? |
|---|---|---|
| `crates/agileplus-domain/src/domain/` | `api_key, audit, backlog, cycle, device_node, event, feature, governance, metric, mod, module, project, service_health, snapshot, state_machine, sync_mapping, work_package` | **absent** — no `acceptance.rs` |
| `crates/agileplus-domain/src/ports/` | `agent, content, mod, observability, review, storage, vcs` | **absent** — no `execution.rs`, no `terminal_acceptance.rs` |
| `crates/agileplus-sqlite/src/repository/` | `audit, backlog, cycles, events, evidence, features, governance, metrics, mod, modules, projects, sync_mappings, work_packages` | **absent** — no `acceptance/` |
| `crates/agileplus-sqlite/src/migrations/` | `001`–`017` only (+ `mod.rs`) | **absent** — no `030_atomic_acceptance.sql` |
| `crates/agileplus-api/src/routes/` | `audit, backlog, branch, cycle, events, features, governance, import, mod, module, stream, work_packages, worktree` | **absent** — no `acceptance.rs` |
| `crates/agileplus-grpc/src/` | `conversions, event_bus, lib, proxy, server, streaming` | **absent** — no `acceptance.rs` / `acceptance_server.rs` |
| `crates/agileplus-application/` | **crate does not exist at the top level** | **absent** — the application layer is missing from the split set entirely |

There is **no `crates/agileplus-application` crate** in the split set. The upstream write path (`accept_feature`) and read path (`require_feature_acceptance`) have no local host crate, so even a partial port would have had nowhere to land.

### 3.3 Identifier sweep — the decisive negative

A repo-rooted `grep -rl` over `crates/` (excluding `/target/`) for the upstream identifier set:

```
AcceptFeatureCommand | accept_feature | AtomicAcceptancePort | TerminalAcceptancePort
accept_feature_atomic | commit_terminal_acceptance | FeatureAcceptanceReceipt
AcceptanceOutcome | AcceptedCandidate | validate_candidate
```

→ **zero hits anywhere in `crates/`**, including `crates/agile-plus/crates/`, `crates/hexa-kit/`, and every `crates/agileplus-*` split crate.

A second sweep for `atomic_acceptance|AtomicAcceptance|AcceptFeature|acceptance_receipt|AcceptanceReceipt` across `agileplus-api`, `agileplus-grpc`, `agileplus-sqlite`, `agileplus-domain`, `agileplus-contract-tests`, `acceptance-contract`, and `agile-plus/crates` → **zero hits**.

A third sweep for `AcceptFeatureCommand|accept_feature_atomic|feature_acceptance_receipts` across `crates/hexa-kit` → **zero hits**. `crates/hexa-kit/agileplus/` is another partial copy of the standalone repo (`crates/`, `docs/`, `harnesses/`, `ADR.md`, `AGENTS.md`, `COMPARISON.md`, …) and is likewise free of the slice.

### 3.4 `crates/acceptance-contract/` — name-adjacent, functionally unrelated

This crate **is** a workspace member (root `Cargo.toml` line 278, "E2.4 Pattern A wave 3 batch AB2 (2026-10-09): 2 small libs (acceptance-contract, dag-scheduler)"). Its `Cargo.toml` points `repository`/`homepage` at `KooshaPari/phenotype-tooling` — confirming provenance from a different repo.

Its public API (`src/lib.rs`, `src/types.rs`) is: `AcceptanceContract { hard_requirements, soft_requirements }`, `Requirement { id, description, weight, skip, probe }`, `Probe::{CommandExitCode, …}`, `ScoreCard`, `BaselineDelta`, `BaselineEntry`, `ExecutionContext`, and `run_acceptance(contract_path, baseline_path, workspace_root, options) -> ScoreCard`. It shells out to probes, diffs a YAML baseline, and scores hard/soft requirements.

**No overlap with atomic acceptance**: no `AcceptFeatureCommand`, no `AcceptedCandidate`, no receipt type, no sqlite schema, no HTTP route, no gRPC service. It solves "does the workspace satisfy a declarative requirement list?", not "atomically accept a feature and commit an immutable receipt". Classifying it as parity would be a false positive.

---

## 4. Absent vs renamed vs unknown

| Layer | Upstream path @ `8699676` | PhenoShared status | Basis |
|---|---|---|---|
| Domain command + oracle | `crates/agileplus-domain/src/domain/acceptance.rs` (`48e684a899e4`) | **ABSENT** | no `acceptance.rs` in split domain, none in snapshot; `AcceptFeatureCommand`/`AcceptedCandidate`/`validate_candidate` = 0 hits repo-wide |
| Domain port | `crates/agileplus-domain/src/ports/terminal_acceptance.rs` (`d73cb54edc7b`) | **ABSENT** | `crates/agileplus-domain/src/ports/` has 7 modules, none matching; `TerminalAcceptancePort`/`AtomicAcceptancePort` = 0 hits |
| Application service (read) | `crates/agileplus-application/src/use_cases/acceptance.rs` (`48923f76c7fc`) | **ABSENT** | no `agileplus-application` crate at top level; snapshot's `use_cases/` has 9 modules, none matching |
| Application service (write) | `crates/agileplus-application/src/use_cases/accept_feature.rs` (`4e88a4496ce1`) | **ABSENT** | as above; `accept_feature`/`accept_feature_atomic` = 0 hits |
| Sqlite transaction + receipt | `crates/agileplus-sqlite/src/repository/acceptance/mod.rs` (`92eb4b8e27fa`) | **ABSENT** | no `acceptance/` under either sqlite `repository/`; `commit_terminal_acceptance` = 0 hits |
| Sqlite migration | `crates/agileplus-sqlite/src/migrations/030_atomic_acceptance.sql` (`c8a845bcbbf9`) | **ABSENT** | split migrations stop at `017`; snapshot stops at `026`; `feature_acceptance_receipts` = 0 hits |
| HTTP route | `crates/agileplus-api/src/routes/acceptance.rs` (`2647f50be88f`) | **ABSENT** | no `acceptance.rs` in either routes dir; no `/{slug}/accept` or `/acceptance-receipt` handler |
| gRPC service | `crates/agileplus-grpc/src/acceptance.rs` (`fc0a11de68a4`) | **ABSENT** | no `acceptance.rs` in either grpc src dir |
| gRPC server bootstrap | `crates/agileplus-grpc/src/acceptance_server.rs` (`12e1200c96bf`) | **ABSENT** | same |
| Test — HTTP | `crates/agileplus-api/tests/atomic_acceptance_http.rs` (`42a3c9341a68`) | **ABSENT** | no `atomic_acceptance*` file anywhere in `crates/` |
| Test — sqlite (api) | `crates/agileplus-api/tests/atomic_acceptance_sqlite.rs` (`567debe4baa1`) | **ABSENT** | same |
| Test — gRPC | `crates/agileplus-grpc/tests/atomic_acceptance_rpc.rs` (`59f684b8b586`) | **ABSENT** | same |
| Test — sqlite (repo) + fixture | `crates/agileplus-sqlite/tests/atomic_acceptance.rs` (`79de1addcec8`), `.../atomic_acceptance/fixture.rs` (`52b48fb98365`) | **ABSENT** | same |
| Traceability test (related, different concern) | `crates/agileplus-domain/tests/acceptance_traceability_integration_test.rs` (`7c9b0e5532cc`, 13,388 B) | **PRESENT but OLDER** | local `crates/agile-plus/crates/agileplus-domain/tests/acceptance_traceability_integration_test.rs`, 384 lines — different revision, and it is traceability, not atomic acceptance |
| Declarative probe engine (name-adjacent) | n/a | **PRESENT but DIFFERENT** | `crates/acceptance-contract/` (phenotype-tooling) — probe/scorecard engine, no receipt/atomicity model |

**Nothing in the tree qualifies as "renamed".** No local file implements accept-feature semantics under a different name — the identifier sweep across 13 upstream type/method names and 3 schema/method names returns zero hits, and the API surface (`/{slug}/accept`, `/{slug}/acceptance-receipt`) has no counterpart.

### 4.1 Explicit unknowns (not asserted either way)

1. **Upstream commit topology.** Whether `8699676` is the tip of `main` and which upstream commits introduced the slice was not walked (no `gh api .../commits` history query was spent). The atomic-acceptance code exists at that SHA; its authoring history is **unknown**.
2. **Upstream file-vs-directory shape.** The recursive tree at `8699676` shows `crates/agileplus-sqlite/src/repository/acceptance/mod.rs` (a directory module) but `crates/agileplus-grpc/src/acceptance.rs` and `crates/agileplus-api/src/routes/acceptance.rs` (flat files). Whether the grpc/api sides have companion `acceptance/` directories elsewhere in that tree is **unknown** — the tree was filtered on `accept|receipt`, so a companion directory named differently (e.g. `crates/agileplus-grpc/src/acceptance/`) would still have been caught by the name filter, but any file whose *contents* hold acceptance logic under an unrelated filename would not.
3. **Snapshot's upstream base SHA.** `crates/agile-plus/` carries no recorded upstream commit SHA in the files inspected (`_branches.txt` lists branch names including `main` but no SHA; `.work-audit/` and `AUDIT_INDEX.md` were not read). The snapshot's exact upstream base is **unknown**; the migration ceiling (`026` vs `030`) bounds it as strictly older than the introduction of `030_atomic_acceptance.sql`.
4. **`crates/agile-plus/.work-audit/` and `AUDIT_INDEX.md`** were not read; they may record known-gap lists. **Not read.**
5. **Behavioural parity of the upstream slice** was not exercised — no upstream code was built and no test was run (read-only mandate).

---

## 5. Implications

1. **The standalone repo is the canonical owner and is ahead.** `crates/ABSORPTION_MANIFEST.md` states `agileplus-*` → "canonical in `<REDACTED>/AgilePlus` (staging copies removed from Agentora 2026-06-17)". The atomic-acceptance slice post-dates the local snapshot, so **no absorption work is pending for it in PhenoShared** — it was never absorbed because it did not exist yet at snapshot time. PhenoShared's `crates/agileplus-*` split crates are an independent, *older-generation* port (migrations `001`–`017`, no `execution` port module, no application crate), not a copy of `8699676`.
2. **No "missing absorption" incident here.** The gap is a snapshot-age gap, not a dropped-file gap. A forensic that diffed only `crates/agile-plus/` against upstream `main` would report the same absent files and could wrongly conclude "absorption dropped 9 files"; the migration-number evidence rules that out.
3. **If parity is wanted in PhenoShared**, the port is not a file copy. It requires: creating `crates/agileplus-application` (absent), adding `domain/acceptance.rs` + `ports/terminal_acceptance.rs` to `agileplus-domain`, adding `repository/acceptance/` + migration `030` to `agileplus-sqlite`, adding `routes/acceptance.rs` to `agileplus-api`, adding `acceptance.rs`/`acceptance_server.rs` to `agileplus-grpc`, and restoring the four test suites. The upstream `AtomicAcceptancePort`/`TerminalAcceptancePort` split, the DB-level immutability triggers, and the "preflight is not a token" separation are the load-bearing properties that must survive any re-homing.
4. **Naming collision risk.** `crates/acceptance-contract/` vs upstream `acceptance` semantics: both use the word "acceptance" for unrelated things. Any future consolidation should rename to disambiguate (upstream side: "terminal acceptance" / "acceptance receipt"; local side: "requirement scorecard").

---

## 6. Method and evidence trail

- **Standalone side:** `gh api "repos/KooshaPari/AgilePlus/git/trees/8699676312dfcd787435221a7926a407af920fc6?recursive=1"` (`truncated=false`, 5,324 entries) filtered for `accept|receipt`; then `gh api "repos/KooshaPari/AgilePlus/contents/<path>?ref=8699676" -H "Accept: application/vnd.github.raw"` for the domain, application, HTTP, gRPC and migration sources.
- **Local side:** `find`/`ls` over `crates/` bounded to depth 6; repo-rooted `grep -rl` (never `$HOME`, never `find /`) for the upstream identifier set; `git log --oneline -- crates/agile-plus`; root `Cargo.toml` member inspection.
- **Tool-call budget:** 8 read-only investigative calls, then artifact delivery. No writes to the repo, no `git` mutation, no test execution, no build.
- **Search hygiene:** all searches rooted at the repo (never `$HOME`/`/`); `grep -rl` used rather than `grep -r`/`find` recursion; no unbounded scans.

### Reproduce the negative

```bash
cd ~/CodeProjects/Phenotype/repos/PhenoShared
grep -rl -E 'AcceptFeatureCommand|accept_feature_atomic|AtomicAcceptancePort|TerminalAcceptancePort|commit_terminal_acceptance|FeatureAcceptanceReceipt|AcceptanceOutcome|AcceptedCandidate|validate_candidate' \
  crates/ 2>/dev/null | grep -v '/target/'
# → no output
```

```bash
gh api "repos/KooshaPari/AgilePlus/git/trees/8699676312dfcd787435221a7926a407af920fc6?recursive=1" \
  --jq '.tree[] | select(.type=="blob") | select(.path|test("accept|receipt";"i")) | "\(.sha[0:12]) \(.size)\t\(.path)"'
# → the 15-file table in §2
```
