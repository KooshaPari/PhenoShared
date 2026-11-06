# Security Policy

## Reporting a Vulnerability

Do not open public issues for security vulnerabilities. Report them privately
via [GitHub Security Advisories](https://github.com/KooshaPari/PhenoVCS/security/advisories/new)
or by emailing the maintainers at [kooshapari@gmail.com](mailto:kooshapari@gmail.com).

Please include:

- A description of the vulnerability.
- Steps to reproduce (proof of concept).
- Potential impact.
- Any suggested fixes or mitigations.

We will acknowledge reports within 48 hours and provide a remediation timeline.

## Supported Versions

This repository tracks `main`. Security fixes are applied to `main` and rolled
into the next tagged release.

## Automated Scanning

This repository is covered by:

- Semgrep + CodeQL SAST (via GitHub Actions).
- `trufflehog` secret scanning on pre-commit and CI.
- Snyk dependency scanning.
