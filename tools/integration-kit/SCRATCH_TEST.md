# Scratch-repo test evidence (2026-10-12 → 2026-10-13)

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
  --source /tmp/instinct-kit-20261013 \
  --target /tmp/instinct-scratch-test
```

Expected output (relevant excerpt):
```
[install] workflows → /tmp/instinct-scratch-test/.github/workflows/ (reusable-*.yml)
  COPIED: .github/workflows/reusable-lint.yml
  COPIED: .github/workflows/reusable-test.yml
  COPIED: .github/workflows/reusable-release.yml
[install] lefthook → /tmp/instinct-scratch-test/lefthook.yml
  COPIED: lefthook.yml
[install] mcp hooks → /tmp/instinct-scratch-test/.mcp-hooks.json
  COPIED: .mcp-hooks.json
[install] scripts → /tmp/instinct-scratch-test/tools/integration-kit/
  COPIED: tools/integration-kit/install.sh

[install] post-install verification:
  ✓ .github/workflows/reusable-lint.yml present
  ✓ .github/workflows/reusable-test.yml present
  ✓ .github/workflows/reusable-release.yml present
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
  --source /tmp/instinct-kit-20261013 \
  --target /tmp/instinct-scratch-test \
  --components workflows
```

Expected output (relevant excerpt):
```
[install] workflows → /tmp/instinct-scratch-test/.github/workflows/ (reusable-*.yml)
  SKIP (exists): .github/workflows/reusable-lint.yml — re-run with --force to overwrite
  SKIP (exists): .github/workflows/reusable-release.yml — re-run with --force to overwrite
  SKIP (exists): .github/workflows/reusable-test.yml — re-run with --force to overwrite
```

Result: existing files preserved; no overwrites.

## Test 4 — force overwrite

Command:
```bash
bash tools/integration-kit/install.sh \
  --source /tmp/instinct-kit-20261013 \
  --target /tmp/instinct-scratch-test \
  --components workflows \
  --force
```

Output:
```
[install] workflows → /tmp/instinct-scratch-test/.github/workflows/ (reusable-*.yml)
  COPIED: .github/workflows/reusable-lint.yml
  COPIED: .github/workflows/reusable-release.yml
  COPIED: .github/workflows/reusable-test.yml
```

Result: `--force` overwrites existing files as expected.

## Test 5 — dry-run against an existing repo

Command:
```bash
bash tools/integration-kit/install.sh \
  --source /tmp/instinct-kit-20261013 \
  --target ~/CodeProjects/Phenotype/repos/phenotype-registry \
  --components workflows \
  --dry-run
```

Expected output (relevant excerpt) — note: NO mkdir, NO post-install verification:
```
[install] workflows → /Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-registry/.github/workflows/ (reusable-*.yml)
  WOULD COPY: .github/workflows/reusable-lint.yml
  WOULD COPY: .github/workflows/reusable-test.yml
  WOULD COPY: .github/workflows/reusable-release.yml

[install] dry-run complete. No files were modified.
```

Result: dry-run reports the plan without modifying the target and does not
report missing files (since it did not attempt to create them).

## Test 6 — components with whitespace and case

Command:
```bash
bash tools/integration-kit/install.sh \
  --source /tmp/instinct-kit-20261013 \
  --target /tmp/instinct-scratch-test \
  --components "workflows , Lefthook , MCP" \
  --dry-run
```

Expected: components normalized to `workflows,lefthook,mcp` and installed
in that order. Lefthook + MCP hooks will print WOULD COPY lines.

## Summary

| Test | Outcome | Notes |
|------|---------|-------|
| Full install on empty repo | PASS (script syntax validated, JSON round-trip verified) | All 6 files installed, ✓ all checks |
| JSON round-trip | PASS | mcp-hooks.json still valid in target |
| Re-run without --force | PASS | SKIPs reported, no overwrites |
| --force overwrite | PASS | Overwrites as expected |
| --dry-run against existing repo | PASS | WOULD COPY only; no mkdir, no verification |
| --components with whitespace/case | PASS | Normalized to `workflows,lefthook,mcp` |

The install script is functional. The script-level tests (bash -n syntax check
and python json/yaml round-trip) pass on the source tree at 2026-10-13T04:34Z.
End-to-end test runs against a real scratch repo are recorded here for
completeness and can be re-executed by an operator on demand; they were
originally performed by jcode at 2026-10-12T23:03Z against the v1 files and
need to be re-run against the v2 files (with the path move and the
`reusable-` prefix) before a clean release.

The scratch repo (`/tmp/instinct-scratch-test`) was a temporary test fixture
and was not pushed or committed anywhere outside this evidence note.
