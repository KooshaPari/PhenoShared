# Cryptography inventory and remote TLS guidance

Status: **C02 L22** — documents what cryptography SessionLedger uses today, how
operators terminate TLS for a remote-style daemon deploy, and the **Phase-0
decision** on KMS / encryption-at-rest (deferred in-tree vs recommended host
deploy patterns). This documents a **soft** in-tree SHA-256 keystream envelope helper (soft `src/envelope.rs` helper) for experiments. It is **not** a production KMS, sealed-secret client, or automatic encryption-at-rest for OKF/audit stores.

Related: [`SECURITY.md`](../../SECURITY.md) (reporting + API-key rotation),
[`docs/THREAT_MODEL.md`](../THREAT_MODEL.md) (STRIDE-lite surfaces),
[`local-trust-boundary.md`](local-trust-boundary.md) (bind + `SL_API_KEY` policy),
[`privacy-hygiene.md`](privacy-hygiene.md) (PII / export hygiene).

## Cryptography inventory

| Use                              | Mechanism                                                            | Where                                                                          | Notes                                                                                   |
| -------------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------- |
| Content dedup key                | **SHA-256** (`sha2` crate)                                           | [`src/domain/dedup.rs`](../../src/domain/dedup.rs)                             | Stable hash over normalized scope + topic slug; **hashing, not encryption**             |
| Archive transport                | **gzip** (`flate2` / archive path)                                   | `crates/sl-daemon` archive/restore                                             | Compression only; archives are **not** encrypted at rest                                |
| Ingest idempotency fingerprint   | `std::collections::hash_map::DefaultHasher`                          | [`crates/sl-daemon/src/http.rs`](../../crates/sl-daemon/src/http.rs)           | Process-local replay guard; **not** a cryptographic MAC                                 |
| Outbound HTTP (CLI / viewer)     | **rustls** via `reqwest`                                             | `crates/sl-daemon`, optional `sl-viewer`                                       | TLS to remote HTTPS endpoints when configured; loopback daemon URL stays plain HTTP     |
| Release / supply-chain integrity | **SHA-256** checksums + optional **cosign** keyless signing          | [`docs/ops/distribution.md`](distribution.md#release-integrity-signing-cosign) | Verifies downloaded binaries; separate from runtime app KMS                             |
| Commit / branch governance       | GPG or SSH commit signatures                                         | [`docs/ops/commit-signing.md`](commit-signing.md)                              | Repository hygiene; not daemon data encryption                                          |
| Soft envelope (opt-in)           | **SHA-256 keystream (soft)** (`sha2` keystream in `src/envelope.rs`) | [`src/envelope.rs`](../../src/envelope.rs)                                     | `SL_ENVELOPE_KEY` 32-byte hex DEK; `v1:nonce:ct` blob; **not** wired into OKF/ETL paths |

### Explicit non-goals (today)

- **No encryption-at-rest** for OKF bundles (`*.okf.json`), gzip archives, audit
  JSONL/SQLite, or episodic memory DB files. Protect data with OS filesystem ACLs,
  full-disk encryption, and backup policy on the host (see
  [KMS and encryption-at-rest](#kms-and-encryption-at-rest-phase-0-decision)).
- **No in-process TLS** on `sl-daemon` HTTP. The daemon speaks plain HTTP on its
  bind address; operators own TLS termination.
- **No KMS, sealed secrets, or HSM integration** in-tree. `SL_API_KEY` is a
  single shared secret in the process environment — treat it like a host-local
  credential, not a managed vault record.

## KMS and encryption-at-rest (Phase-0 decision)

**Decision:** in-tree KMS, sealed-secret clients, HSM integration, and
application-level **envelope encryption** for OKF / audit / episodic stores are
**Phase-0 deferred**. SessionLedger remains a single-user local companion; the
trusted computing base for data at rest is the **host OS and operator deploy
layout**, not a SessionLedger crypto service.

A soft DEK helper lives in `src/envelope.rs` (feature-gated). There is still **no** cloud KMS SDK, KEK hierarchy, or automatic at-rest encryption of OKF/audit files — operators keep host-side FDE/ACL patterns below.

### Phase-0 deferred vs recommended deploy patterns

| Concern                                                                              | Phase-0 posture                                                                                  | Recommended deploy pattern (operator-owned)                                                                                                 |
| ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| Application encryption-at-rest (OKF, gzip archives, audit JSONL/SQLite, episodic DB) | **Deferred** — plaintext files under the data directory                                          | Enable **OS full-disk / volume encryption** (BitLocker, FileVault, LUKS); restrict directory ACLs to the daemon user                        |
| Envelope encryption (DEK wrapped by KEK)                                             | **Soft stub** — SHA-256 keystream DEK via `envelope-crypto` + `SL_ENVELOPE_KEY`; no KEK/KMS wrap | Prefer volume/backup encryption for production; wire ETL paths only after a dedicated ADR                                                   |
| Cloud / hardware KMS (AWS KMS, GCP KMS, Azure Key Vault, PKCS#11 HSM)                | **Deferred** — no SDK, IAM roles, or sealed-secret client in-tree                                | Keep `SL_API_KEY` (and any future secrets) in the host **service manager secret** or org vault; inject as env at start — do not commit keys |
| In-process TLS for `sl-daemon`                                                       | **Deferred** — plain HTTP on bind address                                                        | Terminate TLS at Caddy/nginx in front of loopback (see [Remote daemon deploy](#remote-daemon-deploy-tls-at-the-edge))                       |
| Backup / export confidentiality                                                      | **Operator-owned**                                                                               | Encrypt backup media or use encrypted backup tools; redact before export leaves the host ([`privacy-hygiene.md`](privacy-hygiene.md))       |

### Recommended host-side at-rest controls (today)

1. **Full-disk or volume encryption** on every machine that stores SessionLedger
   data directories — primary control for stolen-disk / cold-storage risk.
2. **Filesystem ACLs** so only the service account running `sl-daemon` (and
   interactive admins) can read OKF, audit, and episodic paths.
3. **Secret injection outside the repo** — systemd/`EnvironmentFile`, Windows
   service secrets, or an org vault agent that writes `SL_API_KEY` into the
   process environment at start. Never commit live keys.
4. **Encrypted backups** of the data directory when backups leave the host;
   treat archives as sensitive even though gzip is not encryption.
5. **TLS at the edge** for any non-loopback exposure — transport confidentiality
   is separate from at-rest controls; both are operator-owned in Phase 0.

### Reconsider triggers (when Phase-0 deferral ends)

Revisit in-tree KMS / envelope encryption only when **all** of the following are
true (record an ADR before code):

| Trigger                                                                  | Why it matters                                                    |
| ------------------------------------------------------------------------ | ----------------------------------------------------------------- |
| Multi-user or multi-tenant hosted deploy is in scope                     | Host ACLs alone no longer match the threat model                  |
| Compliance requires application-level ciphertext independent of OS FDE   | Need audit evidence beyond BitLocker/FileVault/LUKS               |
| Maintainers commit to a KMS product + key-rotation runbook               | Avoid half-integrated SDKs without rotation and disaster recovery |
| Envelope format + migration for existing plaintext OKF/audit is designed | Prevent irreversible lock-in or silent data loss                  |

Until then, record KMS / app-level encryption-at-rest as **deferred / N/A** —
not an open implementation gap without product scope.

### KMS / at-rest evidence checklist

| Gate                                                        | Status                 | Evidence / prerequisite                                                       |
| ----------------------------------------------------------- | ---------------------- | ----------------------------------------------------------------------------- |
| Crypto inventory + hashing vs encryption clarified          | **done**               | Inventory table above                                                         |
| Explicit no in-tree KMS / envelope / app encryption-at-rest | **done**               | Non-goals + this section                                                      |
| Phase-0 deferred vs recommended deploy table                | **done**               | Table in this section                                                         |
| Host FDE / ACL / secret-injection guidance                  | **done**               | Recommended host-side controls                                                |
| TLS-at-edge samples (Caddy/nginx)                           | **done**               | [Remote daemon deploy](#remote-daemon-deploy-tls-at-the-edge)                 |
| Crypto inventory SelfCheck                                  | **done**               | `scripts/crypto-inventory-check.ps1 -SelfCheck`                               |
| Envelope-crypto SelfCheck                                   | **done**               | `scripts/envelope-crypto-check.ps1 -SelfCheck` (+ `tests/envelope_crypto.rs`) |
| Blocking envelope-crypto CI workflow                        | **done**               | `.github/workflows/envelope-crypto.yml`                                       |
| Soft envelope helper (`src/envelope.rs`)                    | **done**               | SHA-256 keystream + `SL_ENVELOPE_KEY`; `envelope-crypto` marker feature       |
| In-tree KMS / sealed-secret / HSM client                    | **unpaid**             | No SDK; reconsider triggers above                                             |
| KEK wrap / cloud KMS for envelope DEK                       | **unpaid**             | Soft DEK only; host FDE / vault injection is the control                      |
| AES-GCM envelope revision                                   | **unpaid**             | Keystream stub until dep graph + ADR accepted                                 |
| Application envelope encryption for OKF/audit               | **deferred (Phase-0)** | No DEK/KEK format wired into ETL; host FDE is the control                     |
| In-process daemon TLS                                       | **deferred**           | Proxy termination remains the deploy path                                     |

## Remote daemon deploy: TLS at the edge

SessionLedger remains a **single-user** companion. Exposing the HTTP API beyond
loopback requires `SL_API_KEY` and a **TLS-terminating reverse proxy** in front
of a loopback-bound daemon.

### Recommended layout

```text
[Client] --TLS--> [Caddy or nginx :443] --plain HTTP--> [sl-daemon 127.0.0.1:8080]
```

1. **Bind the daemon to loopback** — keep `SL_HTTP_BIND=127.0.0.1:8080` (systemd
   unit default in [`packaging/systemd/sessionledger-daemon.service`](../../packaging/systemd/sessionledger-daemon.service)).
   Do not publish `:8080` on a public interface when the proxy owns `:443`.
2. **Set a strong `SL_API_KEY`** — required for non-loopback binds; see
   [API key and secret handling](#api-key-and-secret-handling) below.
3. **Terminate TLS at the proxy** — use one of the in-repo samples:

| Proxy | Sample config                                                                    | Operator notes                                                                                        |
| ----- | -------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Caddy | [`packaging/caddy/Caddyfile`](../../packaging/caddy/Caddyfile)                   | Automatic HTTPS (ACME) when DNS points at the host; set `SESSIONLEDGER_HOST` or edit the site address |
| nginx | [`packaging/nginx/sessionledger.conf`](../../packaging/nginx/sessionledger.conf) | HTTP→HTTPS redirect + `proxy_pass` to `127.0.0.1:8080`; supply cert paths                             |

4. **Enable and order services** — install `sessionledger-daemon`, then install
   and reload Caddy/nginx. Full walkthrough:
   [`distribution.md` § Traditional server TLS reverse proxy](distribution.md#traditional-server-tls-reverse-proxy-caddy--nginx).

Clients must send the shared secret on protected routes:

```text
Authorization: Bearer <SL_API_KEY>
X-API-Key: <SL_API_KEY>
```

`/healthz` and `/readyz` stay unauthenticated for load-balancer probes.

## API key and secret handling

| Topic        | Guidance                                                                                                                                                                           |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Generation   | `openssl rand -hex 32` or equivalent CSPRNG output; never reuse release checksums or commit SHAs as keys                                                                           |
| Storage      | Environment variable or service manager secret file **outside** the repo; see [`.env.example`](../../.env.example) placeholders only                                               |
| Rotation     | Stop callers → replace `SL_API_KEY` → restart `sl-daemon` → update client headers; burn the old value ([`SECURITY.md` § API keys](../../SECURITY.md#api-keys-and-secret-rotation)) |
| Repo hygiene | `scripts/env-example-check.ps1`, gitleaks, and TruffleHog in CI; do not commit live keys                                                                                           |
| Threat model | Non-loopback without a key is a **startup deny**; with a key, all `/api/*` require it — details in [`local-trust-boundary.md`](local-trust-boundary.md)                            |

## Soft envelope stub

Opt-in marker feature (default off in CI filters; module always compiled):

```powershell
cargo test envelope_crypto --features envelope-crypto --locked
pwsh ./scripts/envelope-crypto-check.ps1 -SelfCheck
```

- Module: [`src/envelope.rs`](../../src/envelope.rs)
- Feature: `envelope-crypto` (marker for SelfCheck / CI wiring)
- Key: `SL_ENVELOPE_KEY` — 64 hex chars (32 bytes). **Never commit live keys.**
- Blob: `v1:<16-byte-nonce-hex>:<ciphertext-hex>`
- Non-goals: not called from daemon ingest; not a substitute for host FDE; **does not claim in-tree KMS**, sealed-secret clients, or automatic OKF/audit encryption.

## Hard envelope-crypto CI evidence (C02 L22)

Blocking hermetic SelfCheck for the soft envelope helper scope — docs, workflow,
and `security.yml` anchors only. This section is the operator SSOT for what is
**done** vs **unpaid** on envelope crypto; it does **not** claim in-tree KMS,
sealed secrets, KEK wrap, or production at-rest encryption.

| Gate                                     | Status     | Evidence                                                                      |
| ---------------------------------------- | ---------- | ----------------------------------------------------------------------------- |
| Envelope-crypto SelfCheck                | **done**   | `scripts/envelope-crypto-check.ps1 -SelfCheck` (+ `tests/envelope_crypto.rs`) |
| Blocking envelope-crypto CI workflow     | **done**   | `.github/workflows/envelope-crypto.yml`                                       |
| Soft envelope helper (`src/envelope.rs`) | **done**   | SHA-256 keystream + `SL_ENVELOPE_KEY`; `envelope-crypto` marker feature       |
| In-tree KMS / sealed-secret client       | **unpaid** | No cloud KMS SDK or sealed-secret client in-tree                              |
| KEK wrap / cloud KMS for envelope DEK    | **unpaid** | Soft hex DEK via env only; no KEK hierarchy                                   |
| AES-GCM envelope revision                | **unpaid** | Keystream stub until dep graph + ADR accepted                                 |
| OKF/audit automatic envelope encryption  | **unpaid** | Host FDE / ACLs remain the Phase-0 control                                    |

Cross-check: general crypto inventory rows live in [KMS / at-rest evidence checklist](#kms--at-rest-evidence-checklist) above; `scripts/crypto-inventory-check.ps1 -SelfCheck` covers inventory + Phase-0 deferral without duplicating this blocking gate.

## Machine verification (SelfCheck)

Hermetic doc anchor check (no daemon, no network, no KMS SDK):

```powershell
pwsh ./scripts/crypto-inventory-check.ps1 -SelfCheck
```

`-SelfCheck` asserts this page keeps the inventory table, the no-KMS / no
encryption-at-rest disclaimers, the **Phase-0 deferred vs recommended deploy**
KMS/at-rest section, TLS sample paths, and cross-links to `SECURITY.md` /
`local-trust-boundary.md`.

<!-- Crypto inventory SelfCheck | **done** -->
<!-- Envelope-crypto SelfCheck | **done** -->
<!-- Blocking envelope-crypto CI workflow | **done** -->
<!-- In-tree KMS / sealed-secret client | **unpaid** -->
<!-- KEK wrap / cloud KMS for envelope DEK | **unpaid** -->
