# Block-C Audit — authvault

**Repo:** `KooshaPari/authvault`
**Audit date:** 2026-06-16
**Auditor:** Forge (Block-C, docs PR)
**SSOT:** `phenotype-registry/docs/rationalization/block-c-consolidation.md`

---

## 1. Purpose

Authentication and authorization framework for the Phenotype substrate.
Exposes a hexagonal (ports/adapters) Rust library covering JWT issuance and
validation, refresh-token rotation, session management, RBAC/ABAC policy
evaluation, audit logging, password hashing (Argon2 / Bcrypt), and a
side-car encrypted "secret vault" (ChaCha20-Poly1305 AEAD with an in-process
KMS adapter). A `serve` example wires a minimal axum app so the library can
run as a standalone service. Public-API target: `authvault = "0.1"` on
crates.io (`Cargo.toml:8`).

## 2. Stack

| Layer        | Choice                                          |
|--------------|-------------------------------------------------|
| Language     | Rust 2021, MSRV 1.75 (`Cargo.toml:12`)          |
| Web          | `axum` 0.8 (`Cargo.toml:29`)                    |
| Auth crypto  | `jsonwebtoken` 9 (`use_pem`), `argon2` 0.5, `bcrypt` 0.15 |
| AEAD         | `chacha20poly1305` 0.10, `sha2` 0.11, `zeroize` 1.8 |
| Async        | `tokio` 1 (full), `async-trait` 0.1             |
| Errors       | `thiserror` 2, `anyhow` 1                       |
| Serde/time   | `serde` 1 (derive), `serde_json` 1, `chrono` 0.4 (serde) |
| Misc infra   | `uuid` 1, `http` 1, `tower` 0.5, `tracing` 0.1, `tracing-subscriber` 0.3 |
| Stated but **unused** in code | `tokio-postgres` 0.7, `redis` 1.2, `regex` 1 |
| Dev / bench  | `rcgen` 0.14, `criterion` 0.6, `tempfile` 3     |
| Quality      | `clippy -- -D warnings`, `cargo fmt`, `cargo doc` (per `AGENTS.md:81-83`) |
| Profiles     | `release.lto = true` (`Cargo.toml:46-47`)       |

## 3. Maturity

| Indicator                | Reading                                                |
|--------------------------|--------------------------------------------------------|
| Version                  | `0.1.0` (`Cargo.toml:2`), pre-1.0                      |
| FR catalog               | 10 FRs (`FRs/FR-AUTH-001..010.md`); 5 ✅, 5 🔎 PLANNED (`SPEC.md:13-23`) |
| Doc footprint            | README, CLAUDE.md, AGENTS.md, ADR.md, PLAN.md, CHANGELOG.md, SPEC.md, plus SECURITY_AUDIT.md / SESSION_MANAGEMENT_AUDIT.md / TOKEN_STORAGE_AUDIT.md / TEST_COVERAGE_MATRIX.md — high docs-to-code ratio |
| Tests                    | `tests/unit_tests.rs` 21 kB, `tests/integration_tests.rs` 26 kB, in-module tests in `adapters/kms.rs:94-173` |
| Benchmarks               | 3 declared (`[[bench]]` x3, `Cargo.toml:49-59`); `benches/perf.rs` is 261 B stub |
| Examples                 | 1 (`examples/serve.rs` — 21 lines, exposes only `/health`) |
| Fuzz                     | `fuzz/` with target dir; no `fuzz/Cargo.toml` lockfile inspected, target likely placeholder |
| Public API               | Re-exports 20+ items in `src/lib.rs:28-40`; pre-1.0 churn acceptable |
| Open scope in SPEC       | MFA, passwordless, federation, API keys, rate limiting, OAuth2 provider, multi-tenant — **not implemented** |
| Honest self-statement    | README banner "AI-Agent-Only / Slop Expected" + "70% ACTIVE"; SPEC marks the truth (`SPEC.md:13-23`) |

**Verdict:** mid-maturity library. Core JWT + refresh + revocation + audit
+ session + policy paths have unit/integration coverage. The vault/KMS
sub-system, policy engine, and PKCE flow are present but not yet exercised
by a real adapter, transport, or storage. Roughly half of the README
feature checklist is unimplemented; SPEC is the trustworthy index.

## 4. Over-engineering findings — "ponytail lens"

Lens order: **delete → stdlib → native → yagni → shrink.** One line each.

