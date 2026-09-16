# Specifications

- `build` must delegate to the package build script.
- `test` must delegate to the package test script.
- `lint` must delegate to the package lint script.
- `clean` must remove generated build and documentation output.

Acceptance criteria:

- The task file contains only the four requested common tasks.
- Each task is aligned with the detected Bun/TypeScript repo tooling.

