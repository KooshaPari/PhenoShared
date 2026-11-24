# Specifications

- Add Just targets:
  - `test`: aggregate target for supported workspace-wide test execution.
  - `test-unit`: Rust workspace tests.
  - `test-integration`: dedicated integration suite.
- Preserve existing repo behavior where possible:
  - keep current workspace unit command unchanged;
  - keep integration invocation aligned with the integration crate's documented feature/ignored-test behavior.
- Ensure the integration crate is part of the root Cargo workspace so the new Just target is executable from the repo root.

# ARUs

- Assumption: `test` is intended to be the high-level full runner, not just the unit tier.
- Risk: full integration tests may depend on local tooling such as `process-compose`.
- Uncertainty: the requested worklog path was not further constrained, so it will be written at repo root beside the existing examples.
