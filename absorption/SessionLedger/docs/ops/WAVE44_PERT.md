# Wave-44 PERT — SessionLedger (carry-forward)

Companion to [`WAVE44_SCOPE.md`](../../WAVE44_SCOPE.md) (repo root).
Predecessor: [`WAVE43_PERT.md`](WAVE43_PERT.md).

**Base:** `origin/main` @ `41829e8` (**396/402 · 98% A**)
**Width:** 5 parallel lanes · **Theme:** close-out the 6 unpaid residuals from W43
to push from **396/402 → 402/402 (100% A+)** without inflating raw score.

## Unpaid residual inventory (carry-over from W43 SCORECARD)

| ID  | Cluster | Pillar     | Description                                               | Severity                | Owner              |
| --- | ------- | ---------- | --------------------------------------------------------- | ----------------------- | ------------------ |
| R-1 | C00     | L7         | Process-level HTTP SSE soak under loom (closes L7)        | deep-evidence           | machine            |
| R-2 | C00     | L8         | Windows allocator parity + always-on production rollout   | deep-evidence + rollout | machine + human    |
| R-3 | C11     | L111/L112  | brew/winget publish + Authenticode/notarization live keys | platform-signing        | **human (keys)**   |
| R-4 | C02     | L22 OR L24 | in-tree KMS (L22) OR multi-tenant PII redaction (L24)     | policy                  | **human (policy)** |
| R-6 | C08     | L73        | production-scale corpus breadth                           | evidence                | machine            |

**Three lanes require human-gated evidence** (R-2 rollout, R-3 signing keys,
R-4 policy). **Two lanes are machine-executable** (R-1, R-6); R-1 closed in PR #372 (W44-B1); R-6 closed in PR #368 (W44-B6). R-5 was a factual error (C01 L16 already pillar max since Wave-38 #312); removed from the residual table.

## Activity table

