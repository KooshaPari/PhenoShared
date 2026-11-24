# DOCS_REVIEW.md — phenotype-canonicalization

**Reviewer:** Jcode  
**Date:** 2026-09-17  
**Method:** Read all markdown, validate all JSON, run all tools and tests, verify SHA256 checksums, cross-reference data integrity

---

## Overall Accuracy Score: 82/100

The repo is an unusually well-structured research packet. It is honest about what it is and is not, and the machine-readable artifacts are internally consistent. The main issues are stale checksums, a Python version gate that blocks test execution on the system Python, and one oversized file.

---

## Per-Section Assessment

### README.md (85/100)
- **Accurate:** All numeric claims (24 decisions, 15 findings, 13 profiles, 36 routes, 3 trees, 10 WPs) match actual data exactly.
- **Accurate:** Scope disclaimer ("does not certify all 46 repositories") is correct and honest.
- **Accurate:** Reading order is well-structured and documents reference each other.
- **Issue:** Claims the tools "were executed here with Python 3.13.5" but does not warn that Python 3.9 (the system default on this Mac) will fail on `audit.py` import due to `tomllib`. The README says "Python 3.11 or newer" is required but does not prominently state this as a hard gate.
- **Issue:** SHA256SUMS for README.md itself is stale (mismatch after edits).

### REVIEW-REPORT.md (78/100)
- **Accurate:** File-by-file assessments are fair and evidence-based.
- **Accurate:** Cross-reference matrix to docs-5 is useful.
- **Issue:** Claims "Files reviewed: 5 .md files + 10 machine-readable artifacts" but the table lists 10 items under "Machine-readable artifacts (not reviewed in detail)". The "not reviewed in detail" qualifier contradicts the impression of thorough review.
- **Issue:** Recommendation to merge decisions into docs-5/adr/ assumes those ADRs exist and overlap. This is an assertion without verification. The review itself notes the reviewer did not deeply verify.
- **Stale:** The review was generated in a prior session. It should note its own limitations.

### AUDIT-RUNBOOK.md (92/100)
- **Excellent:** Methodology is sound and appropriately scoped. Clear 10-step procedure.
- **Excellent:** Each step has explicit "do not" guardrails (e.g., "do not publish remote URLs containing credentials").
- **Minor issue:** Steps reference tools in the packet (e.g., `python -I /absolute/path/to/packet/tools/audit.py`) but the `-I` flag is Python 3.1+ and may confuse users on systems where `python` resolves to 2.x.
- **Minor issue:** Step 4 says "use the qualified package manager's frozen/locked resolution mode" but does not specify which tool this refers to.

### SOURCE-INDEX.md (75/100)
- **Excellent:** Provenance tracking is thorough. Every GitHub source has blob SHA, commit SHA, and explicit scope notes.
- **Excellent:** Liveness verification table at the end is a valuable addition.
- **Issue:** File is 684 lines (exceeds the 500-line hard limit per AGENTS.md). Should be split or compressed.
- **Issue:** Many source entries note "scope note: Selected content read through GitHub connector; no product execution" which is honest but means the "verified-on: 2026-09-17" liveness table is misleading -- it records that the source was checked for existence, not that its content was verified.
- **Minor issue:** L01 references a `file_id` from a library document. This is opaque and not resolvable by the reader.

### REPORT.md (88/100)
- **Accurate:** Substantive content, 310 lines, well within limits.
- **Accurate:** 24 decisions are properly scoped with acceptance criteria and exception contracts.
- **Accurate:** All decisions have `mutation_authority: false` which matches the "read-only research and handoff" mode.
- **Minor issue:** Some decisions (e.g., D11, D18, D21, D24) reference GPU kernel and performance optimization topics that seem out of scope for a "canonical tooling" packet. The user request (U01) was about JS/Python tooling. These may be legitimate extensions but the scope creep is not explained.

### decisions.json (95/100)
- **Valid JSON** and validates against `schemas/decisions.schema.json`.
- **All 24 required fields present** in every decision.
- **All `mutation_authority` values are `false`** -- consistent with read-only mode.
- **All evidence references (G01-G23, W01-W24, U01) are valid source IDs** from SOURCE-INDEX.md.
- **Minor issue:** `alternatives_considered` arrays vary in quality. D02 has 5 alternatives ("Use as-is", "Extend owner", etc.) while some decisions have only 1-2. The depth is uneven.

### profiles.json (90/100)
- **Valid JSON.**
- **All 13 profiles reference valid decision IDs** (cross-reference check passes).
- **All profiles have consistent `scope_resolution` text** ("component manifest required; repository name alone is insufficient").
- **Minor issue:** Profiles are abstract (e.g., "js-library", "web-react", "gpu-kernel"). No actual repository is mapped to a profile. The profiles define *what* to check, not *where* it is.

### pattern-matrix.json (88/100)
- **Valid JSON.** 36 routes.
- **All decision references valid.**
- **Consistent structure** with `id`, `question`, `default`, `alternative_trigger`, `acceptance`, `decision_id`, `status`.
- **All status values are `proposed_branching_rule_not_current_absence_claim`** which is appropriately cautious.

### decision-trees.json (92/100)
- **Valid JSON.** 3 trees with proper node structure.
- **No cycles** (verified by test `test_tree_cycle`).
- **Proper branching** with `when_true`/`when_false` and `ACTION:` leaves.
- **Excellent:** `execution_semantics` header warns "Predicates require anchored facts; unknown is not false or pass."

### coverage.json (95/100)
- **Excellent honesty.** Explicitly lists what was NOT done:
  - `full_git_graph_audit: false`
  - `full_repository_checkout_or_build: false`
  - `installed_consumer_verification: false`
  - `hosted_workflow_execution_verified: false`
