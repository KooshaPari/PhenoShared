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

---

### FR-AUTHV-012 — JWT Token Revocation List (Deny-List)

| Field | Value |
|-------|-------|
| **Title** | JTI-based token revocation with TTL eviction |
| **PR** | feat/token-revocation |
| **RFC** | RFC 7519 §4.1.7 (`jti` claim), RFC 7009 (Token Revocation concepts) |
| **Status** | SHIPPED |

**Description**
The system SHALL provide a `RevocationStore` PORT (trait) with `revoke(jti, exp)` and
`is_revoked(jti)` methods.  An in-memory adapter SHALL implement the port with automatic
TTL-based eviction: on every `revoke` call, entries whose `exp` is already in the past
are pruned, bounding the deny-list to only live tokens.  `Authenticator` SHALL accept
an optional `Arc<dyn RevocationStore>` via `with_revocation_store()`; when set, every
decoded token MUST be checked after signature/expiry validation, and tokens whose `jti`
is revoked MUST return `AuthError::Revoked`.

**Acceptance Criteria**

1. A valid token with no revocation store attached passes normally.
2. After `revoke(jti, exp)`, a token with that `jti` returns `Err(AuthError::Revoked)`.
3. A token with a different `jti` is unaffected by revocation of another `jti`.
4. Entries with `exp` in the past are evicted on the next `revoke` call (memory bounded).
5. An `Authenticator` without a store attached continues to work normally (backward compatible).

**Design**
- `RevocationStore` trait lives in `src/domain/ports.rs` (hexagonal port).
- `InMemoryRevocationStore` adapter in `src/adapters/revocation.rs`; uses `Mutex<HashMap<String, Entry>>`.
- `Authenticator::with_revocation_store(Arc<dyn RevocationStore>)` builder method; revocation check
  runs after successful JWT decode to avoid unnecessary store queries on structurally invalid tokens.
- `AuthError::Revoked` variant added to `src/domain/errors.rs`.

**Traceability**
- `src/domain/ports.rs` — `RevocationStore` trait.
- `src/adapters/revocation.rs` — `InMemoryRevocationStore`, TTL eviction.
- `src/domain/auth.rs` — `Authenticator::with_revocation_store()`, revocation check in `decode_token()`, `AuthError::Revoked`.
- Domain tests (auth.rs): `test_valid_token_passes_revocation_check`,
  `test_revoked_token_is_rejected`, `test_different_jti_is_unaffected_by_revocation`,
  `test_expired_revocation_entry_no_longer_blocks`, `test_authenticator_without_store_ignores_revocation`.
- Adapter tests (revocation.rs): `revoke_then_is_revoked_returns_true`,
  `unrevoked_jti_is_not_revoked`, `expired_entries_are_evicted_on_next_revoke`,
  `fresh_revoked_entry_survives_eviction_pass`, `multiple_distinct_jtis_tracked_independently`.

---

### FR-AUTHV-013 — Refresh-Token Rotation with Reuse Detection

| Field | Value |
|-------|-------|
| **Title** | Stateful refresh-token rotation with compromise detection |
| **PR** | #35 |
| **Branch** | `feat/refresh-token-rotation` |
| **RFC** | RFC 6749 §6 (Refreshing an Access Token), OAuth 2.0 Security BCP §2.2.2 |
| **Status** | SHIPPED |

**Description**
The system SHALL issue an opaque refresh token (itself a JWT with `typ=refresh`) alongside every access token via `issue_token_pair()`.  `rotate(refresh_token)` SHALL validate the presented refresh token's signature, expiry, and `typ` claim, then issue a NEW access+refresh pair and INVALIDATE the old refresh JTI via the existing `RevocationStore` port.  If the presented refresh token's JTI does NOT match the currently-registered JTI for its token family (reuse/compromise signal), the system SHALL revoke the entire token family and return `AuthError::CompromisedTokenFamily`.

**Acceptance Criteria**

1. `issue_token_pair()` returns an `access_token`, a `refresh_token`, and a stable `family_id`.
2. `rotate(refresh_token)` with a valid refresh token returns a new pair; the new access token validates; the family_id is preserved.
3. Presenting an already-rotated (stale) refresh token returns `Err(AuthError::CompromisedTokenFamily)`.
4. `rotate()` with an expired refresh token returns `Err(AuthError::Expired)`.
5. The new access token from a rotated pair validates with correct `sub` and `roles`.
6. A refresh token MUST NOT be accepted as a bearer access token.
7. `issue_token_pair()` without a store attached returns an error (backward compatible).