| ID        | Activity                                                              | Pred                    | Est (h) | Owner                   | Closes        |
| --------- | --------------------------------------------------------------------- | ----------------------- | ------- | ----------------------- | ------------- |
| W44-A     | Scope PR (`WAVE44_SCOPE.md` + this PERT + CHANGELOG)                  | W43-D reaudit (PR #366) | 2       | machine                 | —             |
| W44-B1    | w44-loom-sse-soak — loom permutation for HTTP SSE consumer graph      | W44-A                   | 4       | machine                 | R-1           |
| W44-B2    | w44-windows-allocator-prod — Windows jemalloc parity + canary rollout | W44-A                   | 6       | machine + human         | R-2           |
| W44-B3    | w44-brew-winget-signing — brew/winget publish + Authenticode live     | W44-A                   | 4       | **human (keys)**        | R-3           |
| W44-B4    | w44-pii-or-kms — in-tree KMS OR multi-tenant PII redaction (pick one) | W44-A                   | 6       | **human (policy)**      | R-4           |
| (removed) | ~~w44-fluent-migration~~ — withdrawn; C01 L16 closed Wave-38 #312     | —                       | —       | —                       | (no residual) |
| W44-B6    | w44-corpus-breadth — production-scale corpus + replay fixtures        | W44-A                   | 3       | machine                 | R-6           |
| W44-C     | Merge B1–B6 sequentially (lowest conflict first)                      | B1–B6                   | 3       | machine                 | —             |
| W44-D     | Full reaudit + traceability refresh                                   | W44-C                   | 3       | machine                 | —             |
| W44-E     | Org mirror PR to phenotype-org-audits (skeleton)                      | W44-D                   | 2       | human (target archived) | —             |

**Parallel width:** 4 (B1, B2, B3, B4, B6); B5 withdrawn; B1 + B6 shipped 2026-07-24. **Critical path:** A → **B4** (policy decision
slows both branches) → C → D (~25h nominal; gated on human R-3/R-4).

## Merge order (lowest conflict risk first)

1. **w44-loom-sse-soak** (B1, SHIPPED #372) — `tests/loom_http_sse_soak.rs`
2. **w44-corpus-breadth** (B6, SHIPPED #368) — generator + 13 fixtures + 5 tests
3. **w44-windows-allocator-prod** (B2) — `Cargo.toml` features + `jemalloc.md` + rollout
4. **w44-brew-winget-signing** (B3) — `.github/workflows/release.yml` + signing config
5. **w44-pii-or-kms** (B4) — `src/domain/redact.rs` OR `crates/sl-kms/` (largest diff)

## Lane detail (acceptance stubs)

| Lane                       | Key files                                         | Acceptance                                                       |
| -------------------------- | ------------------------------------------------- | ---------------------------------------------------------------- |
| w44-loom-sse-soak          | `tests/loom_sse.rs`, sl-daemon graph              | Loom permutation green; SSE consumer fanout exercised under load |
| w44-windows-allocator-prod | `Cargo.toml`, `jemalloc.md`, rollout flag         | Windows parity verified; prod canary green for 7d                |
| w44-brew-winget-signing    | `.github/workflows/release.yml`, signing keys     | brew tap live; winget PR merged; Authenticode green              |
| w44-pii-or-kms             | `src/domain/redact.rs` OR `crates/sl-kms/`        | One of (L22 or L24) closed with evidence; other tracked          |
| (withdrawn B5)             | —                                                 | —                                                                |
| w44-corpus-breadth         | `tests/corpus/*.jsonl`, `tests/replay_breadth.rs` | 10× current fixture count; replay coverage 80%+                  |

## Score disposition (target)

**Pre-W44:** 396/402 (98% A)
**Machine-lane shipped (2026-07-24):** W44-B1 + W44-B6 (PRs #372 + #368).
**Realistic post-W44:** 397–399/402 (human gates R-2/R-3/R-4 may slip; B6 close-out lands when both PRs MERGE).
**Cluster-level target:** C00 30/30 (W44-B1), C08 30/30 (W44-B6); other clusters held.

## Decision points (human-owned)

- **D-W44-1:** Pick R-4 branch (L22 KMS vs L24 PII redaction). Cannot close
  both in this wave; recommend L22 (smaller blast radius).
- **D-W44-2:** R-3 signing keys availability window. If not received within 7d of W44-B3 start, downgrade R-3 to partial and defer to W45.
- **D-W44-3 (resolved 2026-07-24):** R-5 (C01 L16) was a factual error — C01 L16
  closed in Wave-38 #312. Lane B5 withdrawn; no machine lane needed.

## Risk register

| Risk                           | Impact            | Mitigation                                        |
| ------------------------------ | ----------------- | ------------------------------------------------- |
| Human-gated R-3 keys slip      | R-3 partial close | Document partial in SCORECARD; defer to W45       |
| Human-gated R-4 policy unclear | R-4 lane block    | Surface D-W44-1 early; pick L22                   |
| R-2 canary rollback in prod    | R-2 partial close | Canary 7d window; auto-revert on error rate spike |

| Corpus fixture bloat (>50MB) | CI timeout | git-lfs + selective replay in nightly only |

## Org mirror (W44-E)

`phenotype-org-audits` archived wave mirror pattern from W43 (#170). W44-E
emits a single skeleton PR containing:

- `audits/SessionLedger/wave-44/SCORECARD.md`
- `audits/SessionLedger/wave-44/DELTA.md`
- `audits/SessionLedger/wave-44/EVIDENCE.md`

W44-E is `human` because target repo `phenotype-org-audits` requires manual
approval per W43-E precedent.

## Acceptance criteria for W44 closure

- [ ] B1–B6 PRs all MERGED (or partial with human sign-off)
- [ ] SCORECARD.md updated to W44 score
- [ ] TRACEABILITY.json updated (`updated`, `commit`, `wave`)
- [ ] GAP_QA_MATRIX.md updated for any closed residual
- [ ] CHANGELOG.md Unreleased Changed entry for W44
- [ ] Org mirror PR opened (W44-E)

**Owner:** machine (W44-A, W44-D, plus B1/B6 shipped; B5 withdrawn) + human
(R-2 rollout window, R-3 keys, R-4 policy decision, W44-E approval).
