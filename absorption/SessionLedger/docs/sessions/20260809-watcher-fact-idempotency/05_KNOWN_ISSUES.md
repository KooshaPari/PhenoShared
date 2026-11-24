# Known issues

OS filesystem event timing is intentionally not used in the test; the deterministic repeated ETL input reproduces its downstream effect.

The current checkout's repository-wide `cargo fmt --check` reports pre-existing formatting drift in unrelated daemon resolver, HTTP, main, and lib files. The changed Rust files pass an isolated `rustfmt --check`. `cargo clippy` is blocked before linting by the existing `clippy.toml` fields `warn` and `allow`, which this installed Clippy rejects.
