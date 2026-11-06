# Release traceability matrix

Coverage definition: a requirement is covered only when it has an executable gate or test named
below. The release gate requires every requirement in `docs/specs/SPEC.md` to have a `VERIFIED`
row. Generated measurement: `artifacts/quality/traceability.json`.

| Requirement | Acceptance evidence | Implementation evidence | Status |
|---|---|---|---|
| FR-1 | `src/__tests__/acceptance.test.ts` | `src/client.ts` | VERIFIED |
| FR-2 | `src/__tests__/acceptance.test.ts` | `src/client.ts` | VERIFIED |
| FR-3 | `src/__tests__/acceptance.test.ts` | `src/interceptor.ts` | VERIFIED |
| FR-4 | `src/__tests__/acceptance.test.ts` | `src/interceptor.ts` | VERIFIED |
| FR-5 | `src/__tests__/acceptance.test.ts` | `src/client.ts` | VERIFIED |
| FR-6 | `src/__tests__/acceptance.test.ts` | `src/retry.ts`, `src/client.ts` | VERIFIED |
| FR-7 | `src/__tests__/acceptance.test.ts` | `src/mock.ts` | VERIFIED |
| FR-8 | `crates/httpora-core/tests/requirements_test.rs` | `crates/httpora-core/src/middleware/rate_limit.rs` | VERIFIED |
| FR-9 | `crates/httpora-core/tests/requirements_test.rs` | `crates/httpora-core/src/middleware/rate_limit.rs` | VERIFIED |
| FR-10 | `crates/httpora-core/tests/requirements_test.rs` | `crates/httpora-core/src/middleware/circuit_breaker.rs` | VERIFIED |
| FR-11 | `crates/httpora-core/tests/requirements_test.rs` | `crates/httpora-core/src/middleware/retry.rs` | VERIFIED |
| FR-12 | `crates/httpora-core/tests/requirements_test.rs` | `crates/httpora-core/src/middleware/retry.rs` | VERIFIED |
| FR-13 | `crates/httpora-core/tests/requirements_test.rs` | `crates/httpora-core/src/middleware/cors.rs` | VERIFIED |
| FR-14 | `crates/httpora-core/tests/requirements_test.rs` | `crates/httpora-core/src/builder.rs` | VERIFIED |
| FR-15 | `crates/httpora-core/tests/requirements_test.rs` | `crates/httpora-core/src/builder.rs` | VERIFIED |
| FR-16 | `crates/httpora-core/tests/requirements_test.rs` | `crates/httpora-core/src/error.rs` | VERIFIED |
| NFR-1 | `npm run typecheck` | `tsconfig.json` | VERIFIED |
| NFR-2 | `crates/httpora-core/tests/requirements_test.rs` | `rate_limit.rs`, `circuit_breaker.rs` | VERIFIED |
| NFR-3 | `crates/httpora-core/tests/requirements_test.rs` | `crates/httpora-core/src/middleware/clock.rs` | VERIFIED |
| NFR-4 | `crates/httpora-core/tests/requirements_test.rs` | Rust configuration types | VERIFIED |
| NFR-5 | `cargo test --no-default-features` and `cargo test --all-features` | `crates/httpora-core/Cargo.toml` | VERIFIED |
| NFR-6 | `crates/httpora-core/tests/requirements_test.rs` | `crates/httpora-core/src/error.rs` | VERIFIED |
| NFR-7 | `cargo clippy --all-targets --all-features -- -D warnings` | `crates/httpora-core/src/lib.rs` (`forbid(unsafe_code)`) | VERIFIED |
| NFR-8 | `cargo test --no-default-features` | feature-gated imports in `crates/httpora-core/src/middleware/retry.rs` | VERIFIED |

Functional journey coverage is `16/16 = 100%`: each FR has executable acceptance evidence.
Overall requirement traceability is `24/24 = 100%`. These calculations are re-derived by
`npm run traceability`; a matrix row alone does not replace the named test or gate.
