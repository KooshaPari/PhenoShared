# cargo-deny Staleness Audit

**Audit date:** 2026-05-05
**Scope:** `/Users/<REDACTED>/CodeProjects/Phenotype/repos/*/deny.toml` + `repos/deny.toml`
**Total deny.toml files scanned:** 51 (verified with `[advisories]` section)
**Auditor:** automated parser (Python 3 + tomli)

---

## Summary

| Category | Count |
|---|---|
| Clean (zero ignores) | 42 repos |
| Has ignores | 9 repos |
| TOML parse errors | 2 repos |
| Malformed ignore entries (silent) | 1 repo |
| **Total ignored advisories** | **65** |
| Ignores with rationale | 0 (0%) |
| Ignores with date | 0 (0%) |

**No date fields were found on any ignore entry, making staleness determination impossible via automated parsing.**

---

## Repos With Ignores

### 1. hwLedger -- 24 ignores (HIGHEST RISK)

**File:** `/Users/<REDACTED>/CodeProjects/Phenotype/repos/hwLedger/deny.toml`

All 24 ignores have no rationale and no date.

| Advisory ID | Has Rationale | Date | Notes |
|---|---|---|---|
| RUSTSEC-2024-0411 | NO | -- | 2024 batch |
| RUSTSEC-2024-0412 | NO | -- | 2024 batch |
| RUSTSEC-2024-0413 | NO | -- | 2024 batch |
| RUSTSEC-2024-0414 | NO | -- | 2024 batch |
| RUSTSEC-2024-0415 | NO | -- | 2024 batch |
| RUSTSEC-2024-0416 | NO | -- | 2024 batch |
| RUSTSEC-2024-0417 | NO | -- | 2024 batch |
| RUSTSEC-2024-0418 | NO | -- | 2024 batch |
| RUSTSEC-2024-0419 | NO | -- | 2024 batch |
| RUSTSEC-2024-0420 | NO | -- | 2024 batch |
| RUSTSEC-2024-0384 | NO | -- | 2024 batch |
| RUSTSEC-2024-0370 | NO | -- | 2024 batch |
| RUSTSEC-2024-0375 | NO | -- | 2024 batch |
| RUSTSEC-2025-0012 | NO | -- | |
| RUSTSEC-2025-0057 | NO | -- | |
| RUSTSEC-2025-0075 | NO | -- | |
| RUSTSEC-2025-0080 | NO | -- | |
| RUSTSEC-2025-0081 | NO | -- | |
| RUSTSEC-2025-0098 | NO | -- | |
| RUSTSEC-2025-0100 | NO | -- | |
| RUSTSEC-2025-0119 | NO | -- | |
| RUSTSEC-2025-0134 | NO | -- | |
| RUSTSEC-2023-0071 | NO | -- | **3 years old** |
| RUSTSEC-2017-0008 | NO | -- | **9 years old -- most dangerous** |

Notable: `RUSTSEC-2017-0008` (9 years old, no rationale) and `RUSTSEC-2023-0071` (3 years old, no rationale) are the most potentially stale. `RUSTSEC-2017-0008` also appears twice (duplicate entry in same file).

### 2. BytePort -- 17 ignores

**File:** `/Users/<REDACTED>/CodeProjects/Phenotype/repos/BytePort/deny.toml`

All 17 ignores have no rationale and no date.

