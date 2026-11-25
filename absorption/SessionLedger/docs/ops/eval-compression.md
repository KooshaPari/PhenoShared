# Compression Evaluation Gate

This gate records shallow evidence that SessionLedger's zstd adapter reduces
representative OKF sessions (including compression/token-oriented conformance
fixtures) while preserving byte-for-byte round trips and a coarse token-burn
proxy.

## Method

Run the feature-gated integration test:

```sh
cargo test -p session-ledger --features compress --test compression_eval --locked
```

The test loads a small CI set of OKF fixtures (baseline `auth-fix` plus
token-budget / compress-resume / compress-token-proxy / token-slice-budget /
archive-gzip-resume family fixtures), compresses each with `ZstdCompressor` at
level 3, decompresses it, and asserts that the decoded text exactly matches the
fixture. It then computes:

```text
ratio_bps = compressed_bytes * 10_000 / source_bytes
bytes_saved = source_bytes - compressed_bytes
rough_tokens_saved ~= bytes_saved / 4
```

Basis points keep the assertion integer-only and stable in CI. The rough token
proxy is cross-checked against `CharCountTokenEstimator` scoring the source as
non-empty.

## Threshold

The current gate requires `ratio_bps <= 6_500`, meaning the compressed payload
must be at most 65% of the source fixture size. This is intentionally loose
enough for fixture evolution, but tight enough to catch accidental passthrough
compression, feature miswiring, or a compressor-level regression.

If a fixture changes materially, update the threshold only with a fresh local
run and include the observed compressed/source byte counts in the PR.

## Token-Burn Proxy

SessionLedger burns tokens when continuation context is injected back into an
agent. Byte savings are not a tokenizer-accurate measurement, but for JSON-like
OKF payloads they are a useful rough proxy:

```text
bytes_saved = source_bytes - compressed_bytes
rough_tokens_saved ~= bytes_saved / 4
```

The gate therefore protects a simple operational claim: smaller serialized
continuation payloads usually imply less context transferred, stored, and
eventually rehydrated into prompt material. The CI assertion is about byte
ratio plus a positive token-burn proxy; the token estimate remains a coarse
planning signal rather than a billing metric.

## Per-Fixture Token Ledger

Harbor per-eval token-burn ledgers stay **N/A** (see
[`EVAL_SCOPE.md`](../EVAL_SCOPE.md)). SessionLedger instead pins a shallow
**per-fixture planning ledger** on the compression/token OKF family: intent
`token_estimate` fields must sum to the gate `total_token_estimate` recorded in
each fixture and in [`token-burn.json`](token-burn.json).

Hermetic smoke (no daemon):

```powershell
pwsh ./scripts/token-burn-check.ps1 -SelfCheck
```

Operator contract: [`token-burn.md`](token-burn.md). The Rust companion test
`compress_token_fixtures_per_eval_token_ledger_matches_gate` in
`tests/compression_eval.rs` re-checks the same sums inside the `compress`
feature gate.
