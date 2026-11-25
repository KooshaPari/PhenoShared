# Implementation Strategy

- Use a minimal change set centered on `Justfile`.
- Keep command semantics explicit instead of hiding shell logic inside helper scripts.
- Update docs only where they describe the same testing surface to avoid broad unrelated churn.
- If validation exposes a Cargo workspace mismatch, fix the workspace membership rather than baking a brittle workaround into the Just target.
