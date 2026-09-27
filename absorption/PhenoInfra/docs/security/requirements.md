# Security Requirements

Security requirements for the PhenoDocs documentation hub, a VitePress static site.

## Assets

| Asset | Sensitivity | Description |
|-------|-------------|-------------|
| Published site content | Public | VitePress-generated static HTML/CSS/JS deployed to GitHub Pages |
| Source markdown | Public | Documentation source in this repository |
| Build pipeline | Internal | GitHub Actions workflows that build and deploy the site |
| Repository secrets | Secret | GitHub Actions secrets (deploy tokens, if any) |
| VitePress config | Public | Configuration including navigation, sidebar, theme settings |

## Threat Model Boundary

PhenoDocs is a **static documentation hub**. It does not:
- Accept user input or serve dynamic content
- Store PII, credentials, secrets, or sensitive data in its content
- Run server-side application code in production
- Maintain user sessions or authentication

The primary security concern is **supply-chain integrity** of build dependencies and **correctness of CI/CD pipelines**.

## Requirements by Domain

### CI/CD Pipeline Security
1. All GitHub Actions workflows MUST pin runner versions to `ubuntu-24.04` (not `ubuntu-latest`)
2. All third-party actions MUST be pinned by commit SHA, not by semver tag
3. Dependency lockfiles (`bun.lock`, `uv.lock`) MUST be committed and kept in sync with manifest files
4. Dependency vulnerability scanning SHOULD run on a weekly schedule and on every push to `main`

### Content Security
1. Published site MUST use HTTPS exclusively
2. Documentation MUST NOT contain credentials, API keys, tokens, or secrets
3. External links in documentation SHOULD use `https://` URLs
4. Embedded resources (images, scripts) SHOULD use HTTPS origins

### Repository Security
1. Branch protection SHOULD be enabled on `main` requiring PR review
2. Secret scanning (e.g., `ggshield`, `trufflehog`) SHOULD be configured as a pre-commit hook
3. Dependabot or Renovate SHOULD be configured for automated dependency updates

## Non-Goals
- User authentication or authorization — the site is fully public
- Dynamic request sanitization — there are no runtime user inputs
- Encryption at rest — content is public; no sensitive data is stored
