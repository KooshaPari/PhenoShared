# Privacy hygiene (single-tenant)

Status: **C02 L24** — operator guidance for a **single-user** local SessionLedger
install. This documents privacy hygiene on one host: what may contain PII, how
long to keep it, how to scrub before sharing, and how loopback trust fits.

This is **not** multi-tenant isolation or per-tenant row-level security.
SessionLedger remains a local companion; see [`docs/DESIGN.md`](../DESIGN.md)
non-goals. A minimal opt-in string scrub helper lives in
[`pii-redaction.md`](pii-redaction.md) (`src/pii_redact.rs`) — it is **not**
wired into the ETL / HTTP pipeline automatically.

Related: [`SECURITY.md`](../../SECURITY.md) (reporting + secret rotation),
[`docs/THREAT_MODEL.md`](../THREAT_MODEL.md) (STRIDE-lite disclosure surfaces),
[`local-trust-boundary.md`](local-trust-boundary.md) (bind + `SL_API_KEY` policy),
[`observability.md`](observability.md) (log level discipline),
[`pii-redaction.md`](pii-redaction.md) (in-tree email/API-key scrub helper).

## Single-tenant scope

| Expectation               | Reality today                                                                           |
| ------------------------- | --------------------------------------------------------------------------------------- |
| One operator per machine  | `sl-daemon` runs under the host user; no tenant IDs or org partitions                   |
| Data stays on the host    | Transcripts, OKF bundles, archives, and audit sinks are local filesystem paths          |
| Sharing is operator-owned | Export, backup, and redaction before leaving the host are manual or external-tool steps |
| Remote exposure is opt-in | Non-loopback bind requires `SL_API_KEY` + operator TLS; still single-tenant             |

Do not deploy SessionLedger as a shared multi-user service without additional
identity, network, and data-isolation controls outside this repository.

## PII in logs and structured telemetry

Session content may include names, credentials, file paths, API keys pasted into
chats, and other personally identifiable or sensitive material.

