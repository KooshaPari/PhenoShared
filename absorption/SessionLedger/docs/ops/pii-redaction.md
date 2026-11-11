# In-tree PII redaction helper (stub)

Status: **C02 L24** — minimal hermetic string scrub for emails and common
API-key / token shapes. Operators and library callers can opt in before
export or share.

This is **not** multi-tenant isolation, row-level security, or an automatic
ETL / HTTP redaction pipeline. SessionLedger remains a single-tenant local
companion; see [`privacy-hygiene.md`](privacy-hygiene.md) and
[`docs/DESIGN.md`](../DESIGN.md) non-goals.

Related: [`privacy-hygiene.md`](privacy-hygiene.md) (operator retention +
export hygiene), [`SECURITY.md`](../../SECURITY.md) (secret rotation),
[`docs/THREAT_MODEL.md`](../THREAT_MODEL.md) (disclosure surfaces).

## Phase-0 decision

| Choice                                                      | Rationale                                                                                          |
| ----------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| Std-only helper (`src/pii_redact.rs`)                       | No new crates; hermetic unit tests; cheap to call from scripts or future CLI                       |
| Emails + known key prefixes                                 | Covers the highest-frequency paste accidents (chat emails, `sk-` / `ghp_` / `AKIA` / Slack `xox*`) |
| Opt-in API (`redact` / `redact_emails` / `redact_api_keys`) | ETL and HTTP stay unchanged; operators scrub on export                                             |
| Defer full DLP / NER                                        | Named-entity / ML redaction and policy engines are effort **L**; stub closes the in-tree gap first |

Do **not** treat this helper as a compliance guarantee. Review exports manually
when the recipient is outside the host trust boundary.

## API surface

```rust
use session_ledger::pii_redact::{redact, REDACTED_EMAIL, REDACTED_API_KEY};

// session_ledger::pii_redact::redact is the opt-in entry point
let scrubbed = redact("mail alice@example.com key sk-abcdefghijklmnopqrstuvwxyz012345");
// → "mail [REDACTED_EMAIL] key [REDACTED_API_KEY]"
```

| Function             | Behavior                                           |
| -------------------- | -------------------------------------------------- |
| `redact(s)`          | API-key scrub then email scrub                     |
| `redact_emails(s)`   | Email-shaped substrings → `[REDACTED_EMAIL]`       |
| `redact_api_keys(s)` | Known prefixes + token body → `[REDACTED_API_KEY]` |

Prefix list (Phase-0): `sk-`, `sk_live_`, `sk_test_`, `ghp_` / `gho_` / `ghu_` /
`ghs_` / `ghr_`, `AKIA`, `xoxb-` / `xoxp-` / `xoxa-` / `xoxr-`. Bodies require
≥8 characters after the prefix.

## Future hooks

When a fuller pipeline is warranted:

1. Wire `redact` into optional export / audit-review paths (feature flag).
2. Expand patterns (Bearer JWTs, Azure/GCP key shapes) behind the same API.
3. Optionally adopt a mature DLP library only if false-positive cost is acceptable.
4. Keep multi-tenant / IdP isolation as a separate product decision — out of
   Phase-0 scope.

## Machine verification (SelfCheck)

Hermetic helper + docs smoke (no daemon, no network):

```powershell
pwsh ./scripts/pii-redact-check.ps1 -SelfCheck
```

`-SelfCheck` asserts `src/pii_redact.rs` exposes `redact` / email / API-key
APIs, this doc keeps the Phase-0 decision and non-multi-tenant disclaimer, and
the Rust wrapper test is present.

| Gate                    | Status   |
| ----------------------- | -------- |
| PII redaction SelfCheck | **done** |

Soft CI (non-blocking): `.github/workflows/security.yml` job
`pii-redaction` runs the same `-SelfCheck` with `continue-on-error: true`.
