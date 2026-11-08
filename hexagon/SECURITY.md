# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please report it responsibly.

### How to Report

**Please do not open public issues for security vulnerabilities.**

Instead:

1. Email: security@<REDACTED>.com
2. Subject: `[SECURITY] Hexagon - Brief description`
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if known)
   - Your contact information

### Response Timeline

| Timeframe | Action |
|-----------|--------|
| 24 hours | Acknowledgment of receipt |
| 72 hours | Initial assessment |
| 7 days | Fix or mitigation plan |
| 30 days | Resolution or public disclosure |

### What to Expect

- Prompt acknowledgment of your report
- Regular updates on our progress
- Credit for the discovery (if desired)
- Safe harbor for good faith research

## Security Best Practices

### For Template Users

1. **Dependency Management**:
   - Regularly update dependencies
   - Use `go mod`, `cargo audit`, etc.
   - Review security advisories

2. **Secrets Management**:
   - Never commit secrets to templates
   - Use environment variables
   - Employ secret management services

3. **Input Validation**:
   - Validate all inputs at boundaries
   - Use domain validation
   - Sanitize external data

4. **Error Handling**:
   - Don't expose sensitive information in errors
   - Log security events
   - Use structured error handling

### For Template Contributors

1. **No Hardcoded Secrets**:
   - No API keys in templates
   - No default passwords
   - No certificate files

2. **Secure Defaults**:
   - Enable security features by default
   - Disable dangerous features
   - Document security considerations

3. **Supply Chain**:
   - Minimal dependencies
   - Vetted dependencies only
   - SBOM generation

4. **Generated Code**:
   - Security-focused patterns
   - OWASP Top 10 awareness
   - Input validation examples

## Template Security Features

Hexagon templates include:

1. **Input Validation**:
   - Domain-level validation
   - Type safety
   - Boundary checking

2. **Error Handling**:
   - Structured errors
   - No sensitive data leakage
   - Proper logging

3. **Test Coverage**:
   - Security test examples
   - Validation testing
   - Edge case coverage

## Security Checklist

When using Hexagon templates:

- [ ] Change default configurations
- [ ] Review dependency versions
- [ ] Enable security headers (web templates)
- [ ] Configure authentication
- [ ] Set up logging and monitoring
- [ ] Run security scanners
- [ ] Keep dependencies updated

## Vulnerability Disclosure

We follow coordinated disclosure:

1. Reporter submits vulnerability
2. We investigate and develop fix
3. Fix is tested and deployed
4. Public disclosure with credit

## Security Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE/SANS Top 25](https://cwe.mitre.org/top25/)
- [SLSA Framework](https://slsa.dev/)

## Acknowledgments

We thank security researchers who responsibly disclose vulnerabilities.

## Traceability

/// @trace HEXAGON-SECURITY-001
/// @trace HEXAGON-SPEC-001