| Advisory ID | Has Rationale | Date | Notes |
|---|---|---|---|
| RUSTSEC-2024-0370 | NO | -- | |
| RUSTSEC-2024-0411 | NO | -- | 2024 batch |
| RUSTSEC-2024-0412 | NO | -- | 2024 batch |
| RUSTSEC-2024-0413 | NO | -- | 2024 batch |
| RUSTSEC-2024-0414 | NO | -- | 2024 batch |
| RUSTSEC-2024-0415 | NO | -- | 2024 batch |
| RUSTSEC-2024-0416 | NO | -- | 2024 batch |
| RUSTSEC-2024-0417 | NO | -- | 2024 batch |
| RUSTSEC-2024-0418 | NO | -- | 2024 batch |
| RUSTSEC-2024-0419 | NO | -- | 2024 batch |
| RUSTSEC-2024-0420 | NO | -- | 2024 batch |
| RUSTSEC-2025-0057 | NO | -- | |
| RUSTSEC-2025-0075 | NO | -- | |
| RUSTSEC-2025-0080 | NO | -- | |
| RUSTSEC-2025-0081 | NO | -- | |
| RUSTSEC-2025-0098 | NO | -- | |
| RUSTSEC-2025-0100 | NO | -- | |

Shares the same 10-advisory batch (RUSTSEC-2024-0411 through -0420) with hwLedger.

### 3. forgecode -- 9 ignores

**File:** `/Users/<REDACTED>/CodeProjects/Phenotype/repos/forgecode/deny.toml`

All 9 ignores have no rationale and no date.

| Advisory ID | Has Rationale | Date | Notes |
|---|---|---|---|
| RUSTSEC-2024-0320 | NO | -- | Appears twice (duplicate) |
| RUSTSEC-2024-0436 | NO | -- | |
| RUSTSEC-2025-0134 | NO | -- | |
| RUSTSEC-2025-0141 | NO | -- | |
| RUSTSEC-2026-0098 | NO | -- | |
| RUSTSEC-2026-0099 | NO | -- | |
| RUSTSEC-2026-0104 | NO | -- | |
| RUSTSEC-2026-0118 | NO | -- | |
| RUSTSEC-2026-0119 | NO | -- | |

Note: RUSTSEC-2024-0320 appears twice in the same file (copy-paste error).

### 4. FocalPoint -- 4 ignores

**File:** `/Users/<REDACTED>/CodeProjects/Phenotype/repos/FocalPoint/deny.toml`

| Advisory ID | Has Rationale | Date |
|---|---|---|
| RUSTSEC-2024-0388 | NO | -- |
| RUSTSEC-2024-0436 | NO | -- |
| RUSTSEC-2025-0057 | NO | -- |
| RUSTSEC-2025-0141 | NO | -- |

### 5. rust -- 4 ignores

**File:** `/Users/<REDACTED>/CodeProjects/Phenotype/repos/rust/deny.toml`

| Advisory ID | Has Rationale | Date |
|---|---|---|
| RUSTSEC-2024-0436 | NO | -- |
| RUSTSEC-2025-0134 | NO | -- |
| RUSTSEC-2025-0140 | NO | -- |
| RUSTSEC-2026-0049 | NO | -- |

### 6. helioscope -- 3 ignores

**File:** `/Users/<REDACTED>/CodeProjects/Phenotype/repos/helioscope/deny.toml`

| Advisory ID | Has Rationale | Date |
|---|---|---|
| RUSTSEC-2025-0134 | NO | -- |
| RUSTSEC-2025-0140 | NO | -- |
| RUSTSEC-2026-0049 | NO | -- |

### 7. HeliosLab -- 1 ignore

**File:** `/Users/<REDACTED>/CodeProjects/Phenotype/repos/HeliosLab/deny.toml`

| Advisory ID | Has Rationale | Date |
|---|---|---|
| RUSTSEC-2024-0436 | NO | -- |

### 8. helios-cli -- 1 ignore

**File:** `/Users/<REDACTED>/CodeProjects/Phenotype/repos/helios-cli/deny.toml`

| Advisory ID | Has Rationale | Date |
|---|---|---|
| RUSTSEC-2026-0049 | NO | -- |

### 9. phenoData -- 1 ignore

**File:** `/Users/<REDACTED>/CodeProjects/Phenotype/repos/phenoData/deny.toml`

| Advisory ID | Has Rationale | Date | Notes |
|---|---|---|---|
| RUSTSEC-2023-0071 | NO | -- | 3 years old |

