# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.x     | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of **HexaType** seriously. If you discover a security vulnerability, please do NOT open a public issue. Instead, report it privately.

### What to include

- A detailed description of the vulnerability
- Steps to reproduce (proof of concept)
- Potential impact
- Any suggested fixes or mitigations

We will acknowledge your report within 48 hours.

## Security Considerations

When using HexaType in your projects:

- **Domain Layer**: Keep domain logic pure with no side effects
- **Input Validation**: Validate all data at adapter boundaries
- **Secrets**: Use environment variables for sensitive configuration
- **Dependencies**: Keep npm dependencies updated

## Dependency Scanning

HexaType regularly scans dependencies for vulnerabilities:

- `npm audit` in CI/CD
- Dependabot for automated updates
- Snyk integration (if configured)

---

Thank you for helping keep the community secure!
