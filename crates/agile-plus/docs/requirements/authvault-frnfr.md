# Authvault — Functional & Non-Functional Requirements

**Version:** 1.0.0  
**Date:** 2026-05-29  
**Status:** Backfilled from merged PRs #30, #31, #32 + existing codebase.  
**Intended consumers:** Tracera, AgilePlus (ingestion via shared auth middleware).

---

## 1. Functional Requirements

### FR-AUTHV-001 — PKCE Code-Verifier Generation

| Field | Value |
|-------|-------|
| **Title** | RFC 7636-compliant PKCE code-verifier generation |
| **PR** | #30 (`feat(pkce): RFC 7636-compliant PKCE + CSRF state hardening`) |
| **RFC** | RFC 7636 §4.1 |

**Description**  
The system SHALL generate a cryptographically-random code verifier consisting of 32 entropy bytes
base64url-encoded (no padding) to produce a 43-character string composed exclusively of unreserved
ASCII characters (`A-Z a-z 0-9 - . _ ~`).

**Acceptance Criteria**

1. Generated verifier length is in `[43, 128]` (RFC 7636 §4.1 bounds).
2. Every character is an unreserved ASCII character per RFC 7636 §4.1.
3. Two independently-generated verifiers are statistically unique (collision probability ≤ 2⁻²⁵⁶).
4. Entropy source is `OsRng` (CSPRNG); no deterministic fallback.

**Traceability**  
`src/domain/pkce.rs` — `CodeVerifier::new()`, constants `VERIFIER_MIN_LEN`/`VERIFIER_MAX_LEN`.  
Tests: `test_verifier_length_is_rfc_compliant`, `test_verifier_charset_is_unreserved_ascii`,
`test_verifier_uniqueness`.

---

### FR-AUTHV-002 — PKCE Code-Verifier Ingestion & Validation

| Field | Value |
|-------|-------|
| **Title** | Server-side validation of client-supplied code verifier |
| **PR** | #30 |
| **RFC** | RFC 7636 §4.1 |

**Description**  
The system SHALL accept a client-supplied verifier string and validate its length
(`[43, 128]`) and character set before accepting it into the PKCE flow.  Out-of-range or
non-unreserved-ASCII inputs MUST return `AuthError::ValidationError`.

**Acceptance Criteria**

1. Valid 43-char alphabetic string: accepted.
2. Strings shorter than 43 chars: rejected.
3. Strings longer than 128 chars: rejected.
4. Strings containing `+`, space, or non-ASCII: rejected.

**Traceability**  
`CodeVerifier::from_string()`.  
Tests: `test_verifier_from_string_valid`, `test_verifier_from_string_too_short_rejected`,
`test_verifier_from_string_too_long_rejected`, `test_verifier_from_string_bad_chars_rejected`.

---

### FR-AUTHV-003 — PKCE S256 Challenge Derivation

| Field | Value |
|-------|-------|
| **Title** | S256 code-challenge derivation |
| **PR** | #30 |
| **RFC** | RFC 7636 §4.2, §4.6, Appendix B |

**Description**  
The system SHALL derive an S256 code challenge as
`BASE64URL(SHA-256(ASCII(code_verifier)))` (RFC 7636 §4.6).  The `plain` method is
explicitly unsupported to prevent downgrade attacks.

**Acceptance Criteria**

1. RFC 7636 Appendix B known-answer vector passes:
   verifier `dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk` → challenge
   `E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM`.
2. Challenge derived from the same verifier verifies successfully.
3. Challenge derived from a different verifier fails verification.

**Traceability**  
`CodeVerifier::to_challenge()`, `CodeChallenge::verify()`.  
Tests: `test_s256_challenge_derivation_known_vector`,
`test_challenge_verify_correct_verifier_succeeds`,
`test_challenge_verify_wrong_verifier_fails`.

---

### FR-AUTHV-004 — PKCE Constant-Time Challenge Verification

| Field | Value |
|-------|-------|
| **Title** | Constant-time verifier-challenge comparison |
| **PR** | #30 |
| **RFC** | RFC 7636 §4.6 |

**Description**  
Challenge verification SHALL use a byte-by-byte XOR accumulation pattern equivalent to
`subtle::ConstantTimeEq` to prevent timing-oracle attacks.  A length mismatch fails
immediately (length is public information and does not constitute an oracle).

