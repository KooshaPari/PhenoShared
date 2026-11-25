<!-- .github/PULL_REQUEST_TEMPLATE.md
     Tier-0 fleet-standard PR template.
     Trim sections that do not apply, but keep Summary + Testing. -->

## Summary

<!-- One to three sentences: what does this PR do and why? -->

## Changes

<!-- Bullet list of the key user-visible or maintainer-visible changes. -->
-

## Testing

<!-- How was this verified? Tick all that apply. -->
- [ ] `pytest` passes locally
- [ ] `ruff check .` passes locally
- [ ] Manual smoke test (describe below)
- [ ] New tests added / updated

## Risk & Rollout

<!-- Note any migrations, feature flags, or coordination needed. -->
- [ ] No DB migration
- [ ] No public API change
- [ ] Backwards compatible

## Related

<!-- Issues, PRs, specs, or worklog entries this addresses. -->
- Closes #
- Refs:

## Checklist

- [ ] Conventional commit title (`feat:`, `fix:`, `chore:`, …)
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] Self-review performed
