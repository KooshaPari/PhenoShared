# Governance

## Project Leadership

BytePort is maintained by the KooshaPari organization. Product direction,
architecture decisions, and release governance are human-directed. Implementation
may be agent-assisted.

## Decision Process

### Architecture Decisions

Major architectural decisions are recorded as ADRs in `docs/adr/`. Each ADR
follows the format:

```
docs/adr/ADR-NNN-short-title.md
```

ADRs are:
- Proposed by any contributor
- Reviewed by maintainers
- Accepted/Rejected by project lead
- Never modified after acceptance (superseded by new ADRs)

### Release Process

1. Changes merge to `main` via PR with passing CI
2. Release branch created for major versions
3. Version bumped per Semantic Versioning
4. CHANGELOG.md updated
5. GitHub release created with artifacts
6. Docker image published

### Versioning

- **Major (X.0.0):** Breaking API changes
- **Minor (0.X.0):** New features, backward compatible
- **Patch (0.0.X):** Bug fixes, backward compatible

## Contribution Guidelines

See [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Development setup
- Code style requirements
- PR process
- Testing requirements

## Code of Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Security

See [SECURITY.md](SECURITY.md) for vulnerability reporting and security policy.

## License

BytePort is licensed under the terms in [LICENSE](LICENSE).