**Acceptance Criteria**

1. Correct verifier → `Ok(())`.
2. Wrong verifier → `Err(ValidationError("code_challenge mismatch"))`.
3. No early-exit branch on content bytes (XOR-fold, single conditional at end).

**Traceability**  
`CodeChallenge::verify()` (lines 107-126 `src/domain/pkce.rs`).

---

### FR-AUTHV-005 — CSRF State Generation & Constant-Time Verification

| Field | Value |
|-------|-------|
| **Title** | Opaque OAuth2 state parameter (CSRF protection) |
| **PR** | #30 |
| **RFC** | RFC 6749 §10.12 |

**Description**  
The system SHALL generate a 32-byte cryptographically-random state value
(base64url-encoded) for binding authorization requests to client sessions.
Incoming state MUST be verified with constant-time comparison; mismatch MUST return
`AuthError::ValidationError("state parameter mismatch (CSRF check failed)")`.

**Acceptance Criteria**

1. Two independently-generated states are unique.
2. `state.verify(state.as_str())` succeeds.
3. `state.verify(other_state.as_str())` fails.
4. `state.verify("")` fails.

**Traceability**  
`OAuthState::new()`, `OAuthState::verify()`.  
Tests: `test_state_uniqueness`, `test_state_verify_matching_state_passes`,
`test_state_verify_wrong_state_rejected`, `test_state_verify_empty_rejected`.

---

### FR-AUTHV-006 — Secret Vault AEAD Encryption at Rest

| Field | Value |
|-------|-------|
| **Title** | ChaCha20-Poly1305 AEAD at-rest encryption for secrets |
| **PR** | #31 (`feat(vault): ChaCha20-Poly1305 AEAD at-rest encryption for secrets`) |
| **RFC** | RFC 8439 (ChaCha20-Poly1305) |

**Description**  
The system SHALL encrypt every secret with ChaCha20-Poly1305 AEAD using a fresh
96-bit (12-byte) random nonce per seal operation.  The on-wire/on-disk envelope is
`nonce (12 B) || ciphertext+tag`.  The 256-bit master key never leaves the `VaultKey`
struct and is zeroed on drop.

**Acceptance Criteria**

1. Round-trip encrypt/decrypt returns original bytes (byte, Unicode, empty value).
2. Decryption with a wrong key returns `VaultError::DecryptionFailed`.
3. Bit-flip in ciphertext body returns `VaultError::DecryptionFailed` (AEAD tag rejection).
4. Bit-flip in AEAD tag returns `VaultError::DecryptionFailed`.
5. Bit-flip in nonce returns `VaultError::DecryptionFailed`.
6. Two encryptions of identical plaintext produce different ciphertexts (nonce uniqueness).
7. 1000 consecutive seal operations produce 1000 unique nonces.

**Traceability**  
`src/domain/vault.rs` — `EncryptedBlob::seal()`, `EncryptedBlob::open()`, `VaultKey`.  
Tests: `round_trip_bytes`, `round_trip_unicode`, `round_trip_empty_value`,
`wrong_key_fails_to_decrypt`, `tampered_ciphertext_rejected`, `tampered_tag_rejected`,
`tampered_nonce_rejected`, `nonces_are_unique_across_encryptions`,
`same_plaintext_yields_different_ciphertexts`.

---

### FR-AUTHV-007 — Secret Vault TTL / Expiry

| Field | Value |
|-------|-------|
| **Title** | Optional TTL with automatic expiry enforcement |
| **PR** | #31 |

**Description**  
`SecretVault::put()` SHALL accept an optional `ttl_seconds: Option<i64>`.  When
`Some(secs)`, `expires_at` is set to `Utc::now() + secs`.  Any `get()` on an expired
entry MUST return `VaultError::Expired` without decrypting.

**Acceptance Criteria**

1. Secret with `ttl=60` is readable immediately.
2. Secret with `ttl=-1` (already expired) returns `VaultError::Expired` on `get()`.
3. `list()` excludes expired entries.

**Traceability**  
`SecretVault::put()`, `SecretVault::get()`, `SecretVault::list()`, `VaultEntry::is_expired()`.  
Tests: `ttl_secret_accessible_before_expiry`, `expired_secret_returns_error`,
`list_excludes_expired_entries`.

