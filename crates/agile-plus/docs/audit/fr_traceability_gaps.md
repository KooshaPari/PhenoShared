# FR-AGP Traceability Gap Matrix
Generated: 2026-06-15

| FR-AGP-ID | Impl Crate(s) | Has Tests in FR file? | Gap? |
|-----------|---------------|----------------------|------|
| FR-AGP-001 | agileplus-sqlite | ✅ yes | none |
| FR-AGP-011 | agileplus-grpc, agileplus-proto | ✅ yes | none |
| FR-AGP-012 | agileplus-api | ✅ yes | none |
| FR-AGP-013 | agileplus-application, agileplus-github | ✅ yes | none |
| FR-AGP-015 | agileplus-api | ✗ no | **NEEDS TEST** |
| FR-AGP-016 | agileplus-cli | ✗ no | **NEEDS TEST** |
| FR-AGP-017 | agileplus-triage | ✅ yes (2 files) | none |
| FR-AGP-018 | agileplus-application, agileplus-cli, agileplus-triage | ✅ yes (2 files) | none |
| FR-AGP-019 | agileplus-application, agileplus-cli, agileplus-triage | ✅ yes (2 files) | none |
| FR-AGP-020 | agileplus-application, agileplus-cli, agileplus-triage | ✅ yes | none |
| FR-AGP-021 | agileplus-application, agileplus-cli | ✅ yes | none |
| FR-AGP-022 | agileplus-application, agileplus-cli | ✅ yes | none |
| FR-AGP-023 | agileplus-cli | ✅ yes | none |

## Gaps
- **FR-AGP-002 through FR-AGP-010, FR-AGP-014**: not referenced in code (missing impl or missing annotation)
- **FR-AGP-015**: `agileplus-api` has no tests in the file referencing this FR
- **FR-AGP-016**: `agileplus-cli` has no tests in the file referencing this FR

## Next Steps
1. Add `#[test]` coverage for FR-AGP-015 and FR-AGP-016
2. Audit FR-AGP-002..010 and FR-AGP-014 — add code annotations or implement
