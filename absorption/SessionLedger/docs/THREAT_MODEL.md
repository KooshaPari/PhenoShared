# SessionLedger — STRIDE-lite Threat Model

Status: living document for local-first SessionLedger (`sl-daemon` + OKF pipeline).  
Scope: **ingest**, **archive/restore path handling**, **malicious OKF bundles**, and **local daemon exposure**.  
Reporting: follow [`SECURITY.md`](../SECURITY.md) (private advisory / maintainer contact — do not open public issues for vulns).

This is a **STRIDE-lite** model: each surface lists the relevant STRIDE categories, assumed trust boundaries, and mitigations (implemented or recommended). It is not a formal risk register or CVSS scoring sheet.

---

## 1. Trust model & assets

| Asset                                               | Why it matters                                                |
| --------------------------------------------------- | ------------------------------------------------------------- |
| Session transcripts (`*.jsonl`) under `--watch`     | Source of operator intent, secrets, and work product          |
| OKF bundles (`*.okf.json`) under `--out` / data dir | Distilled continuation artifacts; may embed sensitive context |
| Gzip archives under `<data_dir>/archive/`           | Long-lived copies of the same content                         |
| Daemon HTTP API (default `127.0.0.1:8080`)          | Read/list/search/replay/ingest bridge for local viewers       |

**Assumptions (Phase 0 / local-first):**

- The host user who runs `sl-daemon` is trusted on that machine.
- The product is **not** a multi-tenant or internet-facing service ([`docs/DESIGN.md`](DESIGN.md) non-goal).
- Single-tenant privacy hygiene (PII in logs, retention, redaction before share, loopback trust) is documented in [`docs/ops/privacy-hygiene.md`](ops/privacy-hygiene.md) — not row-level isolation or in-tree redaction pipelines.
- Network attackers on the LAN are **out of scope only if** the bind address stays loopback; binding to `0.0.0.0` changes the threat model.

**Trust boundaries:**

```text
  [untrusted files on disk] ──watch──▶ ETL ──write──▶ [out_dir *.okf.json]
  [HTTP client] ──TCP──▶ axum (CORS: Any) ──read/write paths──▶ out_dir
  [CLI archive/restore] ──paths──▶ archive/ + output_dir
```

---

## 2. Surface: Ingest

### 2.1 File-watch ingest (ETL)

Watcher reads `*.jsonl` from `--watch`, compiles sessions, exports OKF to `--out` (`crates/sl-daemon`).

| STRIDE                     | Threat                                                        | Notes / mitigations                                                                                                      |
| -------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| **S**poofing               | Attacker drops a forged transcript into the watch dir         | Same-user FS trust; mitigate with watch-dir permissions (owner-only) and optional signed/provenance fields later         |
| **T**ampering              | Malformed or hostile JSONL alters distilled bundles           | Parser/compile failures should fail closed per file; corrupt outputs skipped on list (`read_all_bundles` skips bad JSON) |
| **R**epudiation            | No durable audit of which file produced which OKF             | Prefer retaining provenance (`source_id` / corpus) in OKF; log watch→write mapping in ops                                |
| **I**nformation disclosure | Watch dir may contain secrets; OKF copies them into `out_dir` | Treat `out_dir` as sensitive; restrict FS ACLs; do not sync to shared/cloud paths without scrubbing                      |
| **D**enial of service      | Huge/rapidly changing JSONL floods the consumer queue         | Bound queue depth (mpsc), `--once` for CI; consider size/rate limits                                                     |
| **E**levation of privilege | N/A beyond writing under configured `out_dir`                 | Ensure daemon does not run as a more privileged user than the data owner                                                 |

### 2.2 HTTP ingest (`POST /api/ingest`)

Validates a `PostBundle` via `validate_okf_bundle` (structural checks: `bundle_id`, `created_at`, messages, roles, `token_count`). On success returns `200` with validation result; failures return `422`.

