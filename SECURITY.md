# Security Policy

## Supported Versions

The following versions of this project receive security updates:

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |
| < latest| :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability, please follow these steps:

### 1. Do NOT Create a Public Issue

Security vulnerabilities should **never** be reported via public GitHub issues.

### 2. Report Privately

Email security concerns to: **security@<REDACTED>.com**

Include the following information:
- Description of the vulnerability
- Steps to reproduce (if applicable)
- Potential impact
- Suggested fix (if known)

### 3. Response Timeline

| Action | Timeline |
|--------|----------|
| Acknowledgment | Within 48 hours |
| Initial assessment | Within 7 days |
| Fix development | Depends on severity |
| Disclosure | After fix is released |

### 4. Disclosure Policy

We follow responsible disclosure:
1. Fix is developed and tested
2. Fix is released in a new version
3. Security advisory is published
4. Reporter is credited (if desired)

## Security Best Practices for Users

### Dependencies

Keep dependencies up to date:

```bash
# Rust (Cargo)
cargo audit

# Python (pip)
pip-audit

# Node.js (npm)
npm audit
```

### Secret Management

- Never commit secrets to version control
- Use environment variables or secret management tools
- Rotate credentials regularly

### Input Validation

- Validate all user inputs
- Use parameterized queries (prevent injection attacks)
- Implement rate limiting

## Security Tools Used

| Tool | Purpose |
|------|---------|
| cargo-audit | Rust dependency vulnerability scanning |
| pip-audit | Python dependency vulnerability scanning |
| npm audit | Node.js dependency vulnerability scanning |
| CodeQL | Static analysis security testing |
| Dependabot | Automated dependency updates |

## Security-Related Configuration

### Rust Projects

Add to `deny.toml`:

```toml
[advisories]
version = 2
db-path = ".cargo/advisory-db"
db-urls = ["https://github.com/rustsec/advisory-db"]
yanked = "deny"

[bans]
multiple-versions = "warn"
wildcards = "warn"
```

### Python Projects

Add to CI:

```yaml
- name: Run security audit
  run: pip-audit --desc --format=json
```

### Node.js Projects

Add to CI:

```yaml
- name: Run security audit
  run: npm audit --audit-level=moderate
```

## License

Security policies and procedures are provided under the same license as the project.
