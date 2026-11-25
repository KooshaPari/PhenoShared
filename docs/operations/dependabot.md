# Dependabot: scanning, rescan triggers, and remediation

## How scans are triggered

GitHub has **no public API to force a Dependabot rescan**. Scans happen when:

1. **A manifest changes** on the default branch (push to `Cargo.lock`, `go.mod`,
   `uv.lock`, `package-lock.json`, etc.). This is the only reliable on-demand trigger.
2. **The schedule** in [`.github/dependabot.yml`](../../.github/dependabot.yml) fires
   (currently `weekly` for every configured ecosystem).
3. GitHub's own background re-evaluation.

Observed in practice: merging dependency PRs #351/#352/#355 dropped open alerts
from **75 -> 45** on the next scan, without any manual trigger.

## On-demand rescan (when you need it now)

Push a trivial, harmless change to a manifest on `main`. Example:

```bash
cd ~/CodeProjects/Phenotype/repos/pheno
# no-op touch that still creates a commit so the push registers
printf '\n' >> crates/argis-extensions/go.mod
git add crates/argis-extensions/go.mod
git commit -m "chore: trigger dependabot rescan"
git push origin main          # LEFTHOOK=0 to skip the slow cargo pre-push hooks
```

The alert list refreshes within a few minutes.

Verify with:

```bash
gh api "repos/KooshaPari/PhenoShared/dependabot/alerts?state=open&per_page=100" --paginate \
  | python3 -c "import sys,json,collections; d=json.load(sys.stdin); d=[d] if isinstance(d,dict) else d; \
print(len(d), dict(collections.Counter(a['security_advisory']['severity'] for a in d)))"
```

## What is configured

`dependabot.yml` now tracks every ecosystem that has produced an advisory:

| Ecosystem | Directory |
|---|---|
| cargo | `/` (root workspace) |
| bun | `/` (root JS workspace) |
| gomod | `/crates/argis-extensions` |
| uv | `/python`, `/agileplus-mcp` |
| npm | `/docs`, `/crates/policystack`, `/crates/logify/docs`, `/crates/hexa-kit/templates/{typescript,hexagon/typescript}` |
| github-actions, terraform, cargo (iac) | pre-existing entries |

## Known blockers

- **`cargo` must run with `--offline`** for this workspace:
  `crates/phenotype-nvms-adapter` depends on
  `github.com/KooshaPari/nanovms.git`, which **returns 404**. Online resolution
  fails; the cached copy in `Cargo.lock` is used offline.
- **glib 0.18.5** (medium, Linux-only) is deferred: it is pulled by
  `tray-icon -> libappindicator 0.9 -> gtk 0.18.2`. Fixing it needs the gtk-rs
  0.20 ecosystem, which is not in the local cargo cache.
- `_archived/byteport/**` lockfiles are an intentionally frozen archive.