---

### FR-AUTHV-008 — Secret Vault Key Rotation

| Field | Value |
|-------|-------|
| **Title** | In-place secret rotation with fresh nonce and version increment |
| **PR** | #31 |

**Description**  
`SecretVault::rotate()` SHALL re-encrypt the existing plaintext with a fresh random
nonce, increment the version counter, and preserve the plaintext value.

**Acceptance Criteria**

1. Nonce before and after rotation differ.
2. Version increments by 1 on each `put()` or `rotate()` call.
3. Plaintext is still recoverable after rotation.
4. `rotate()` on an expired or missing entry returns an error.

**Traceability**  
`SecretVault::rotate()`.  
Tests: `rotate_re_encrypts_with_new_nonce`, `rotate_increments_version`,
`version_increments_on_put`.

---

### FR-AUTHV-009 — Secret Vault Key Construction

| Field | Value |
|-------|-------|
| **Title** | VaultKey generation and import |
| **PR** | #31 |

**Description**  
`VaultKey::generate()` SHALL produce a fresh CSPRNG 256-bit key.
`VaultKey::from_bytes()` SHALL accept exactly 32 bytes (e.g., from a KMS);
other lengths MUST return `VaultError::InvalidKeyLength`.

**Acceptance Criteria**

1. `from_bytes(&[0u8; 16])` → `Err(InvalidKeyLength)`.
2. Key generated → exported raw → re-imported → encrypts/decrypts correctly.

**Traceability**  
`VaultKey::generate()`, `VaultKey::from_bytes()`.  
Tests: `vault_key_from_bytes_wrong_length_fails`, `vault_key_from_bytes_round_trip`.

---

### FR-AUTHV-010 — Bearer Token Validation

| Field | Value |
|-------|-------|
| **Title** | HTTP `Authorization: Bearer <jwt>` validation |
| **PR** | #32 (`feat: add bearer token validation`) |
| **RFC** | RFC 6750 §2.1, RFC 7519 (JWT), RFC 7662 (token introspection concepts) |

**Description**  
The system SHALL parse an `Authorization` header value of the form `Bearer <token>`,
validate the JWT signature, expiry (`exp`), not-before (`nbf`), issuer (`iss`), and
audience (`aud`) claims, and return decoded `Claims` on success.  Any deviation MUST
return a typed `AuthError` variant.

**Acceptance Criteria**

1. Valid `Bearer <jwt>` with correct issuer/audience → `Ok(Claims)`.
2. Expired token → `Err(AuthError::Expired)`.
3. Wrong signing key → `Err(AuthError::BadSignature)`.
4. Wrong audience → `Err(AuthError::WrongAudience)`.
5. Non-`Bearer` scheme or extra whitespace-separated tokens → `Err(AuthError::Malformed)`.
6. Missing scheme token → `Err(AuthError::Malformed)`.

**Traceability**  
`src/domain/auth.rs` — `Authenticator::validate_bearer_token()`,
`Authenticator::validation()`.  
Integration tests: `test_validate_bearer_token` (integration_tests.rs line 134),  
Unit tests: `test_validate_bearer_token_success`, `test_validate_bearer_token_expired`,
`test_validate_bearer_token_bad_signature`, `test_validate_bearer_token_wrong_audience`,
`test_validate_bearer_token_malformed`.

---

### FR-AUTHV-011 — JWT Generation with Standard Claims

| Field | Value |
|-------|-------|
| **Title** | JWT access-token generation with `sub`, `iss`, `aud`, `exp`, `iat`, `nbf`, `jti`, `roles` |
| **PR** | Pre-existing; hardened by #32 |
| **RFC** | RFC 7519 §4.1 |

**Description**  
`Authenticator::generate_token()` SHALL produce a signed JWT containing all registered
claim names (`sub`, `iss`, `aud`, `exp`, `iat`, `nbf`, `jti`) plus a `roles` array.
The default expiry is 24 hours.  Custom expiry is available via
`generate_token_with_expiry()`.

**Acceptance Criteria**