| Surface                                    | PII posture                                                                                                                                                                                                                                                        |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `tracing` / stdout logs                    | **Do not** log full `*.jsonl` transcripts or ingest bodies at `info` or above. Prefer `RUST_LOG=sl_daemon=info,tower_http=warn`. Reserve `trace` for local debugging only. See [`observability.md` § Log level discipline](observability.md#log-level-discipline). |
| Structured audit (`events.jsonl` / SQLite) | Records `actor`, `action`, `resource`, `request_id`, and timestamps — **not** transcript or ingest payload text ([`local-trust-boundary.md` § Structured audit events](local-trust-boundary.md#structured-audit-events)).                                          |
| HTTP validation errors                     | Keep messages short; avoid echoing large attacker-controlled blobs ([`THREAT_MODEL.md`](../THREAT_MODEL.md) HTTP ingest table).                                                                                                                                    |
| `/api/metrics`, `/metrics`                 | Aggregate counts and histograms only — no message bodies.                                                                                                                                                                                                          |
| CI / support bundles                       | Scrub logs and audit exports before attaching to public issues; use private advisories per [`SECURITY.md`](../../SECURITY.md).                                                                                                                                     |

When `SL_LOG_FORMAT=json` is enabled (`json-logs` feature), treat log files like
audit exports: restrict filesystem ACLs and rotate on the same schedule as
`<data_dir>/audit/`.

## Transcript and artifact retention

SessionLedger does **not** enforce TTLs on watch-dir transcripts, OKF output,
gzip archives, or audit sinks. Retention is operator policy on the host.

| Data class              | Typical location                                         | Retention guidance                                                                                                                                                                                     |
| ----------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Raw transcripts         | `--watch` / `SL_WATCH_DIR` (`*.jsonl`)                   | Keep while sessions are active; archive or delete when no longer needed for resume. Treat as **highest sensitivity**.                                                                                  |
| OKF bundles             | `--out` / `SL_DATA_DIR` (`*.okf.json`)                   | Distilled context may still embed secrets from source sessions. Align retention with transcripts or shorten if bundles are exported more often.                                                        |
| Gzip archives           | `<data_dir>/archive/<year>/<month>/`                     | Long-lived copies — include in backup scope; prune dated folders when disk or policy requires.                                                                                                         |
| Audit sink              | `<data_dir>/audit/events.jsonl` or `events.db`           | Follow rotation policy in [`local-trust-boundary.md` § Retention and rotation policy](local-trust-boundary.md#retention-and-rotation-policy) (for example 90 days active, then move to dated archive). |
| Agent / IDE transcripts | `~/.cursor/...`, `~/.forge/sessions`, tool-specific dirs | Outside `sl-daemon` control — document your own purge cadence if compliance requires it.                                                                                                               |

Recommended single-user desktop policy:

1. **Pin roots** — set `SL_DATA_DIR` so OKF, archive, and audit paths stay under one owner-only directory.
2. **Choose a window** — document a calendar retention window (for example 90 days) in local ops notes; the daemon will not enforce it.
3. **Rotate audit** — move (do not truncate in place) `events.jsonl` per local-trust-boundary; include `audit/` in backups.
4. **Delete source JSONL** only after confirming OKF/archive copies are no longer needed for resume or compliance.

## Redaction before export or share

There is **no** automatic redaction pass in the ETL or HTTP API. An opt-in
hermetic helper (`session_ledger::pii_redact::redact`) scrubs emails and common
API-key shapes in strings — see [`pii-redaction.md`](pii-redaction.md). Before
OKF bundles, audit exports, or log excerpts leave the host:

| Step            | Action                                                                                                                                                                                                 |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1. Scope        | Export only the minimum `bundle_id` / date range required for the recipient.                                                                                                                           |
| 2. Provenance   | Strip or generalize `provenance`, `source_id`, and `corpus` when identifiers would leak who ran which session ([`OKF-SPEC.md` § Provenance leakage](../reference/OKF-SPEC.md#164-provenance-leakage)). |
| 3. Entity text  | Review `messages`, `labels`, and `properties` in OKF JSON for secrets, tokens, internal URLs, and customer data. Optionally run `pii_redact::redact` on text fields as a first pass.                   |
| 4. Audit / logs | Use [`audit-review.ps1`](../../scripts/audit-review.ps1) filters; redact `resource` and `request_id` if they embed path or account hints.                                                              |
| 5. Re-validate  | Open the scrubbed file locally before upload; prefer encrypted transfer for anything still sensitive.                                                                                                  |

For public GitHub issues or CI artifacts: use fixtures with synthetic content only
(`tests/fixtures/okf/`). Never commit live transcripts or production OKF exports.

## Loopback trust and local boundaries

Privacy on a single-tenant install depends on **who can reach the daemon and read
the data directory**:

| Control              | Guidance                                                                                                                                                                    |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| HTTP bind            | Default loopback (`127.0.0.1:8080`). Open read/write `/api/*` on loopback without a key is intentional for local viewers — not safe on LAN/WAN.                             |
| `SL_API_KEY`         | Set for non-loopback binds or when local automation needs an explicit write secret. Rotation: [`SECURITY.md` § API keys](../../SECURITY.md#api-keys-and-secret-rotation).   |
| Filesystem ACLs      | Restrict `--watch`, `--out`, and `SL_DATA_DIR` to the operator user (and backup agents you trust).                                                                          |
| CORS + DNS rebinding | Permissive CORS on loopback increases browser-driven disclosure risk — see [`THREAT_MODEL.md` § Local daemon exposure](../THREAT_MODEL.md#5-surface-local-daemon-exposure). |
| TLS                  | In-process TLS is not provided; terminate at a reverse proxy for remote-style deploys — [`crypto-inventory.md`](crypto-inventory.md).                                       |

Full bind/auth matrix: [`local-trust-boundary.md`](local-trust-boundary.md).

## Machine verification (SelfCheck)

Hermetic doc anchor check (no daemon, no network):

```powershell
pwsh ./scripts/privacy-hygiene-check.ps1 -SelfCheck
```

`-SelfCheck` asserts this page keeps the single-tenant disclaimer, PII-in-logs
guidance, transcript retention, redaction steps, loopback trust cross-links, and
references to `SECURITY.md` / `THREAT_MODEL.md` / `local-trust-boundary.md`.
