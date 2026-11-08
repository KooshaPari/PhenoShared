# Security Policy

## Reporting a Vulnerability

Use one of the following channels:

1. Preferred: GitHub Security Advisories for this repository.
2. Fallback: open a private issue in the owning organization and tag `@<REDACTED>`.

Do not disclose exploit details publicly before triage.

## Response Expectations

- Initial acknowledgment target: 2 business days.
- Triage target: 5 business days.
- Remediation timeline: severity-based and communicated in advisory thread.

## Supported Versions

This repository follows latest-main support for template contracts.

| Version | Supported |
| --- | --- |
| latest `main` | Yes |
| older commits/tags | No |

## Repository Security Rules

1. No secrets in repository history.
2. Reconcile and manifest contracts must fail loudly on invalid state.
3. Release only from green CI checks.
4. Contract changes must include manifest version updates.
