# npm release — `@phenotype/design`

First-publish checklist and one-command finish after `NPM_TOKEN` is configured.

## Prerequisites

| Requirement | Status (2026-07-21) | Action |
|-------------|---------------------|--------|
| Package name `@phenotype/design` on `main` | Done (#79) | — |
| `publishConfig.access: public` in `package.json` | Done (#79) | — |
| `publish.yml` workflow on `main` | Done | This PR hardens it |
| npm org `@phenotype` membership | **Verify** | [npmjs.com/org/phenotype](https://www.npmjs.com/org/phenotype) — publisher account must be in the org |
| `NPM_TOKEN` GitHub secret | **Missing** | Automation token with publish rights to `@phenotype/design` |
| Prior npm publish | **None** | `npm view @phenotype/design` returns 404 |

### Why `v2.0.1` (not reusing `v2.0.0`)

- Git tag `v2.0.0` points at `@kooshapari/design` and has a GitHub release, but **never**
  triggered a successful npm publish (no `NPM_TOKEN`, zero `publish.yml` runs).
- `2.0.1` is the first semver aligned with `@phenotype/design` SSOT for registry consumers.

## One-command finish (after merge)

```bash
# 1. Configure npm automation token (once)
gh secret set NPM_TOKEN -R KooshaPari/phenoDesign --body "$NPM_TOKEN"

# 2. Dry-run the publish workflow (optional)
gh workflow run publish.yml -R KooshaPari/phenoDesign -f dry_run=true

# 3. Create GitHub release → triggers publish.yml on release:published
gh release create v2.0.1 \
  -R KooshaPari/phenoDesign \
  --title "v2.0.1 — @phenotype/design (first npm)" \
  --notes "First public npm release of @phenotype/design. Fleet consumers can switch from github:KooshaPari/phenoDesign to bun add @phenotype/design@2.0.1."

# 4. Verify
npm view @phenotype/design version
```

## Local publish (alternative)

Requires `npm login` or `NPM_TOKEN` with publish access to the `@phenotype` scope:

```bash
cd /path/to/phenoDesign
bun install --frozen-lockfile
bun run build
bun run test
npm publish --access public
```

## Consumer migration (next AC)

After `2.0.1` is on npm, fleet repos can replace:

```json
"@phenotype/design": "github:KooshaPari/phenoDesign"
```

with:

```json
"@phenotype/design": "^2.0.1"
```

Affected repos: `heliosApp`, `phenodocs`, `thegent` (per fleet consumer PRs #526, #210/#211, #1156).
