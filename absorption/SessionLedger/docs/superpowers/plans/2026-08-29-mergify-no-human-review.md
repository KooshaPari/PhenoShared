# Mergify No-Human-Review Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow SessionLedger pull requests to auto-merge after configured CI succeeds without a human approval or reviewer-completion predicate.

**Architecture:** Modify only `.mergify.yml` for behavior, plus these execution docs for the corrected invariant. The Mergify merge and ready-label rules stop testing approval or reviewer-completion counts while retaining CI, conflict, open-PR, squash, labeling, reviewer notification, and large-PR behavior. Shell validation parses the YAML and asserts the policy invariants without requiring a paid service.

**Tech Stack:** Mergify YAML, Ruby standard-library YAML parser, GitHub pull-request automation.

---

### Task 1: Remove Mergify human-completion predicates while retaining CI gates

**Files:**

- Modify: `.mergify.yml:4-26,67-79`
- Test: inline Ruby policy assertions against `.mergify.yml`

- [ ] **Step 1: Write the failing policy assertion**

Run:

```bash
ruby -e '
require "yaml"
rules = YAML.load_file(".mergify.yml").fetch("pull_request_rules")
merge = rules.find { |rule| rule.fetch("name") == "Auto-merge when CI green" }
ready = rules.find { |rule| rule.fetch("name") == "Add ready-to-merge label" }
raise "merge rule missing" unless merge
raise "ready rule missing" unless ready
raise "human review completion predicate remains" if [merge, ready].flat_map { |rule| rule.fetch("conditions") }.any? { |condition| condition.include?("approved-reviews") || condition.include?("review-requested") }
raise "missing ci gate" unless merge.fetch("conditions").include?("check-success=ci")
raise "missing lint gate" unless merge.fetch("conditions").include?("check-success=lint")
raise "missing test gate" unless merge.fetch("conditions").include?("check-success=test")
raise "missing conflict gate" unless merge.fetch("conditions").include?("-conflict")
puts "Mergify no-human-review policy: valid"
'
```

Expected: fail because the current merge rule still contains
`#review-requested=0`.

- [ ] **Step 2: Edit only the two policy rules**

Replace the merge rule heading and name with:

```yaml
# Auto-merge when all configured CI checks pass.
- name: Auto-merge when CI green
```

Delete these human-completion condition entries, and no other safeguards:

```yaml
- "#approved-reviews-by>=1"
- "#review-requested=0"
```

Keep these merge conditions exactly:

```yaml
- check-success=ci
- check-success=lint
- check-success=typecheck
- check-success=test
- -conflict
- -closed
```

- [ ] **Step 3: Run policy validation**

Run the Step 1 Ruby command again.

Expected: `Mergify no-human-review policy: valid`.

- [ ] **Step 4: Run syntax and scope checks**

Run:

```bash
ruby -e 'require "yaml"; YAML.load_file(".mergify.yml"); puts "mergify YAML: valid"'
git diff --check
git diff -- .mergify.yml
```

Expected: valid YAML, no whitespace errors, and only the human-completion
predicates plus the merge rule wording changed.

- [ ] **Step 5: Commit, push, and open the policy PR**

Run:

```bash
git add .mergify.yml docs/superpowers/specs/2026-08-29-mergify-no-human-review-design.md docs/superpowers/plans/2026-08-29-mergify-no-human-review.md
git commit -m "ci(mergify): remove human completion gate"
git push -u origin ci/mergify-no-human-review
gh pr create --base main --head ci/mergify-no-human-review --title "ci(mergify): remove human completion gate" --body "Removes only Mergify human-completion predicates while retaining CI and conflict gates. Validated YAML and policy invariants locally."
```

Expected: one policy-only PR with normal hosted CI and auto-merge enabled.