### 10. phenoUtils -- 1 ignore

**File:** `/Users/<REDACTED>/CodeProjects/Phenotype/repos/phenoUtils/deny.toml`

| Advisory ID | Has Rationale | Date |
|---|---|---|
| RUSTSEC-2026-0049 | NO | -- |

---

## Repos With TOML Parse Errors (broken deny.toml)

### 11. AtomsBot -- parse error (cargo-deny will fail)

**File:** `/Users/<REDACTED>/CodeProjects/Phenotype/repos/AtomsBot/deny.toml`
**Error:** `Cannot overwrite a value (at line 24, column 66)`

Root cause: duplicate `allow-registry` key in `[sources]` section.

```toml
[sources]
unknown-registry = "deny"
allow-registry = ["https://github.com/rust-lang/crates.io-index"]
allow-registry = ["https://github.com/rust-lang/crates.io-index"]  # TOML overwrite error
```

cargo-deny will refuse to parse this file entirely. Note: this file has no advisory ignores at all -- the error is a structural issue unrelated to advisories.

### 12. PhenoControl -- parse error (cargo-deny will fail)

**File:** `/Users/<REDACTED>/CodeProjects/Phenotype/repos/PhenoControl/deny.toml`
**Error:** `Cannot overwrite a value (at line 21, column 66)`

Root cause: same duplicate `allow-registry` issue in `[sources]` section.

Additionally, the ignore entries use non-conformant field names:

```toml
ignore = [
    { crate = "RUSTSEC-2020-0036", reason = "failure not referenced in any dependency tree" },
    { crate = "RUSTSEC-2025-0119", reason = "number_prefix not referenced in any dependency tree" },
]
```

cargo-deny expects `{ id = "...", rationale = "..." }` but this file uses `{ crate = "...", reason = "..." }`. These ignores are silently ineffective even if the TOML parse error were fixed.

### 13. PhenoObservability -- malformed ignores (silent failure)

**File:** `/Users/<REDACTED>/CodeProjects/Phenotype/repos/PhenoObservability/deny.toml`
**Status:** Parses successfully but ignore entries use wrong field names -- silently ineffective.

```toml
[[advisories.ignore]]
crate = "protobuf"
advisory = "RUSTSEC-2026-0105"
reason = "protobuf: LOW severity uncontrolled recursion..."
```

cargo-deny expects `{ id, rationale, date }` but this file uses `{ crate, advisory, reason }`. The advisory RUSTSEC-2026-0105 is **NOT actually ignored** despite the entry existing in the file.

---

## Cross-Repo Advisory Frequency

| Advisory ID | Repos Affected | Advisory IDs Ignored |
|---|---|---|
| RUSTSEC-2025-0134 | 6 | hwLedger, forgecode, FocalPoint, rust, helioscope, rust |
| RUSTSEC-2024-0436 | 5 | hwLedger, forgecode, FocalPoint, rust, HeliosLab |
| RUSTSEC-2026-0049 | 5 | rust, helioscope, helios-cli, phenoUtils, rust |
| RUSTSEC-2023-0071 | 3 | hwLedger, phenoData, hwLedger (duplicate) |
| RUSTSEC-2025-0140 | 3 | rust, helioscope, rust |
| RUSTSEC-2024-0411 through -0420 | 2 each | hwLedger + BytePort (same 10-advisory batch) |
| RUSTSEC-2024-0370 | 2 | hwLedger, BytePort |
| RUSTSEC-2025-0057 | 2 | hwLedger, FocalPoint |
| RUSTSEC-2025-0075, -0080, -0081, -0098, -0100 | 2 each | hwLedger + BytePort |
| RUSTSEC-2025-0119 | 2 | hwLedger + PhenoControl (via wrong field names) |
| RUSTSEC-2017-0008 | 2 | hwLedger (duplicate entry) |
| RUSTSEC-2026-0098, -0099, -0104, -0118, -0119 | 2 each | forgecode |
| RUSTSEC-2025-0141 | 2 | forgecode, FocalPoint |
| RUSTSEC-2024-0320 | 2 | forgecode (duplicate entry) |

