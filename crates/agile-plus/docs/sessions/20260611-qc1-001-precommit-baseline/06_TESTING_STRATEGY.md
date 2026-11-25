# Testing Strategy

- Validate the YAML structure with `pre-commit validate-config`.
- Inspect the rendered hook list with `pre-commit run --all-files --hook-stage manual` only if the environment already has the required binaries available.
- Record command outcomes in the worklog.
