# Specifications

- Add a GitHub Actions workflow that:
  - creates or updates a release PR from main,
  - publishes crates after the release PR is merged,
  - uses GITHUB_TOKEN and CARGO_REGISTRY_TOKEN.
- Add repository-level release-plz config to exclude non-publishable packages.
- Update contributor documentation to reflect the new flow.
