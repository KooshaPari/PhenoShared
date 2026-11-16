# Security — SOTA (HexaKit genesis)

## Threat model

- Templates accidentally committing secrets placeholders
- Agents pushing to wrong GitHub accounts
- Domain code smuggled into genesis tree

## Controls

- `review.md` org blocklist (non-<REDACTED> remotes, force-push)
- `trufflehog` / secret scan workflows in template `.github/`
- Charter blocks new domain crates without review

## Alternatives

| Approach | Verdict |
|----------|---------|
| Per-repo ad-hoc policy | Rejected |
| Centralized SOC2 platform only | Overkill |
| **Kilo Code Stand + template scanners** | Chosen |
