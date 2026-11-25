# focus-crypto

Token wrapping, secure secret storage abstraction, and integrity digests. Provides OS keychain integration (Apple Keychain on iOS/macOS, Linux Secret Service on Android/Linux) and in-memory fallbacks for testing.

## Purpose

Centralizes secrets management (tokens, API keys, passphrases) behind a platform-agnostic trait. Integrates with native secure storage (Keychain, Secret Service); provides in-memory and null implementations for tests. Includes HMAC-SHA256 integrity digests for data validation.

## Key Types

- `SecureSecretStore` — trait: `get()`, `set()`, `delete()` for secret strings
- `AppleKeychainStore` — uses native iOS/macOS Keychain
- `LinuxSecretServiceStore` — uses Linux Secret Service (DBus)
- `InMemorySecretStore` / `NullSecureStore` — for testing
- `TokenWrap` — wraps token with metadata (issued_at, expires_at, refresh_token)
- `IntegrityDigest` — SHA-256 digest for data validation

## Entry Points

- `default_secure_store()` — returns platform-appropriate store
- `SecureSecretStore::set()` — persist token to keychain
- `SecureSecretStore::get()` — retrieve with plaintext in-memory
- `TokenWrap::verify_integrity()` — check HMAC digest

## Functional Requirements

- Platform-agnostic secrets management
- No plaintext tokens on disk except during active use
- Integrity validation for cryptographic operations

## Consumers

- All connectors (token storage)
- `focus-backup` (encryption keys)
- Native app credential flows (iOS, Android)