1. **delete `src/domain/vault.rs` (814 lines) + `src/adapters/vault_store.rs` (351) + `src/adapters/kms.rs` (174) + `LocalKmsAdapter` and the `KeyManagementService` port** — a ChaCha20-Poly1305 secret vault is a separate product bolted onto an auth lib; it has zero callers in the library, no KMS, no file adapter wired to any real config, and the README never advertises it.
2. **delete `bcrypt` dep + `Argon2Hasher`/`BcryptHasher` dual-hasher seam in `src/adapters/hashers.rs`** — `argon2` is the de-facto winner; the `PasswordHasher` trait has a single real impl argument.
3. **delete `regex` dep** — `cargo tree`-searched against `regex::` shows no use in `src/`; dead weight on the build graph.
4. **delete `tokio-postgres` and `redis` deps** — only `InMemory*Store` adapters ship; no DB or cache adapter exists in `src/adapters/`.
5. **delete `examples/serve.rs` `tracing_subscriber::fmt::init()` + axum wiring** — exposes only `/health`, never the auth API; pure demo tax.
6. **delete `fuzz/` directory** — no working `fuzz/Cargo.toml` corpus, no harness in CI, orphaned directory from "AI-DD slop" setup.
7. **stdlib-ize `src/infrastructure/error.rs` (29 lines, `AuthKitError`)** — hand-rolled `Display`+`Error` for a 4-variant Config/Init/Runtime/Security shell that is never constructed anywhere; remove the file entirely.
8. **stdlib-ize the hand-rolled `impl serde::Serialize for AuthError` in `src/domain/errors.rs:79-86`** — `thiserror` already gives you a `Display`; or use `#[derive(Serialize)]` and the tag-less string form with one attribute; ~8 lines drop.
9. **stdlib-ize `src/middleware/pkce_state_session.rs` (184 lines)** — the PKCE `OAuthState` map is reinventing `std::collections::HashMap<CodeVerifier, CodeChallenge>`; the wrapper adds no behavior.
10. **stdlib-ize `src/domain/identity.rs:1-30` `User`/`Role` builders** — chainable `with_*` setters with no validation; `#[derive(Default)]` + public fields or a real `User::new` ctor is half the size.
11. **native — prefer `std::sync::RwLock` over `tokio::sync::Mutex` for the in-memory stores** — `adapters/storage.rs`, `adapters/refresh_token.rs`, `adapters/revocation.rs`, `domain/session_store.rs`, `adapters/vault_store.rs` all use `Mutex<HashMap<…>>`; the critical sections are sync lookups, not `.await`-bound; `std::sync::RwLock` removes tokio-task coupling.
12. **native — `chacha20poly1305::aead::OsRng` → `getrandom::getrandom` or `rand::rngs::OsRng` (already a dep)** — `Cargo.toml:27` brings `rand`; `vault.rs:11` and `kms.rs:25` re-import `OsRng` from `aead`, a third RNG path.
13. **native — drop `async-trait` (`Cargo.toml:16`) once `UserStorage`/`SessionStorage`/`PasswordHasher` etc. are made `dyn`-safe natively** — Rust 1.75 (the MSRV) supports native `async fn in trait`; the `#[async_trait]` macro on every port in `src/domain/ports.rs` is unneeded boilerplate.
14. **yagni — collapse `RefreshTokenStore` (port) + `InMemoryRefreshTokenStore` (impl) and `RevocationStore` + `InMemoryRevocationStore` into a single `TokenState` trait** — they are both "set membership of opaque IDs" with `add` / `contains` / `remove`; the split is one-trait-per-verb inflation.
15. **yagni — `AuthMethod` enum (`src/domain/auth.rs:50-59`) with 5 variants including `OAuth2` and `ApiKey`** — the library has no OAuth2 client or API-key validator in `src/`; remove the variants and re-add when the FR lands.
16. **yagni — `AuditAction` enum (`src/domain/ports.rs:16-32`) including `VaultRead` / `VaultWrite`** — these are dead variants while the vault itself is dead code; drop the two vault-flavored variants.
17. **yagni — `AuditOutcome::{Success,Failure}`** — `bool` would do; the wrapper exists to make the audit sink feel "domain-y."
18. **yagni — `SecretVaultBuilder`/`SecretVault` split in `src/domain/vault.rs`** — builder pattern for a struct with two fields and no required config; collapse to `SecretVault::new(key, store)`.
19. **yagni — `BcryptHasher` (deprecation-grade alternative hasher)** — see #2; one canonical path means one less seam.
20. **yagni — `AuthKitError` re-exported in `src/lib.rs:39`** — never used, see #7.
21. **yagni — `fuzz/fuzz_targets/`** — see #6; if no harness is run in CI it is not part of the project.
22. **shrink — `src/domain/auth.rs` (1184 lines)** — split into `claims.rs` (Claims, RefreshClaims, TokenPair) + `authenticator.rs` (Authenticator) + `rotation.rs` (refresh family logic); 1184 in one file is the dominant size offender.
23. **shrink — `src/domain/policy.rs` (408 lines)** — the `Condition`/`Policy` DSL is custom; 80% of the engine is a 5-variant `Condition` evaluator that `serde_json::Value::as_str/as_i64/...` would do at a third the size.
24. **shrink — `src/middleware/adapter.rs` (312 lines) of axum glue** — only used by the dropped `serve` example; if axum integration is real, keep; if it's a demo, drop the file.
25. **shrink — `Cargo.toml:46-47` `[profile.release] lto = true`** — the lib is not size-constrained; `codegen-units = 1` + default LTO already covers what an auth lib needs; drop the line.

