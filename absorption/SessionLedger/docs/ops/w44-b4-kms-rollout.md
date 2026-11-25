# W44-B4 — KMS-vs-PII-redaction policy decision (D-W44-1 → L22 KMS)

**Lane**: W44-B4 — `w44-kms-or-redaction`
**R tag**: R-4 (policy)
**Status on main**: implementation blocked on policy decision (D-W44-1).

## D-W44-1: pick the path

**Option L22 (in-tree KMS)**: ship SessionLedger with a `sl-kms` crate that wraps the macOS Keychain (Apple CryptoKit `SecKey*`) on macOS, Linux `secret-service` (D-Bus) on Linux, and Windows Credential Manager on Windows. Stores the `sl-daemon` service key + any per-session auth tokens. Service key is generated at first install and never leaves the device.

**Option L23 (multi-tenant PII redaction)**: ship a regex+NER-based PII redactor that runs at the daemon's `/api/sessions/ingest` boundary, scrubbing emails, phone numbers, IP addresses, and OAuth tokens from incoming transcripts before they hit storage. No KMS at all.

## Decision: **L22 (in-tree KMS)**

**Rationale** (smaller blast radius):

| Dimension        | L22 (KMS)                                              | L23 (PII redaction)                                               |
| ---------------- | ------------------------------------------------------ | ----------------------------------------------------------------- |
| Surface area     | One new crate (`sl-kms`), bounded to auth path         | Touches every ingress endpoint                                    |
| Failure mode     | Single key not found → auth fails → user knows         | Missed PII → silent leak → user doesn't know                      |
| Compliance       | OS-blessed credential storage (Keychain, Cred Mgr)     | Pattern-based scrubbing is **never** authoritative for compliance |
| Operational cost | One-time setup + rotation                              | Ongoing redaction-rule maintenance, false positives               |
| Threat model     | Stolen laptop = attacker can't move key (Keychain ACL) | Stolen laptop = full local DB if attacker can auth                |
| Latency          | One Keychain fetch at boot                             | Per-request regex+NER overhead                                    |

L23's blast radius is large because redaction is **permissive** by nature (you scrub what you recognize, leave what you don't). L22's blast radius is bounded to the credential path.

## Implementation plan (machine-resolvable, this commit)

- `crates/sl-kms/Cargo.toml` + `crates/sl-kms/src/lib.rs` — minimal KMS wrapper around platform credential stores. **Stub-only** (calls return `Err(KmsError::NotImplemented)`); this commit just establishes the API surface so the human-gated work has a clear target.
- `crates/sl-daemon/Cargo.toml` — declare `sl-kms` as a dependency; **not wired into the auth path yet** (human gates this on rotation policy + key derivation parameters).
- `docs/ops/w44-b4-kms-rollout.md` — operator runbook for the rollout window.

## Human-gated portion (NOT this commit)

- **R-4.a** — Key rotation cadence (90 days is current W43 norm).
- **R-4.b** — Key derivation parameters (Argon2id memory + iterations).
- **R-4.c** — Multi-device key sync vs single-device-only (single-device is simpler and matches the existing threat model).
- **R-4.d** — Recovery flow (recovery codes vs paper backup vs nothing).

## Verification

```
cargo build -p sl-kms
# Expected: builds clean. The sl-kms::get("sl-daemon-key") returns Err(NotImplemented).
```

## Files

- `crates/sl-kms/Cargo.toml`
- `crates/sl-kms/src/lib.rs` (stub)
- `crates/sl-daemon/Cargo.toml` (declare dep, no wire-up)
- `docs/ops/w44-b4-kms-rollout.md`
