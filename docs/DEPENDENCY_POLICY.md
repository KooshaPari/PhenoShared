# Dependency Management Policy

## Overview
This document outlines the dependency management policy for pheno-harness to ensure stability, security, and maintainability across the codebase.

## Version Pinning
- **Direct Dependencies**: All direct dependencies listed in `pyproject.toml` must be pinned to specific major.minor versions (e.g., `>=1.2.0`) or exact versions for critical infrastructure.
- **Lock Files**: Use `uv.lock` or `requirements.txt` to lock transitive dependencies. All CI/CD pipelines must use the lock file to ensure reproducible builds.
- **Minimum Version Strategy**: Use `>=` for flexibility in patch updates unless a specific feature requires a newer version.

## Audit Process
- **Automated Scanning**: Integrate `safety`, `pip-audit`, or `cargo audit` into CI pipelines to scan for known vulnerabilities (CVEs).
- **Manual Review**: Periodically review dependencies for license compliance (GPL/AGPL restrictions) and maintenance status.
- **Update Frequency**:
    - **Critical/Security Patches**: Apply immediately within 24 hours.
    - **Minor/Major Updates**: Evaluate quarterly or during major release cycles.

## Adding New Dependencies
1. **Justification**: Document the need for the dependency in the PR description.
2. **License Check**: Ensure the license is compatible (MIT, BSD, Apache 2.0 preferred).
3. **Size/Performance Impact**: Evaluate the dependency's footprint and performance overhead.
4. **Maintenance Health**: Check for recent commit activity and open issue response times.

## Removing Dependencies
- Remove unused dependencies immediately to reduce attack surface and bloat.
- Verify no implicit reliance exists via dynamic imports or runtime usage.
