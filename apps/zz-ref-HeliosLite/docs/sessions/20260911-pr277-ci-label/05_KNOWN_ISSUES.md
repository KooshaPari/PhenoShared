# Known issues

No remaining scoped blockers. All crate gates pass. Cargo emits existing workspace.dev-dependencies and duplicate binary target manifest warnings; clippy with -D warnings passes.

Initial cold-compilation test attempt timed out at 600 seconds on a loaded host; final full suite passes. Synthetic Bash tests are Unix-only and do not replace hosted GitHub Actions validation. Portable snapshot, guard structure and policy assertions remain available on every host. actionlint passes.

Recursive child review is disabled for this child swarm. Parent coordinator reviewed portability and retains integration ownership. No LSP, lint.yml/test.yml, conversation changes, commits, pushes or hosted executions were made by this worker.