**Design**
- `RefreshTokenStore` port in `src/domain/ports.rs` — `insert_family`, `rotate`, `revoke_family`.
- `InMemoryRefreshTokenStore` adapter in `src/adapters/refresh_token.rs`; lazy TTL eviction on every write.
- `RefreshClaims` struct in `src/domain/auth.rs` carries `sub`, `iss`, `exp`, `iat`, `jti`, `family_id`, `typ="refresh"`, `roles`.
- `Authenticator::issue_token_pair()` and `Authenticator::rotate()` builder methods.
- `AuthError::CompromisedTokenFamily` and `AuthError::InvalidRefreshToken` variants added.
- Refresh token validation uses `leeway = 0` (strict expiry, no clock-skew tolerance).

**Traceability**
- PR: #35 (`feat/refresh-token-rotation` — refresh-token rotation with reuse detection)
- `src/domain/ports.rs` — `RefreshTokenStore` trait.
- `src/adapters/refresh_token.rs` — `InMemoryRefreshTokenStore`, lazy eviction.
- `src/domain/auth.rs` — `TokenPair`, `RefreshClaims`, `Authenticator::issue_token_pair()`, `Authenticator::rotate()`, `make_refresh_token()`, `decode_refresh_token()`.
- `src/domain/errors.rs` — `AuthError::CompromisedTokenFamily`, `AuthError::InvalidRefreshToken`.
- Domain tests (auth.rs): `test_rotate_valid_refresh_issues_new_pair`,
  `test_rotate_reused_refresh_token_returns_compromise_error`,
  `test_rotate_expired_refresh_token_rejected`,
  `test_rotated_access_token_validates`,
  `test_refresh_token_is_not_valid_as_access_token`,
  `test_issue_token_pair_without_store_errors`.
- Adapter tests (refresh_token.rs): `insert_then_rotate_succeeds_with_correct_old_jti`,
  `rotate_with_wrong_old_jti_returns_compromise`,
  `rotate_unknown_family_returns_not_found`,
  `revoke_family_removes_entry`,
  `expired_families_are_evicted_on_next_insert`,
  `multiple_families_tracked_independently`.

---

### FR-AUTHV-014 — Audit Log: AuditSink port + AuditEvent wired into token/vault flows

| Field | Value |
|-------|-------|
| **Title** | Audit-log sink with structured events for all security-relevant token and vault operations |
| **Branch** | `feat/audit-log` |
| **Status** | SHIPPED |

**Description**
The system SHALL emit a structured `AuditEvent` for every security-relevant operation: token issue, validate, reject, revoke, rotate, and vault read/write.  Events MUST NOT contain token values or plaintext secrets — only opaque identifiers (`jti`, subject UUID, vault key name).

**Acceptance Criteria**

1. `AuditSink` port trait (`record(&self, AuditEvent)`) defined in `domain/ports.rs`; `Send + Sync`.
2. `AuditEvent` fields: `timestamp` (UTC), `actor` (Option<String>), `subject` (jti / key name), `action` (enum), `outcome` (Success/Failure), `reason` (Option<String> — never contains secret material).
3. `AuditAction` variants: `TokenIssued`, `TokenValidated`, `TokenRejected`, `TokenRevoked`, `TokenRotated`, `VaultRead`, `VaultWrite`.
4. `InMemoryAuditSink` adapter (spy pattern for tests) — `events()` / `drain()`.
5. `TracingAuditSink` adapter — emits structured `tracing::info!` records at INFO level.
6. `Authenticator::with_audit_sink()` wires sink into all token operations.
7. `SecretVault::with_audit_sink()` wires sink into all vault `put`/`get`/`rotate`/`remove` operations.
8. No token value or plaintext secret appears in any `AuditEvent` field.
9. All existing tests continue to pass (no breaking changes).

**Design**
- `AuditSink` is an optional port (`Option<Arc<dyn AuditSink>>`); absent sink = no-op (zero overhead).
- `AuditEvent::success(actor, subject, action)` and `AuditEvent::failure(actor, subject, action, reason)` constructors.
- `subject` for token events = JTI (opaque random UUID, not the token string); for vault events = key name.
- `reason` for failures = error variant description (e.g., "token expired") — never raw token bytes.

