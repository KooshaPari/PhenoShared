# ResearchLedger Release Candidate P1 Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the release candidate fail closed for consent, public-reference retrieval, release verification, and local evidence capture.

**Architecture:** Keep consent decisions and durable job state in SQLite, but apply the batch limit only after eligibility filtering and recheck at the worker boundary. Keep network policy deterministic at URL validation; do not overclaim DNS-rebinding protection until the HTTP resolver is pinned. Keep scripts as independently tested release gates under Bun/Vitest.

**Tech Stack:** Rust, rusqlite, reqwest, Tauri, Bun, Vitest, Node-compatible ESM scripts.

---

### Task 1: Make reference job selection and execution consent-safe

**Files:**

- Modify: `apps/desktop/src-tauri/src/storage.rs:374-400`
- Modify: `apps/desktop/src-tauri/src/lib.rs:971-1045, tests`

- [ ] **Step 1: Write failing Rust tests**

Add a test with one revoked pending reference followed by one active-consent pending reference and request a limit of one. Assert the returned job is the later active URL. Add a worker-boundary test that revokes consent after dequeue and asserts no fetch callback is invoked and the job is recorded blocked.

- [ ] **Step 2: Run the focused tests to verify RED**

Run: `RESEARCHLEDGER_SKIP_BUNDLE_RESOURCE_VALIDATION=1 cargo test --manifest-path apps/desktop/src-tauri/Cargo.toml pending_reference -- --nocapture`

Expected: the eligible later job is omitted or the revoked claimed job proceeds to fetch.

- [ ] **Step 3: Implement the smallest behavior change**

Query pending rows by id without SQL `LIMIT`; append only currently allowed decisions and stop when `jobs.len() == limit`. At the worker boundary, reopen the database, decide the canonical target URL again, mark a denied job `blocked` with a revocation reason, and continue before any network request.

- [ ] **Step 4: Run focused Rust tests to verify GREEN**

Run the command from Step 2.

Expected: both new tests pass.

### Task 2: Expand public URL policy without overstating DNS guarantees

**Files:**

- Modify: `apps/desktop/src-tauri/src/reference_fetch.rs:109-158, tests`
- Modify: `docs/A_PLUS_SCORECARD.md`

- [ ] **Step 1: Write failing URL-policy tests**

Extend `rejects_private_and_credentialed_urls` with `http://[::ffff:127.0.0.1]/`, `http://100.64.0.1/`, `http://224.0.0.1/`, `http://255.255.255.255/`, and `http://192.0.2.1/`; each must return `UnsafeUrl`.

- [ ] **Step 2: Run the test to verify RED**

Run: `RESEARCHLEDGER_SKIP_BUNDLE_RESOURCE_VALIDATION=1 cargo test --manifest-path apps/desktop/src-tauri/Cargo.toml rejects_private_and_credentialed_urls -- --nocapture`

Expected: at least one public-policy test unexpectedly succeeds.

- [ ] **Step 3: Implement address classification**

Normalize IPv4-mapped IPv6 before applying IPv4 policy. Reject loopback, private, link-local, unspecified, shared carrier-grade NAT (`100.64.0.0/10`), documentation/reserved ranges, multicast, and broadcast. Preserve allowed globally routable addresses. Record hostname resolution as preflight only in the scorecard unless a verified resolver pin is added.

- [ ] **Step 4: Run the test to verify GREEN**

Run the command from Step 2.

Expected: all listed unsafe URLs reject.

### Task 3: Make scripts fail closed and protocol-correct

**Files:**

- Modify: `scripts/_capture_common.mjs:742-835`
- Modify: `scripts/smoke_retrieval_reranker.mjs:440-525`
- Modify: `scripts/verify_csp.mjs:32-55`
- Modify: `scripts/release_macos.mjs:132-165`
- Modify/Create: corresponding `*.test.mjs` files under `scripts/`

- [ ] **Step 1: Write failing Bun/Vitest tests**

Test that an empty capture rejects with `CAPTURE_EMPTY` and closes the browser context. Test a mixed MLX/TEI endpoint list and assert each request's serialized body matches its target engine. Test CSP rejection for `http://localhost:5173` and `ws://localhost:5173`. Test release signature parsing rejects missing `Timestamp=` and an authority that does not contain the configured identity.

- [ ] **Step 2: Run focused tests to verify RED**

Run: `bun run test -- scripts`

Expected: each new test fails because the current scripts serialize empty capture, reuse the primary-engine request body, allow development-source variants, or accept incomplete signature metadata.

- [ ] **Step 3: Implement minimal guards**

Wrap capture collection/write in `try/finally`, assert non-empty after collection and before payload construction, and always close the context. Compute `requestBody(target.engine, ...)` and `requestText` inside the endpoint loop. Reject production source tokens that are wildcard, `ws:`/`wss:`, or parse as loopback/localhost HTTP(S) origins. Pass `signingIdentity` into `verifySignedApplication` and require its authority plus `Timestamp=` before notarization.

- [ ] **Step 4: Run focused tests to verify GREEN**

Run: `bun run test -- scripts`

Expected: all focused script tests pass.

### Task 4: Regress the release candidate

**Files:**

- Modify: `docs/A_PLUS_SCORECARD.md` only if evidence/status wording changed

- [ ] **Step 1: Run suites**

Run: `bun run test && bun run build && bun run verify:csp && bun run verify:resources`

Run: `RESEARCHLEDGER_SKIP_BUNDLE_RESOURCE_VALIDATION=1 cargo test --manifest-path apps/desktop/src-tauri/Cargo.toml --lib && cargo fmt --manifest-path apps/desktop/src-tauri/Cargo.toml -- --check`

Expected: every command exits zero.

- [ ] **Step 2: Record only proved status**

Keep signing, notarization, live GitHub import, and resolver-pinning evidence as open gates unless their real commands/artifacts prove them.

- [ ] **Step 3: Preserve and prepare review**

Run: `python3 /path/to/phenotype/repos/.airlock/bin/airlock-v2.py snapshot "$PWD"`

Expected: a new WIP ref is reported; inspect its SHA and open a successor PR only after all validations and review-thread replies are ready.
