# Testing Strategy

- Validate the Taskfile by invoking the Task runner itself in the cloned repo.
- Confirm `task build`, `task test`, `task lint`, and `task clean` resolve without syntax issues.
- Use the repo's existing Node toolchain for build/test commands and transient `npx` tooling for lint.
- Validate `task lint` against the whole repository tree so Markdown and config drift are
  caught consistently, not just the top-level documentation files.
- Current validation ran `task build`, `task test`, `task lint`, and `task clean`.