1. Generated token verifies with the same `Authenticator`.
2. Decoded `claims.sub` matches the source `UserId`.
3. Decoded `claims.roles` contains supplied role names.
4. Custom expiry produces a token with the correct `exp` timestamp.

**Traceability**  
`Claims::new()`, `Authenticator::generate_token()`,
`Authenticator::generate_token_with_expiry()`.  
Tests: `test_generate_and_verify_token`, `test_expired_token`.

---

## 2. Non-Functional Requirements

### NFR-AUTHV-001 — Cryptographic Correctness: S256 Only

| Field | Value |
|-------|-------|
| **Title** | Exclusive use of S256 PKCE method; no `plain` downgrade |
| **PR** | #30 |
| **RFC** | RFC 7636 §4.2 |

**Description**  
The PKCE implementation SHALL support only the S256 method.  The `plain`
method MUST NOT be accepted, preventing downgrade attacks.

**Evidence**  
`CodeVerifier::to_challenge()` always computes `SHA-256`; no `method` parameter exists.

---

### NFR-AUTHV-002 — Cryptographic Correctness: Constant-Time Comparisons

| Field | Value |
|-------|-------|
| **Title** | All secret-comparison paths are constant-time |
| **PR** | #30 |

**Description**  
All comparisons of cryptographic material (PKCE challenge, OAuth state) SHALL use
accumulator-XOR or `subtle::ConstantTimeEq` patterns.  No early-exit on content bytes
is permitted.

**Evidence**  
`CodeChallenge::verify()` and `OAuthState::verify()` both use
`fold(0u8, |acc, (a, b)| acc | (a ^ b))` — single exit after full scan.

---

### NFR-AUTHV-003 — Cryptographic Correctness: Random Nonce per Seal

| Field | Value |
|-------|-------|
| **Title** | Fresh 96-bit CSPRNG nonce for every ChaCha20-Poly1305 seal |
| **PR** | #31 |

**Description**  
Each call to `EncryptedBlob::seal()` SHALL generate a fresh nonce via
`ChaCha20Poly1305::generate_nonce(&mut OsRng)`.  Nonce reuse under the same key MUST
be operationally impossible.

**Evidence**  
`nonces_are_unique_across_encryptions` — 1000 seals with identical plaintext produce
1000 distinct nonces (probability of collision ≤ 2⁻⁹⁶).

---

### NFR-AUTHV-004 — Cryptographic Correctness: ZeroizeOnDrop for Key Material

| Field | Value |
|-------|-------|
| **Title** | Master vault key zeroed from memory on drop |
| **PR** | #31 |

**Description**  
`VaultKey` SHALL derive `zeroize::ZeroizeOnDrop` so its 32-byte raw array is
overwritten with zeros when the struct is dropped, preventing key material from
lingering in heap/stack memory.

**Evidence**  
`#[derive(Clone, ZeroizeOnDrop)]` on `VaultKey`; `zeroize` crate in `Cargo.toml`.

---

### NFR-AUTHV-005 — No Hand-Rolled Cryptography

| Field | Value |
|-------|-------|
| **Title** | Vetted crate usage for all cryptographic primitives |
| **PR** | #30, #31 |

**Description**  
All cryptographic operations SHALL use vetted RustCrypto ecosystem crates:

| Primitive | Crate |
|-----------|-------|
| AEAD | `chacha20poly1305` |
| Hash | `sha2` |
| Base64url | `base64` (general_purpose::URL_SAFE_NO_PAD) |
| CSPRNG | `rand` (OsRng) |
| Zeroize | `zeroize` |
| JWT | `jsonwebtoken` |

No custom implementations of AES, SHA, or MAC are permitted.

---

### NFR-AUTHV-006 — Tamper Detection via AEAD Authentication Tag

| Field | Value |
|-------|-------|
| **Title** | Any single-bit mutation in ciphertext, tag, or nonce is detected |
| **PR** | #31 |

**Description**  
The Poly1305 authentication tag SHALL ensure that any modification to the
ciphertext envelope — body, tag, or nonce — causes decryption to fail with
`VaultError::DecryptionFailed` before any plaintext is returned.

**Evidence**  
Tests: `tampered_ciphertext_rejected`, `tampered_tag_rejected`,
`tampered_nonce_rejected`.

---

### NFR-AUTHV-007 — JWT Claim Validation (Expiry, Issuer, Audience)

