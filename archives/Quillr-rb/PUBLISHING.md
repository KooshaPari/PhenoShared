# Publishing `@kooshapari/quillts` to npm

This document covers the full release flow for the TypeScript package.

## Prerequisites

1. **npm account** — you must be logged in (`npm whoami`).
2. **NPM_TOKEN** — set in `.npmrc` (already configured to read `NPM_TOKEN` env var).
3. **Build passes** — `npm run quality` must be green before any publish.

## Quick reference

```bash
# 1. Run the full quality gate
npm run quality

# 2. Bump the version (this creates a git tag automatically)
npm version patch   # 0.1.0 -> 0.1.1  (bug fixes)
npm version minor   # 0.1.0 -> 0.2.0  (new features, backwards compatible)
npm version major   # 0.1.0 -> 1.0.0  (breaking changes)

# 3. Push the commit AND the tag
git push --follow-tags

# 4. Publish to npm
npm publish
```

That's it. The `publishConfig` in `package.json` already points to the public
npm registry, so `npm publish` picks up the right target automatically.

## Step-by-step

### 1. Quality gate

```bash
npm run quality
```

This runs format check, lint, type-check, tests with coverage, traceability
verification, and a production build — all in sequence. Fix any failures before
proceeding.

### 2. Version bump

`npm version` updates `package.json`, commits the change, and creates a git tag
named `v<version>`.

| Command | When to use |
|---------|-------------|
| `npm version patch` | Bug fixes, doc updates, internal refactors |
| `npm version minor` | New features that are backwards-compatible |
| `npm version major` | Breaking API changes |

> **Tip:** To include a release note in the tag message, pass `--message`:
> ```bash
> npm version patch -m "fix: resolve retry backoff jitter"
> ```

### 3. Push to GitHub

```bash
git push --follow-tags
```

This pushes the version commit and the `v<version>` tag so GitHub can create a
matching release if desired.

### 4. Publish

```bash
npm publish
```

The `.npmrc` file provides the auth token via the `NPM_TOKEN` environment
variable. If publishing from CI, ensure `NPM_TOKEN` is set as a repository
secret.

### 5. Verify

After publishing, confirm the new version appears on the
[package page](https://www.npmjs.com/package/@kooshapari/quillts) and that
installation works:

```bash
npm info @kooshapari/quillts version
# should print the version you just published
```

## Publishing from CI (GitHub Actions)

If you prefer automated releases, set the `NPM_TOKEN` secret in your GitHub
repo settings and add a step like:

```yaml
- name: Publish to npm
  run: npm publish
  env:
    NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
```

Trigger this on tag pushes (`v*`) or after a successful CI run on `main`.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `401 Unauthorized` | `NPM_TOKEN` is missing or expired — regenerate at npmjs.com |
| `403 Forbidden` | You're not a maintainer of `@kooshapari/quillts` — add yourself via `npm owner add` |
| `402 Payment Required` | Scoped packages require a paid npm plan for private access — use `"access": "public"` (already set) |
| Tag already exists | `git tag -d v<version> && git push --delete origin v<version>`, then re-run `npm version` |