| STRIDE                     | Threat                                                            | Notes / mitigations                                                                                                                                               |
| -------------------------- | ----------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **S**poofing               | Any local client can POST without auth                            | Acceptable on loopback-only; **require auth or disable ingest** if bind is non-local                                                                              |
| **T**ampering              | Crafted payload bypasses weak validation                          | Current checks are structural only — not semantic integrity or size caps; add max body size, max message count/length                                             |
| **I**nformation disclosure | Validation error messages may echo attacker input                 | Keep messages short; avoid reflecting large content blobs                                                                                                         |
| **D**oS                    | Oversized JSON body / many messages                               | Enforce body limits at the HTTP layer; reject extreme `token_count` / array sizes                                                                                 |
| **E**oP                    | If ingest later **writes** files using `bundle_id` as a path stem | **Must** sanitize `bundle_id` the same way replay does (reject `/`, `\`, `..`); today ingest is validate-only — preserve that invariant when persistence is added |

---

## 3. Surface: Archive / restore path traversal

`archive_bundles` gzips `*.okf.json` into `<data_dir>/archive/<year>/<month>/<bundle_id>.json.gz`.  
`restore_bundle` gunzips an archive path into `output_dir`.  
`find_archive_path` searches recursively for `<bundle_id>.json.gz`.

| STRIDE                         | Threat                                                                                           | Notes / mitigations                                                                                                                                                                                                                                                                                                                     |
| ------------------------------ | ------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **T**ampering / path traversal | `bundle_id` or archive filename containing `..` or separators writes/reads outside intended dirs | Archive dest uses `bundle_id_from_path` (filename stem only) — good. **Restore** joins `output_dir` with the archive’s file stem after stripping `.gz`; callers must not pass attacker-controlled `output_dir` or archive names with traversal. CLI `bundle_id` for find should reject `/`, `\`, `..` (mirror HTTP replay sanitization) |
| **T**ampering                  | Zip-slip style: malicious `.json.gz` whose logical name escapes                                  | Prefer writing only a **sanitized basename** under a canonicalized `output_dir`; refuse if resolved path is not under the output root                                                                                                                                                                                                   |
| **I**nformation disclosure     | Recursive find + restore of attacker-planted archives under `archive/`                           | Keep `archive/` owner-writable only; do not restore from untrusted trees                                                                                                                                                                                                                                                                |
| **D**oS                        | Gzip bombs (tiny compressed → huge decompressed)                                                 | Cap decompressed size in `gunzip_bytes`; fail closed on oversize                                                                                                                                                                                                                                                                        |
| **D**oS                        | Deep/wide archive trees slow `find_recursive`                                                    | Bound depth/entries or index by id                                                                                                                                                                                                                                                                                                      |

**Recommended invariant:** after any path join, `canonicalize` (or equivalent) and assert the result is still under the configured data/output root.

---

## 4. Surface: Malicious OKF bundles

OKF documents (`*.okf.json`) are JSON graphs (entities, relations, provenance). They are listed, searched, streamed (SSE), and replayed by the HTTP API; viewers and resume flows may treat them as injectable context.

| STRIDE                     | Threat                                                                             | Notes / mitigations                                                                                                                 |
| -------------------------- | ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| **T**ampering              | Hostile entity labels/properties (prompt injection when re-injected into an agent) | Treat OKF as **untrusted input** to agents; sanitize/quote on inject; preserve provenance so operators can audit                    |
| **T**ampering              | Schema confusion / unexpected types                                                | Validate against OKF dialect (`okf: "1.0"`) before trust; reject unknown major versions ([`src/ports/okf.rs`](../src/ports/okf.rs)) |
| **I**nformation disclosure | Bundles may embed secrets from source sessions                                     | Same as ingest: protect `out_dir`; consider redaction hooks before export/share                                                     |
| **D**oS                    | Huge entity arrays / deeply nested JSON                                            | Cap parse size; replay already streams entities — still bound array length and file size before parse                               |
| **S**poofing               | Fake `provenance` / `source_id`                                                    | Structural validation does not prove origin; signing or content hashes are future hardening                                         |

Replay path (`GET /api/replay/{bundle_id}`) **already rejects** `bundle_id` values containing `/`, `\`, or `..` — keep this check on every path-derived id.

---

## 5. Surface: Local daemon exposure

Default bind: `127.0.0.1:8080` (`--http-bind`; `off` disables HTTP). CORS is **permissive** (`allow_origin/methods/headers: Any`) so local WASM viewers can call the API.

| STRIDE                     | Threat                                                                                  | Notes / mitigations                                                                                                                     |
| -------------------------- | --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **S**poofing               | No authentication on health, list, search, stream, replay, ingest                       | Loopback + local-user trust; document that **non-loopback bind is unsupported without auth**                                            |
| **T**ampering              | Local malware or other users’ processes call the API                                    | OS user isolation; prefer loopback; optional token later                                                                                |
| **I**nformation disclosure | `GET /api/bundles`, `/api/search`, SSE paths expose session content to any local client | Expected for a local viewer bridge; harden FS + bind address                                                                            |
| **I**nformation disclosure | DNS rebinding / browser CSRF from a malicious page to `127.0.0.1:8080`                  | Permissive CORS increases impact; mitigate with `Origin` checks, localhost-only CSRF tokens, or binding to a random port + opaque token |
| **D**oS                    | SSE fan-out or expensive search against large `out_dir`                                 | Limit concurrent streams; paginate list/search                                                                                          |
| **E**oP                    | Operator sets `--http-bind 0.0.0.0:...`                                                 | Treat as severity upgrade: LAN/WAN exposure of session data and ingest; warn in CLI/docs                                                |

**Operational defaults (recommended):**

1. Keep `--http-bind` on loopback (or `off` when unused).
2. Restrict permissions on `--watch` and `--out`.
3. Report vulnerabilities per [`SECURITY.md`](../SECURITY.md).

---

## 6. STRIDE summary matrix

| Surface           | S   | T   | R   | I   | D   | E   |
| ----------------- | --- | --- | --- | --- | --- | --- |
| File-watch ingest | ●   | ●   | ○   | ●   | ●   | ○   |
| HTTP ingest       | ●   | ●   | ○   | ○   | ●   | ●*  |
| Archive / restore | ○   | ●   | ○   | ●   | ●   | ○   |
| Malicious OKF     | ●   | ●   | ○   | ●   | ●   | ○   |
| Local HTTP daemon | ●   | ●   | ○   | ●   | ●   | ●   |

● = primary concern for this surface · ○ = secondary / deferred · \* if ingest gains filesystem writes

---

## 7. Out of scope (this revision)

- Supply-chain / dependency compromise (covered operationally by `cargo deny`, gitleaks, SBOM — see [`SECURITY.md`](../SECURITY.md))
- Viewer UI XSS (separate frontend threat model when shipping web UI beyond local WASM)
- Multi-tenant hosted deployments

---

## 8. Related docs

- [`SECURITY.md`](../SECURITY.md) — vulnerability reporting and disclosure
- [`docs/ops/privacy-hygiene.md`](ops/privacy-hygiene.md) — single-tenant PII, retention, redaction, loopback trust
- [`docs/DESIGN.md`](DESIGN.md) — architecture and non-goals
- [`docs/reference/OKF-SPEC.md`](reference/OKF-SPEC.md) — OKF dialect
- [`crates/sl-daemon/README.md`](../crates/sl-daemon/README.md) — daemon run modes
