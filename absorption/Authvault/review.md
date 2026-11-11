# review.md — Kilo Code Stand

## Kilo Code Stand

- **standard_id:** `kilo-code-stand@1`
- **applies_to:** all PRs; agent-authored commits
- **owner:** KooshaPari
- **charter:** [charter.md](charter.md)
- **sota:** [SOTA.md](SOTA.md)

## Review tiers

| Tier | Action | Rules |
|------|--------|-------|
| **Block** | Fail PR | Secrets; scope outside charter; domain logic in wrong role owner |
| **Warn** | Comment | Doc drift from SOTA; incomplete OKF update |
| **Info** | Optional | Style |

## Agent autonomy

Level **2** — agents may open PRs; human or CI merge required.
