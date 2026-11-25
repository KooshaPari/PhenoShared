# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.x     | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of **HexaGo** seriously. If you discover a security vulnerability, please do NOT open a public issue. Instead, report it privately.

### What to include

- A detailed description of the vulnerability
- Steps to reproduce (proof of concept)
- Potential impact
- Any suggested fixes or mitigations

We will acknowledge your report within 48 hours.

## Security Considerations

When using HexaGo in your projects:

- **Domain Layer**: Keep domain logic free of external dependencies
- **Port Interfaces**: Validate all input at adapter boundaries
- **Secrets**: Use environment variables for sensitive configuration
- **Logging**: Avoid logging sensitive data

## Dependency Scanning

HexaGo uses Go's native vulnerability scanning:

- `go vuln` for dependency vulnerabilities
- Dependabot for automated updates
- CI/CD security scanning

---

Thank you for helping keep the community secure!
