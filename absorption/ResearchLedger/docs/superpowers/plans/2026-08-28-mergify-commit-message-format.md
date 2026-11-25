# Mergify Commit Message Format Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Mergify's deprecated templates with supported declarative commit-message formatting without changing auto-merge eligibility.

**Architecture:** Change only the two affected `actions.merge` configuration blocks. The declarative format keeps Mergify's pull-request-title subject, emits no body content, and generates valid trailers from actual commit authors. Validation combines local YAML parsing, a negative scan for the deprecated key, and Mergify's hosted configuration check.

**Tech Stack:** YAML, Mergify workflow automation, GitHub Actions, Bun for repository-local quality commands.

---

## Task 1: Prove the current deprecated configuration

**Files:**

- Inspect: `.mergify.yml:17-39`

- [ ] **Step 1: Scan both existing templates**

Run:

```bash
rg -n -C 3 'commit_message_template' .mergify.yml
```

Expected: exactly two occurrences, in `Auto-merge when approved + CI green` and `Auto-merge dependency updates`.

- [ ] **Step 2: Parse the unmodified YAML**

Run:

```bash
ruby -e 'require "yaml"; YAML.load_file(".mergify.yml"); puts "yaml_ok"'
```

Expected: `yaml_ok`.

## Task 2: Replace both templates with supported declarative formats

**Files:**

- Modify: `.mergify.yml:17-39`

- [ ] **Step 1: Make the focused configuration change**

Replace each:

```yaml
commit_message_template: |
  {{ title }} (#{{ number }})

  Co-authored-by: {{ author }}
```

with:

```yaml
commit_message_format:
  title: pr-title
  body: empty
  trailers:
    - co-authored-by
```

- [ ] **Step 2: Inspect the diff for scope**

Run:

```bash
git diff --check && git diff -- .mergify.yml
```

Expected: no whitespace errors and only the two intended merge-rule changes.

## Task 3: Validate and publish the protected PR

**Files:**

- Modify: `.mergify.yml:17-39`
- Test: `.mergify.yml` configuration check on GitHub

- [ ] **Step 1: Validate the resulting YAML and absence of the deprecated key**

Run:

```bash
ruby -e 'require "yaml"; YAML.load_file(".mergify.yml"); puts "yaml_ok"'
if rg -n 'commit_message_template' .mergify.yml; then
  echo 'deprecated key remains' >&2
  exit 1
else
  status=$?
  test "$status" -eq 1 || exit "$status"
fi
```

Expected: `yaml_ok`, followed by no search output and exit status 0.

- [ ] **Step 2: Run the repository configuration-quality commands**

Run:

```bash
bun run verify:resources
bun run verify:csp
```

Expected: both commands exit 0.

- [ ] **Step 3: Commit and push the focused change**

Run:

```bash
git add .mergify.yml
git commit -m 'ci(mergify): migrate commit message formatting'
git push -u origin fix/mergify-commit-message-format
```

Expected: one configuration commit published without rewriting any existing ref.

- [ ] **Step 4: Open and qualify the PR**

Run:

```bash
gh pr create --base main --head fix/mergify-commit-message-format --title 'ci(mergify): migrate commit message formatting' --body 'Migrates both deprecated commit_message_template rules to Mergify commit_message_format. Preserves PR-title subjects and replaces generic author-only trailers with canonical commit-author provenance.'
gh pr checks --watch
```

Expected: Mergify configuration validation and the normal required checks pass; then use the normal repository review and merge policy.
