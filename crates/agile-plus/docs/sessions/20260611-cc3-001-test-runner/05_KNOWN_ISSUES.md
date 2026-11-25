# Known Issues

- `test-integration` can still fail in environments missing the external services and tooling expected by `agileplus-integration-tests`.
- The repo also has a `Taskfile.yml`; this task does not attempt to mirror the Just target split there because the request was explicitly scoped to the Just runner.