- **Clear limitations list** with 6 specific items.
- **`next_unresolved`** lists 5 concrete next steps.

### audit/findings.json (90/100)
- **Valid JSON.** 15 findings.
- **All evidence references valid.**
- **Consistent structure** with `observation`, `interpretation`, `countercase`, `acceptance_proof`, `priority`, `kind`, `status`.
- **All `product_execution: "not_run"`** -- consistent with read-only mode.
- **Minor issue:** Priority distribution is 4 P0, 5 P1, 6 P2. The P0 findings are well-justified but the P2 findings seem speculative (e.g., F14 about PhenoDocs/VitePress needing OXC qualification -- the docs may never need OXC).

### migration/work-packages.json (90/100)
- **Valid JSON.** 10 work packages.
- **Dependency graph is valid** (WP03 depends on WP01, WP05 depends on WP02+WP04, etc.).
- **All `state: "proposed_not_executed"`** -- consistent.
- **All `resource_claims` are identical** ("shared manifests/lockfiles/releases require one integration writer"). This is boilerplate that should be customized per WP.
- **All `rollback` fields are identical** -- same boilerplate concern.

### tools/ (85/100)
- `audit.py` (199 lines), `receipt_validator.py` (78 lines), `validate_packet.py` (138 lines) -- all under limits.
- **`validate_packet.py` works correctly** on this system (exit 0, VALID output).
- **`audit.py` fails on Python 3.9** due to `tomllib` import (Python 3.11+ only). This is documented in README but the error message is a raw `ModuleNotFoundError` rather than a friendly "requires Python 3.11+" message.
- **`receipt_validator.py`** is clean and well-tested.

### tests/ (80/100)
- `test_packet.py` (97 lines, 12 tests) -- **all pass** on Python 3.9.
- `test_tools.py` (147 lines) -- **fails to import** on Python 3.9 due to `audit.py` dependency on `tomllib`.
- The test suite has a **hidden Python version gate**: `test_packet.py` works everywhere, but `test_tools.py` requires 3.11+.
- Tests that DO run are comprehensive and well-written: negative controls, malformed input, cycle detection, schema validation.

### verification/ (90/100)
- `summary.json` records 40 tests passed, 98.2% statement coverage, 95.1% branch coverage -- all on Python 3.13.5.
- `packet-validation.json` confirms VALID structure with jsonschema.
- `typescript-multiple-projects.json` contains the experimental results.
- **Consistent** with README claims about what was executed.

### SHA256SUMS (70/100)
- **2 of 37 checksums are stale**: README.md and SOURCE-INDEX.md.
- The other 35 checksums match.
- This means SHA256SUMS was generated before the final edits to README.md and SOURCE-INDEX.md. Should be regenerated.

---

## Specific Issues Found

| # | File | Line/Ref | Severity | Description |
|---|------|----------|----------|-------------|
| 1 | SHA256SUMS | L2, L5 | Medium | README.md and SOURCE-INDEX.md checksums stale after edits |
| 2 | tools/audit.py | L16 | Medium | `import tomllib` fails on Python 3.9; no friendly error message |
| 3 | tests/test_tools.py | L12 | Medium | `import audit` fails on Python 3.9; test suite partially broken |
| 4 | SOURCE-INDEX.md | Full | Medium | 684 lines exceeds 500-line hard limit |
| 5 | README.md | L31 | Low | States "Python 3.11 or newer" but doesn't highlight it as a hard gate |
| 6 | REVIEW-REPORT.md | L6 | Low | "not reviewed in detail" qualifier undermines the review's authority |
| 7 | migration/work-packages.json | All | Low | All `resource_claims` and `rollback` fields are identical boilerplate |
| 8 | audit/findings.json | F14 | Low | P2 priority for docs tooling qualification seems speculative |
| 9 | L01 in SOURCE-INDEX.md | L346-349 | Low | `file_id` is opaque and not resolvable |
| 10 | coverage.json | Full | Info | 6 limitations honestly listed; no actual issues, just honest scope |

---

## Recommendations

1. **Regenerate SHA256SUMS** after all edits are complete. This is a one-command fix.
2. **Add a friendly Python version check** to `audit.py` (e.g., `if sys.version_info < (3, 11): print("Requires Python 3.11+"); sys.exit(1)` before the `import tomllib`).
3. **Split SOURCE-INDEX.md** into `SOURCE-INDEX.md` (summary) + `SOURCE-DETAIL.md` (full provenance), or compress the liveness table.
4. **Customize `resource_claims` and `rollback`** per work package in `migration/work-packages.json` rather than using identical boilerplate.
5. **Remove or downgrade L01** from SOURCE-INDEX.md since the `file_id` is not resolvable.
6. **Note in REVIEW-REPORT.md** that it was generated in a prior session and may not reflect the final state.

---

## Repo Description vs. Reality

**README claims:** "audit and agent handoff" packet for canonical tooling engineering.

**Reality:** This is an accurate description. The repo contains:
- A research snapshot (not a deployed policy)
- Machine-readable decisions, profiles, and patterns
- Reference tools (collector, receipt validator, packet validator)
- Test fixtures and negative controls
- A bounded migration plan (not executed)

**The description matches reality.** The key qualifier is that this is "proposed operationalization, not deployed policy" -- which the README states prominently.

---

## Summary

This is one of the better-structured research packets in the ecosystem. The honesty about scope limits, the machine-readable cross-references, the negative control tests, and the explicit coverage tracking are all exemplary. The issues are minor: stale checksums, a Python version gate, one oversized file, and some boilerplate in work packages.
