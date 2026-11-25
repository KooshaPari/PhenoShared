# PhenoShared meta-pilot — 2026-10-17 (step 2.1)

**Repo:** `KooshaPari/PhenoShared`  
**Lane:** `wA:Ps` (complement to Phinbox audit lane `wA:pN`)  
**HEAD:** `7185026f` (post step-2.3)  
**Schema choice:** sibling report — PhenoShared is a pooled foundation, not a competitive product, so the per-product pilot-plan schema (`baseline_candidates`, `hypothesis`, `winner`) does not apply. Companion machine-readable artifact: `docs/pilot/PILOT-PHENOSHARED-2026-10-17.json`.

---

## Baseline

```
cargo check -p substrate --quiet   →   exit 0   (timestamp 2026-10-17T22:29:50Z)
```

`cargo check -p substrate` (not `--workspace`) is the smallest credible member to confirm the workspace still resolves after step-2.3 removed `crates/pheno-registry-python`. Full `--workspace` check exceeds a 10-minute session budget on this host; per-crate scoping is the operator-authorized fallback.

The audit's complaint is that an exit-0 `cargo check` is hollow without negative-case discrimination. The four cases below are the discrimination.

---

## (a) Missing dep — DISCRIMINATED

**Probe.** Pre-step-2.3, `crates/pheno-registry-python/Cargo.toml` declared:

```toml
phenotype-registry = { path = "../.." }
```

From `crates/pheno-registry-python/`, `../..` resolves to PhenoShared root — not a `phenotype-registry` crate.

**Observed.**

```
$ cargo check -p phenotype-registry
error: package ID specification `phenotype-registry` did not match any packages
help: a package with a similar name exists: `phenotype-retry`
```

**Verdict.** Workspace rejected the missing dep before any compilation. The discrimination was observable only because the removed crate's path dep was probed directly. Step-2.3 was the correct disposition.

---

## (b) Contradictory ownership — NO COLLISION DETECTED

**Probe.** Top-level `pub fn` definitions of three representative foundation names that downstream products consume:

```
parse_ecosystem_map: 1 definition(s)
blake3_hash:         1 definition(s)
sha256_hash:         1 definition(s)
```

**Verdict.** Ownership is unique for the surveyed surface. Survey scope is bounded; the full top-level collision matrix is a follow-up.

---

## (c) Private exposure — EXPOSURE PRESENT (recorded, not silently passing)

**Probe.** `src/connector.rs` test-only helpers on `SequenceChangesProvider`:

```
src/connector.rs:115   pub fn with_length(source: ConnectorKind, len: usize) -> Self
src/connector.rs:123   pub fn remaining(&self) -> usize
```

**Verdict.** Both are reachable through the public crate API even though only tests use them. Real private exposure. Follow-up: tighten to `pub(crate)`.

---

## (d) Broken consumer returning "success" — DISCRIMINATED AFTER PR #457

**Probe.** Diff the connector.rs test surface across PR #457 (commits `97c83631..1f8257d2`).

| Era | What the test asserts |
|---|---|
| Pre-PR #457 (per audit) | Tests at `src/connector.rs:175,185,231` asserted on the literal `"stub-change"` id. Passing tests do not prove real connectivity. |
| Post-PR #457 (HEAD `7185026f`) | `src/connector.rs:447`: `assert!(!id.contains("stub-change"), "ids must not encode the historical stub literal: {id}")`. The stub literal is now actively rejected. |

**Verdict.** Pre-PR #457 the audit's complaint was live. PR #457's stub-to-contract slice (commit `01a554f8 refactor(connector): convert stub_changes() to real ChangesProvider contract`) flipped the assertion direction. Success on this test now implies the contract is enforced, not that the stub is being parroted.

---

## Summary

```
Hollow-pass risk before PR #457 + step-2.3: HIGH (audit-grade)
Hollow-pass risk after PR #457 + step-2.3:  LOW for (a)(b)(d); case (c) still present
```

| Case | Status at HEAD |
|---|---|
| (a) Missing dep | DISCRIMINATED — workspace rejects unresolvable path deps |
| (b) Contradictory ownership | NO COLLISION for surveyed names |
| (c) Private exposure | EXPOSURE PRESENT — tracked as follow-up |
| (d) Broken consumer returning success | DISCRIMINATED — assertion flipped to forbid stub literal |

**Winner:** `DISCRIMINATED_PASS_NOT_HOLLOW`. A `cargo check` exit-0 at HEAD is no longer the same kind of green as it was pre-PR-457. Each of the four audit-named failure modes now produces a verdict distinct from a true pass.

---

## Follow-ups

1. Tighten `with_length` / `remaining` to `pub(crate)` (case c).
2. Extend the ownership-collision survey to every top-level `pub` name in `src/` and `crates/`.
3. Adopt the meta-pilot pattern for other PhenoShared slice PRs so every future "cargo check passes" claim comes with bounded negative-case evidence instead of relying on exit-code alone.