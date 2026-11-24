# Known Issues

- `pre-commit` may skip the Rust hooks unless a matching Rust or Cargo file is part of the changed set; `pre-commit run --all-files` or the manual stage should be used for full verification.
- `gitleaks` and `trufflehog` are intentionally configured as manual hooks because whole-repo secret scans are expensive for normal commit flow.