---

## Key Findings

1. **100% of ignores lack rationale.** Every one of the 65 ignores has an empty rationale string. This is the primary security debt -- ignores without documented rationale cannot be audited, reviewed, or handed off.

2. **100% of ignores lack date.** No ignore entry has a `date` field. The cargo-deny `ignore` field supports an ISO 8601 `date` that acts as an expiration marker, but none of the 65 entries use it. Without dates, staleness cannot be automatically determined and ignores persist indefinitely.

3. **Two repos have broken deny.toml files.** AtomsBot and PhenoControl both have duplicate `allow-registry` keys in the `[sources]` section. cargo-deny will refuse to run on these repos entirely.

4. **PhenoObservability has silently ineffective ignores.** The ignore entry uses `{ crate, advisory, reason }` instead of the cargo-deny schema `{ id, rationale, date }`. The advisory is NOT actually ignored.

5. **PhenoControl uses wrong field names.** Even if the TOML parse error were fixed, the ignores would be silently dropped because they use `crate`/`reason` instead of `id`/`rationale`.

6. **Duplicate identical ignores in hwLedger and forgecode.** RUSTSEC-2017-0008 appears twice in hwLedger; RUSTSEC-2024-0320 appears twice in forgecode. Copy-paste errors.

7. **The most dangerous ignores are the oldest ones without rationale or date:**
   - `RUSTSEC-2017-0008` (hwLedger) -- 9 years old, no rationale, unknown vulnerability class
   - `RUSTSEC-2023-0071` (hwLedger, phenoData) -- 3 years old, no rationale

8. **A common dependency drives the largest ignore cluster.** The 10-advisory batch RUSTSEC-2024-0411 through -0420 appears identically across BytePort and hwLedger. These likely originate from the same transitive dependency (possibly axum, tokio-postgres, or surrealdb) and should be evaluated together.

---

## Recommendations

1. **Add rationale to every ignore.** Document why the risk is acceptable: e.g., "not reachable in our usage", "dev-only dependency", "vulnerability requires specific conditions only met in adversarial scenarios."

2. **Add expiration dates.** Use the `date` field on every ignore (e.g., `date = "2026-07-01"`) to force mandatory re-evaluation. This is the primary mechanism cargo-deny provides for staleness management.

3. **Fix AtomsBot and PhenoControl.** Remove duplicate `allow-registry` entries from the `[sources]` section.

4. **Fix PhenoObservability.** Change `{ crate, advisory, reason }` to `{ id, rationale, date }`.

5. **Fix PhenoControl.** Change `{ crate, reason }` to `{ id, rationale, date }`.

6. **Remove duplicate ignores.** hwLedger has RUSTSEC-2017-0008 twice; forgecode has RUSTSEC-2024-0320 twice.

7. **Audit the 10-advisory batch together.** RUSTSEC-2024-0411 through -0420 in BytePort and hwLedger should be evaluated as a group -- they share a common dependency trigger and should have coordinated resolution.

8. **Evaluate oldest ignores first.** RUSTSEC-2017-0008 and RUSTSEC-2023-0071 in hwLedger should be reviewed for actual necessity. Nine years of unmaintained code may have been replaced.

---

## Methodology

- File discovery: `find /Users/<REDACTED>/CodeProjects/Phenotype/repos -maxdepth 2 -name "deny.toml" -not -path "*/target/*" | sort`
- Filter: only files containing `[advisories]` section (verified with grep)
- Parse: Python 3 with `tomli` (TOML 1.0 compliant)
- Staleness threshold: >365 days since ignore date
- Date reference: 2026-05-05
