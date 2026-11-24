# Known Issues

- The workflow depends on repository secrets:
  - CARGO_REGISTRY_TOKEN must be configured before publish can succeed.
- Additional crates may still need richer crates.io metadata later if maintainers want to narrow or expand the publish set.