| Field | Value |
|-------|-------|
| **Title** | JWT decoder enforces `exp`, `nbf`, `iss`, `aud` |
| **PR** | #32 |
| **RFC** | RFC 7519 §4.1, RFC 6750 |

**Description**  
`Authenticator::validation()` SHALL configure `jsonwebtoken::Validation` with
`validate_exp = true`, `validate_nbf = true`, explicit issuer, and explicit audience.
Each failure maps to a distinct `AuthError` variant for consumer diagnostic clarity.

**Evidence**  
`Authenticator::validation()` (`auth.rs` lines 144-151); `decode_token()` error mapping
(lines 157-168).

---

### NFR-AUTHV-008 — Bearer Token Header Strict Parsing

| Field | Value |
|-------|-------|
| **Title** | `Bearer` scheme check is case-insensitive; extra tokens rejected |
| **PR** | #32 |
| **RFC** | RFC 6750 §2.1 |

**Description**  
The bearer token parser SHALL accept `Bearer` (case-insensitive) followed by exactly
one token.  Headers with a different scheme, no token, or extra whitespace-separated
tokens SHALL return `AuthError::Malformed`.

**Evidence**  
`validate_bearer_token()` uses `eq_ignore_ascii_case("Bearer")` and checks
`parts.next().is_some()` after extracting scheme+token.

---

### NFR-AUTHV-009 — Test Coverage: Cryptographic Rejection Paths

| Field | Value |
|-------|-------|
| **Title** | All cryptographic failure paths have dedicated regression tests |
| **PR** | #30, #31, #32 |

**Description**  
Every rejection path for PKCE, vault AEAD, and bearer-token validation SHALL have at
least one dedicated unit test exercising that exact failure mode (not just the success
path).

**Evidence**  
Tests covering rejection paths:

- PKCE: `test_verifier_from_string_too_short_rejected`,
  `test_verifier_from_string_too_long_rejected`,
  `test_verifier_from_string_bad_chars_rejected`,
  `test_challenge_verify_wrong_verifier_fails`,
  `test_state_verify_wrong_state_rejected`,
  `test_state_verify_empty_rejected`.
- Vault: `wrong_key_fails_to_decrypt`, `tampered_ciphertext_rejected`,
  `tampered_tag_rejected`, `tampered_nonce_rejected`, `expired_secret_returns_error`,
  `missing_secret_returns_not_found`, `vault_key_from_bytes_wrong_length_fails`.
- Bearer: `test_validate_bearer_token_expired`,
  `test_validate_bearer_token_bad_signature`,
  `test_validate_bearer_token_wrong_audience`,
  `test_validate_bearer_token_malformed`.

---

## 3. Gaps / PLANNED

| ID | Area | Gap | Status |
|----|------|-----|--------|
| GAP-001 | PKCE | `code_challenge_method` negotiation — server must reject `plain` at the protocol level, not just by omission | PLANNED |
| GAP-002 | Vault | Persistent backend (e.g., Redis/Postgres) — current `SecretVault` is in-memory only; restarts lose all secrets | PLANNED |
| GAP-003 | Vault | Key-wrapping / KMS integration — `VaultKey` can be loaded from bytes but there is no KMS plugin interface | PLANNED |
| GAP-004 | Vault | Audit log — no record of `put`, `rotate`, `get`, or `remove` operations with caller identity | PLANNED |
| GAP-005 | Tokens | Refresh-token rotation — `refresh_token()` re-uses the same `sub`/`roles` without invalidating the prior token | PLANNED |
| GAP-006 | Tokens | Token revocation list — no mechanism to revoke a non-expired JWT before its `exp` | PLANNED |
| GAP-007 | Bearer | Asymmetric (RS256/ES256) signing key support — current implementation is HMAC-only | PLANNED |
| GAP-008 | PKCE | State binding to server session — `OAuthState` is generated but the server-side session association is not enforced at the middleware layer | PLANNED |
| GAP-009 | General | Rate-limiting on failed auth attempts — no brute-force protection for verifier/state/bearer endpoints | PLANNED |
| GAP-010 | General | Tracera / AgilePlus middleware adapter — wiring of these requirements into Axum tower layers for consumer repos not yet documented | PLANNED |