**net: -1,900 lines possible** (~33% of the 5,830 LoC library, plus dead deps `regex`, `tokio-postgres`, `redis`, `bcrypt` once #1/#2/#3/#4 land).

## 5. Cross-repo Block-C notes

Per `phenotype-registry/docs/rationalization/block-c-consolidation.md`, the
audit doc must record the per-repo interactions for siblings. authvault is
the **merge target** of consolidation #2 (Auth dedup) and is otherwise
orthogonal to the other two consolidations. For completeness:

- **phenotype-voxel / phenotype-terrain / phenotype-water → GFX-SDK merge (#1).**
  No code coupling to authvault. The audit PRs for those repos must not
  import authvault crates; the SDK workspace's `Cargo.toml` will not list
  `authvault` as a dep. Action: ensure the GFX-SDK workspace root
  `Cargo.toml` (to be authored in the merge PR) does not pull authvault
  transitively. If any of the three GFX source repos currently has a
  `Cargo.toml` entry pointing at `KooshaPari/authvault`, that dep line
  must be deleted in the per-repo GFX audit PR.
- **phenoShared → generic-lib rescope (#3).** phenoShared (whatever its
  current form) must not be a dependency of authvault, and vice versa.
  Action: when the rescope lands, verify `authvault/Cargo.toml` has no
  `[patch.crates-io]` or path-dep pointing at phenoShared; if it does,
  inline the one or two small utilities it actually used and drop the
  dep. (No such dep is present in the current `Cargo.toml`, so the
  rescope is a no-op on this side — confirmed.)
- **authvault itself → auth-dedup target (#2).** authvault is the
  destination for any duplicate auth repos in Block-C. The merge PR
  flow: (a) each duplicate repo first issues a per-repo Block-C audit
  PR pointing back at this file; (b) the duplicate's auth code lands
  here via a single consolidation PR that preserves the `authvault = 0.1`
  semver; (c) the duplicates archive. The current
  `Cargo.toml:1-12` name and version stay stable through the merge to
  avoid breaking the per-FR evidence trail in `SPEC.md`.

## 6. Consolidation verdict

**Keep and consolidate into.** authvault is the canonical home for
authentication, authorization, and session primitives in the Phenotype
stack. The hexagonal structure (domain/application/adapters) is sound, the
FR catalog in `SPEC.md` is honestly marked, and the implemented surface
(JWT, refresh, revocation, audit, session, policy, PKCE) is cohesive.

Two carve-outs to record against the SSOT:

1. **The vault/KMS sub-system is a future product, not an auth concern.**
   `src/domain/vault.rs`, `src/adapters/vault_store.rs`, `src/adapters/kms.rs`,
   the `KeyManagementService` port, and the `Vault*` re-exports in
   `src/lib.rs:37` should be **lifted into a new repo** (working name
   `phenotype-secretvault`) before the auth-dedup merge. They drag in
   `chacha20poly1305`, `zeroize`, the `KmsError` enum, and the entire
   `AuditAction::VaultRead/Write` variant set, none of which authvault
   itself needs. The lift is the single highest-leverage change in this
   audit (~1,340 LoC and 2 deps out of authvault, into a properly
   scoped crate).
2. **The hexagonal skeleton is correct, but the application layer is
   one file (`src/application/services.rs`, 159 lines).** Once the
   vault is lifted and the dead hasher/adapter branches are pruned,
   `application/services.rs` becomes the natural seam to absorb the
   duplicate auth code from consolidation #2 — that is the file the
   per-repo merge PRs should target.

**Linked from SSOT:** `phenotype-registry#75`.
