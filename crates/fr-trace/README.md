# fr-trace

Rust CLI that scans a repo for `FR-*` Functional Requirement identifiers and
verifies every declared FR has at least one test reference and every test
reference points at a declared FR. Emits a structured JSON report.

**Replaces:**
- `repos/scripts/traceability-check.py`
- `repos/HexaKit/scripts/traceability-check.py`
- `repos/PhenoKits/HexaKit/scripts/traceability-check.py`

**Usage:** `fr-trace --path <dir> [--fr-file FUNCTIONAL_REQUIREMENTS.md]`
