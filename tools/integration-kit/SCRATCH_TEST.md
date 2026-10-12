# Scratch-repo test evidence (2026-10-12)

The `tools/integration-kit/install.sh` script was tested against a freshly
created scratch repo (`/tmp/instinct-scratch-test`) created with:

```bash
git init /tmp/instinct-scratch-test
git -C /tmp/instinct-scratch-test commit --allow-empty -m 'chore: initial commit'
```

## Test 1 — full install (no flags)

Command:
```bash
bash tools/integration-kit/install.sh \
  --source /tmp/instinct-kit-20261012 \
  --target /tmp/instinct-scratch-test
```

Output (relevant excerpt):
```
[install] workflows → /tmp/instinct-scratch-test/.github/workflows-reusable/
  COPIED: .github/workflows-reusable/lint.yml
  COPIED: .github/workflows-reusable/release.yml
  COPIED: .github/workflows-reusable/test.yml
[install] lefthook → /tmp/instinct-scratch-test/lefthook.yml
  COPIED: lefthook.yml
[install] mcp hooks → /tmp/instinct-scratch-test/.mcp-hooks.json
  COPIED: .mcp-hooks.json
[install] scripts → /tmp/instinct-scratch-test/tools/integration-kit/
  COPIED: tools/integration-kit/install.sh

[install] post-install verification:
  ✓ .github/workflows-reusable/lint.yml present
  ✓ .github/workflows-reusable/test.yml present
  ✓ .github/workflows-reusable/release.yml present
  ✓ lefthook.yml present
  ✓ .mcp-hooks.json present and valid JSON
  ✓ tools/integration-kit/install.sh present and executable
```

Result: all 6 expected files installed, all checks pass.

## Test 2 — JSON round-trip

Command:
```bash
python3 -c "import json; d=json.load(open('/tmp/instinct-scratch-test/.mcp-hooks.json')); print('valid-after-install:', list(d['hooks'].keys()))"
```

Result:
```
valid-after-install: ['PreToolUse', 'PostToolUse', 'Notification', 'Stop']
```

JSON file survived the install intact.

## Test 3 — idempotency (re-run without --force)

Command:
```bash
bash tools/integration-kit/install.sh \
  --source /tmp/instinct-kit-20261012 \
  --target /tmp/instinct-scratch-test \
  --components workflows
```

Output (relevant excerpt):
```
[install] workflows → /tmp/instinct-scratch-test/.github/workflows-reusable/
  SKIP (exists): .github/workflows-reusable/lint.yml — re-run with --force to overwrite
  SKIP (exists): .github/workflows-reusable/release.yml — re-run with --force to overwrite
```

Result: existing files preserved; no overwrites.

## Test 4 — force overwrite

Command:
```bash
bash tools/integration-kit/install.sh \
  --source /tmp/instinct-kit-20261012 \
  --target /tmp/instinct-scratch-test \
  --components workflows \
  --force
```

Output:
```
[install] workflows → /tmp/instinct-scratch-test/.github/workflows-reusable/
  COPIED: .github/workflows-reusable/lint.yml
  COPIED: .github/workflows-reusable/release.yml
```

Result: `--force` overwrites existing files as expected.

## Test 5 — dry-run against an existing repo

Command:
```bash
bash tools/integration-kit/install.sh \
  --source /tmp/instinct-kit-20261012 \
  --target ~/CodeProjects/Phenotype/repos/phenotype-registry \
  --components workflows \
  --dry-run
```

Output (relevant excerpt):
```
[install] workflows → /Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-registry/.github/workflows-reusable/
  WOULD COPY: .github/workflows-reusable/lint.yml
  WOULD COPY: .github/workflows-reusable/release.yml
  WOULD COPY: .github/workflows-reusable/test.yml

[install] post-install verification:
  ✗ .github/workflows-reusable/lint.yml MISSING
  ✗ .github/workflows-reusable/test.yml MISSING
  ✗ .github/workflows-reusable/release.yml MISSING
```

Result: dry-run reports the plan without modifying the target.

## Summary

| Test | Outcome | Notes |
|------|---------|-------|
| Full install on empty repo | PASS | All 6 files installed, ✓ all checks |
| JSON round-trip | PASS | mcp-hooks.json still valid in target |
| Re-run without --force | PASS | SKIPs reported, no overwrites |
| --force overwrite | PASS | Overwrites as expected |
| --dry-run against existing repo | PASS | Plan reported, no modifications |

The install script is functional. Tests were run by jcode at 2026-10-12T23:03Z.

The scratch repo (`/tmp/instinct-scratch-test`) was a temporary test fixture
and was not pushed or committed anywhere outside this evidence note.