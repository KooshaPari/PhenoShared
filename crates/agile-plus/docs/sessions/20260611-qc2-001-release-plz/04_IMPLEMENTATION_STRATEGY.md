# Implementation Strategy

- Keep the automation isolated in .github/workflows/release-plz.yml.
- Use release-plz.toml for package-level release controls instead of scattering workflow exclusions.
- Avoid publishing root, test, benchmark, and xtask packages to prevent invalid crates.io releases.