**Traceability**
- `src/domain/ports.rs` — `AuditSink` trait, `AuditEvent`, `AuditAction`, `AuditOutcome`.
- `src/adapters/audit.rs` — `InMemoryAuditSink`, `TracingAuditSink`.
- `src/domain/auth.rs` — `Authenticator::with_audit_sink()`, `Authenticator::audit()`, emission in `generate_token()`, `decode_token()`, `rotate()`.
- `src/domain/vault.rs` — `SecretVault::with_audit_sink()`, `SecretVault::audit()`, emission in `put()`, `get()`, `rotate()`, `remove()`.
- Domain tests (auth.rs): `audit_token_issued_on_generate`, `audit_token_validated_on_verify_success`, `audit_token_rejected_on_expired`, `audit_token_revoked_emits_correct_event`, `audit_token_rotated_on_success`, `audit_token_rejected_on_compromised_rotation`.
- Domain tests (vault.rs): `vault_put_emits_vault_write_success`, `vault_get_emits_vault_read_success`, `vault_get_expired_emits_vault_read_failure_with_reason`, `vault_rotate_emits_read_then_write`, `vault_audit_event_contains_no_plaintext_secret`.
- Adapter tests (audit.rs): `in_memory_sink_records_events`, `in_memory_sink_records_failure_with_reason`, `in_memory_sink_drain_clears_events`, `in_memory_sink_multiple_events_in_order`, `tracing_sink_does_not_panic`.

---

---

### FR-AUTHV-015 — KMS Envelope Encryption for Secret Vault

| Field | Value |
|-------|-------|
| **Title** | Per-secret DEK envelope encryption via hexagonal `KeyManagementService` port |
| **Branch** | `feat/kms-envelope-encryption` |
| **Status** | SHIPPED |

**Description**
The system SHALL encrypt each secret with a unique per-secret Data-Encryption Key (DEK) generated
by a `KeyManagementService` (KMS) port.  The DEK is wrapped (encrypted) by a Key-Encryption Key
(KEK) before storage; only the wrapped DEK is persisted alongside the ciphertext.  The plaintext
DEK SHALL be `ZeroizeOnDrop` and dropped immediately after each seal / open operation.  A local
in-process adapter implements the port using ChaCha20-Poly1305 AEAD; cloud adapters (AWS KMS,
GCP Cloud KMS, HashiCorp Vault) can be substituted without touching domain code.

**Acceptance Criteria**

1. Round-trip: `put()` generates a fresh DEK, seals the secret, stores the wrapped DEK;
   `get()` unwraps the DEK via KMS and decrypts the ciphertext — original plaintext recovered.
2. Wrong KEK rejects unwrap: transplanting an entry into a vault backed by a different KEK
   returns `VaultError::DecryptionFailed`.
3. Each secret gets a distinct DEK: two `put()` calls produce different `wrapped_dek` values.
4. Tampered wrapped-DEK rejected: a single bit-flip in the stored wrapped DEK causes
   `get()` to return `VaultError::DecryptionFailed`.
5. Plaintext DEK zeroed on drop (`ZeroizeOnDrop` on `DataKey.plaintext` and `VaultKey`).
6. `LocalKmsAdapter` requires no external infrastructure; seam/TODO for AWS/GCP/HashiCorp
   adapters is documented in `src/adapters/kms.rs`.

**Design**
- `KeyManagementService` trait + `DataKey` struct + `KmsError` in `src/domain/ports.rs` (hexagonal port).
- `LocalKmsAdapter` in `src/adapters/kms.rs` — wraps/unwraps DEKs with AEAD using master KEK.
- `KmsVaultEntry` and `KmsSecretVault` in `src/domain/vault.rs` — envelope-encrypted vault.
- `DataKey.plaintext` derives `zeroize::ZeroizeOnDrop`; `LocalKmsAdapter.kek` zeroized in `Drop`.

**Traceability**
- `src/domain/ports.rs` — `KeyManagementService` trait, `DataKey`, `KmsError`.
- `src/adapters/kms.rs` — `LocalKmsAdapter`, `generate_data_key`, `decrypt_data_key`.
- `src/domain/vault.rs` — `KmsVaultEntry`, `KmsSecretVault`.
- Adapter tests (kms.rs): `generate_and_decrypt_round_trip`, `wrong_kek_fails_to_unwrap`,
  `each_generate_produces_distinct_dek`, `tampered_wrapped_dek_rejected`,
  `no_dek_reuse_across_many_generations`.
- Domain tests (vault.rs): `kms_vault_round_trip`, `kms_vault_round_trip_unicode`,
  `kms_vault_round_trip_empty`, `kms_vault_wrong_kek_fails_to_decrypt`,
  `kms_vault_each_secret_has_distinct_dek`, `kms_vault_tampered_wrapped_dek_rejected`,
  `kms_vault_rotate_uses_new_dek`.

---

---

### FR-AUTHV-016 — VaultStore Persistent Backend (Hexagonal Port + Adapters)

