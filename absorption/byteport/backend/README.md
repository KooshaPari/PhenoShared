# `backend/`

The BytePort backend lives in [`backend/byteport/`](./byteport/) (Go module
`byteport`). It is the canonical backend built by `Dockerfile` and reached
by the desktop app and the Tauri shell.

Previous incarnations of this directory (the `github.com/byteport/api` module
and the `bytebridge` Fermyon experiment) were retired in 2026-09-20; see
[`docs/operations/two-backends.md`](../docs/operations/two-backends.md) for
the historical analysis that motivated the consolidation.
