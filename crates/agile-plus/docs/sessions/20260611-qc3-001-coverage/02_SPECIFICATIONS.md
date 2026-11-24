# Specifications

- Replace `cargo-tarpaulin` with `cargo-llvm-cov` in the main CI workflow.
- Upload an LCOV artifact to Codecov from the Rust coverage job.
- Use repo-safe GitHub Actions permissions for Codecov upload.
- Add a README badge pointing to the repository Codecov page.
- Document one local coverage command for contributors.

## ARUs

- Assumption: `codecov/codecov-action@v6` with OIDC is acceptable for this public repository.
- Risk: `cargo llvm-cov` compile time may differ from tarpaulin; validation will focus on syntax and local test pass, not a full CI run.
- Uncertainty: actual Codecov badge rendering cannot be confirmed without a remote run, so the badge URL is set to the standard GitHub repo form.