| Field | Value |
|-------|-------|
| **Title** | Swappable vault storage via hexagonal `VaultStore` port with in-memory and file-backed adapters |
| **Branch** | `feat/vault-persistence` |
| **Status** | SHIPPED |

**Description**
The system SHALL expose a `VaultStore` PORT (trait: `put(key, VaultEntry)`, `get(key)`,
`delete(key)`, `list_keys()`) so vault storage is swappable without changing domain code.
TWO adapters are provided:

1. `InMemoryVaultStore` — the pre-existing in-memory behaviour refactored behind the port.
2. `FileVaultStore` — encrypted-at-rest records serialised to a file via `serde_json`.
   Records contain only AEAD-sealed ciphertext + wrapped DEK (already produced by the
   existing `EncryptedBlob`/KMS pipeline); the file holds **no plaintext secrets**.
   Writes are atomic (write-to-tmp then `fs::rename`).
   Corrupt files are handled gracefully — `open()` returns `Err` rather than panicking.

Clear TODO seams for `RedisVaultStore` and `PostgresVaultStore` are documented in
`src/adapters/vault_store.rs`.

**Acceptance Criteria**

1. File adapter round-trip: persist sealed records → reload from disk → decrypt succeeds.
2. In-memory adapter: all CRUD operations work correctly.
3. File contains NO plaintext secret bytes (assert with byte-level search).
4. `delete` and `list_keys` work for both adapters.
5. Corrupt file handled gracefully (no panic; returns `Err`).
6. All pre-existing tests continue to pass (no regressions).

**Traceability**
- `src/domain/ports.rs` — `VaultStore` trait.
- `src/adapters/vault_store.rs` — `InMemoryVaultStore`, `FileVaultStore`.
- Adapter tests (vault_store.rs): `in_memory_put_get_round_trip`, `in_memory_missing_key_returns_none`,
  `in_memory_delete_removes_entry`, `in_memory_delete_absent_returns_false`,
  `in_memory_list_keys_returns_all`, `file_store_round_trip_persist_reload`,
  `file_store_delete_persists`, `file_store_list_keys_works`,
  `file_contains_no_plaintext_secret`, `corrupt_file_handled_gracefully`,
  `file_store_decrypt_after_reload_succeeds`.

---

### FR-AUTHV-017 — Asymmetric JWT Signing (RS256 / ES256)

