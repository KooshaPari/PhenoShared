# Implementation Strategy

- Replace the existing multi-language baseline instead of extending it, because QC1-001 requests a narrower hook set and the repo instructions explicitly prefer full replacements over backward-compatibility shims.
- Reuse the Rust command lines already documented in `Justfile` and `CONTRIBUTING.md`.
- Restrict `shellcheck` to known shell scripts already present in the repo.
