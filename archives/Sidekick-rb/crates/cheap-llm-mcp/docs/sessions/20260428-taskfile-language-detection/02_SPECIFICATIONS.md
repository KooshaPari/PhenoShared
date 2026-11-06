# Specifications

Deliver a `Taskfile.yml` with these tasks:
- `build`
- `test`
- `lint`
- `clean`

Behavior:
- Detect the repo language from manifests in the project root.
- Use the language-specific command set for each task.
- Fail fast when no supported language can be detected.