| Field | Value |
|-------|-------|
| **Title** | Configurable asymmetric JWT signing via RS256 (RSA PKCS#1 v1.5) and ES256 (ECDSA P-256) |
| **Branch** | `feat/asymmetric-signing` |
| **RFC** | RFC 7518 §3.3 (RS256), §3.4 (ES256), RFC 7515 (JWS) |
| **Status** | SHIPPED |

**Description**
The system SHALL support three JWT signing algorithms via a `SigningKey` enum: `Hmac(secret)`,
`Rs256 { private_pem, public_pem }`, and `Es256 { private_pem, public_pem }`.  The selected
algorithm is pinned in `jsonwebtoken::Validation`, ensuring the decoder **rejects tokens whose
`alg` header differs** from the configured algorithm.  This closes the alg-confusion attack
surface (RFC 7515 §10.7) and prevents `alg=none` bypass.

**Acceptance Criteria**

1. RS256 round-trip: token signed with RSA private key verifies with RSA public key.
2. ES256 round-trip: token signed with EC private key verifies with EC public key.
3. HS256 continues to work (no breaking changes to existing `Authenticator::new(secret)` API).
4. Alg-confusion: RS256 token rejected by HS256 verifier; HS256 token rejected by RS256 verifier.
5. `alg=none`: hand-crafted unsigned token rejected by all three algorithm verifiers.
6. Wrong key: token signed with one key is rejected by a verifier with a different key.

**Design**
- `SigningKey` enum in `src/domain/signing.rs` — `Hmac`, `Rs256`, `Es256` variants.
- `SigningKey::encoding_key()` / `decoding_key()` bridge to `jsonwebtoken::EncodingKey` / `DecodingKey`.
- `Authenticator::with_signing_key(key: SigningKey)` constructor; `Authenticator::new(secret)` is a
  backward-compatible shim that wraps `SigningKey::Hmac`.
- `Authenticator::validation()` calls `Validation::new(self.signing_key.algorithm())` to pin the alg.
- EC private keys must be PKCS#8 PEM (`BEGIN PRIVATE KEY`); SEC1 (`BEGIN EC PRIVATE KEY`) is not
  accepted by `jsonwebtoken`.

**Traceability**
- `src/domain/signing.rs` — `SigningKey` enum, `encoding_key()`, `decoding_key()`, `algorithm()`.
- `src/domain/auth.rs` — `Authenticator::with_signing_key()`, updated `generate_token()`,
  `decode_token()`, `validation()`, `make_refresh_token()`, `decode_refresh_token()`.
- `src/domain/mod.rs` — `pub mod signing`, `pub use signing::SigningKey`.
- `Cargo.toml` — `jsonwebtoken = { version = "9", features = ["use_pem"] }`.
- Domain tests (auth.rs): `rs256_round_trip`, `es256_round_trip`,
  `hs256_still_works_after_asymmetric_refactor`, `alg_confusion_rs256_token_rejected_by_hs256_verifier`,
  `alg_confusion_hs256_token_rejected_by_rs256_verifier`, `alg_none_token_is_rejected`,
  `rs256_wrong_key_rejected`, `es256_wrong_key_rejected`.

---

### FR-AUTHV-018 — PKCE State Binding to Server Session at Middleware

| Field | Value |
|-------|-------|
| **Title** | Middleware-enforced binding of OAuth `state` to the active server session |
| **Branch** | `feat/gap008-pkce-session-binding` |
| **Status** | SHIPPED |

**Description**  
The system SHALL bind OAuth `state` tokens to the server session that initiated the authorization
request and enforce that binding in the callback middleware. On an OAuth callback, the middleware
MUST extract the `state` query parameter and session cookie, verify the pair against the session
binding store, and reject the callback with a 401 JSON body when the state is missing, unbound, or
bound to a different session.

**Acceptance Criteria**

1. A callback with a valid `state` and matching session cookie passes through to the handler.
2. A callback with no `state` query parameter returns `401` with `{"error":"invalid_state",...}`.
3. A callback with a missing session cookie returns `401` with `{"error":"invalid_state",...}`.
4. A callback whose `state` is bound to a different session returns `401` with `{"error":"invalid_state",...}`.
5. An expired binding is treated as invalid and rejected with the same 401 response.

**Traceability**  
`src/domain/session_store.rs` — `SessionStore`, `InMemorySessionStore`.  
`src/middleware/pkce_state_session.rs` — `enforce_pkce_state_session()`, query/cookie extraction, 401 JSON response.  
Tests: `bind_and_verify_state_succeeds`, `verify_wrong_session_fails`, `verify_missing_state_fails`,
`revoke_state_removes_binding`, `expired_state_is_rejected`, `rebinding_state_overwrites_previous_session`,
`valid_binding_allows_callback`, `missing_state_is_rejected`, `missing_cookie_is_rejected`,
`wrong_session_binding_is_rejected`, `expired_state_is_rejected`.

---

## 3. Gaps / PLANNED

| ID | Area | Gap | Status |
|----|------|-----|--------|
| GAP-001 | PKCE | `code_challenge_method` negotiation — server must reject `plain` at the protocol level, not just by omission | PLANNED |
| GAP-002 | Vault | Persistent backend (e.g., Redis/Postgres) — current `SecretVault` is in-memory only; restarts lose all secrets | SHIPPED → FR-AUTHV-016 |
| GAP-003 | Vault | Key-wrapping / KMS integration — `VaultKey` can be loaded from bytes but there is no KMS plugin interface | SHIPPED → FR-AUTHV-015 |
| GAP-004 | Vault | Audit log — no record of `put`, `rotate`, `get`, or `remove` operations with caller identity | SHIPPED → FR-AUTHV-014 |
| GAP-005 | Tokens | Refresh-token rotation — `refresh_token()` re-uses the same `sub`/`roles` without invalidating the prior token | SHIPPED → FR-AUTHV-013 |
| GAP-006 | Tokens | Token revocation list — no mechanism to revoke a non-expired JWT before its `exp` | SHIPPED → FR-AUTHV-012 |
| GAP-007 | Bearer | Asymmetric (RS256/ES256) signing key support — current implementation is HMAC-only | SHIPPED → FR-AUTHV-017 |
| GAP-008 | PKCE | State binding to server session — `OAuthState` is generated but the server-side session association is not enforced at the middleware layer | SHIPPED → FR-AUTHV-018 |
| GAP-009 | General | Rate-limiting on failed auth attempts — no brute-force protection for verifier/state/bearer endpoints | PLANNED |
| GAP-010 | General | Tracera / AgilePlus middleware adapter — wiring of these requirements into Axum tower layers for consumer repos not yet documented | SHIPPED → docs/integration/middleware-adapter.md |
