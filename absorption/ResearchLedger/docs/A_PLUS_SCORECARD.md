# ResearchLedger release scorecard

Status as of 2026-08-15: **release candidate, not A+ yet**. This document records
implementation evidence, not a release or installed-app claim. Only consented bounded
reference fetching, persisted claims/provenance, and versioned hybrid retrieval with a
local cross-encoder contract are evidenced in the current integration.

| Requirement                   | Evidence                                                                                                                                                                                                                                                                | Status                                                                                       |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Local-first Tauri desktop     | Tauri desktop source, SQLite metadata, and Markdown vault paths are present in the integration                                                                                                                                                                          | IMPLEMENTED / package and installed-app validation pending                                   |
| GitHub import                 | Rust-owned local GitHub CLI integration and importer code are present                                                                                                                                                                                                   | IMPLEMENTED / authenticated installed-app invocation pending                                 |
| Provider boundary             | Official export/manual permalink path is the intended LinkedIn boundary; no release claim is supported by this merge                                                                                                                                                    | IMPLEMENTED boundary / live policy and installed-app validation pending                      |
| Consented bounded fetching    | Scoped, expiring, revocable consent grants with malformed timestamp fail-closed behavior; hashed consent audit targets; post-consent bounded queue selection, reclaimable leases, pre-fetch revocation recheck, and public-address DNS-pinned HTTP clients              | IMPLEMENTED / packaged-app and security-review validation pending                            |
| Claims and provenance         | Persisted provenance and structured claims with source citations and reproducible spans; unchanged reimports remove stale provenance atomically                                                                                                                         | IMPLEMENTED / validation pending                                                             |
| Search/RAG                    | FTS5 lexical search, deterministic chunking, model/version/input-hashed vectors, hybrid fusion including vector-only candidates, and a numeric-loopback local cross-encoder contract with deterministic fallback; adapter prevents model-download fallback              | IMPLEMENTED / local-model quality and restart validation pending                             |
| Frontend and interoperability | Workspace workflows and OKF-style Markdown/JSON interchange are implemented                                                                                                                                                                                             | IMPLEMENTED / validation and packaged-app parity pending                                     |
| Privacy and security          | Renderer credential boundary, URL/path guards, consent and audit code are implemented                                                                                                                                                                                   | IMPLEMENTED / security review and installed-app verification pending                         |
| Verification                  | Historical source and hosted evidence on `fb8dc6c` is retained for provenance only; it does not attest the current PR head. Current source, hosted CI, package, installed-binary, and authenticated-provider evidence must be recorded against the exact candidate SHA. | PENDING exact-SHA validation, package, installed-binary, and authenticated-provider evidence |

## Remaining A+ gates

1. Run the complete validation suite and record reproducible results for this merged integration.
2. Build and validate the release package, then prove packaged and installed-binary parity.
3. Complete security review, including the consent, credential, provider-boundary, URL/path, and
   dependency surfaces; resolve or explicitly govern findings.
4. Run an authenticated GitHub import in the installed application, recording repository and README
   counts plus non-secret hashes; the renderer must never receive a credential.
5. Restart the installed application and verify that consent state, fetched-source provenance,
   claims, vector/index state, and cited retrieval results survive the restart.
6. Validate the configured local cross-encoder/model on the installed path and retain the
   deterministic fallback as the offline behavior.
   Operational prerequisite: optional local retrieval services and any permitted packaged connector
   dependencies must be installed and started by the operator. No credential, cookie, or raw sensitive
   target is retained as release evidence.
