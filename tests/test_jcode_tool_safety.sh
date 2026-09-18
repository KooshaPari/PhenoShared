#!/usr/bin/env bash
# Regression gate for the jcode pre_tool approval hook.
#
# The hook is invoked the way jcode invokes it: JCODE_HOOK_TOOL_NAME in the
# environment, the bare tool-input JSON on stdin. Exit 0 allows the call,
# exit 2 blocks it. Approval-required commands are deferred into the phinbox
# inbox by the elicitate shim; every record this test creates is removed again
# so the operator's inbox is left untouched.
set -euo pipefail

repo_root=$(cd "$(dirname "$0")/.." && pwd)
hook="$repo_root/guards/jcode-tool-safety"

inbox="$HOME/Library/Application Support/phinbox/inbox"
before_list=$(mktemp)
after_list=$(mktemp)
trap 'rm -f "$before_list" "$after_list"' EXIT
ls -1 "$inbox"/*.json 2>/dev/null | sort > "$before_list" || true

pass=0
fail=0

# A per-run token keeps generated request ids distinct from any approval the
# operator has already granted. Answering a request caches its decision for
# 24h, so reusing a fixed command string would let a cached approval mask a
# regression in the gate's own detection.
tag="t$$-$(date +%s)"

decide() { # $1=expected allow|block  $2=command
  local expected="$1" command="$2" status actual
  set +e
  printf '{"command":%s}' \
    "$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$command")" \
    | JCODE_HOOK_TOOL_NAME=bash "$hook" >/dev/null 2>&1
  status=$?
  set -e
  actual=block
  [ "$status" -eq 0 ] && actual=allow
  if [ "$actual" = "$expected" ]; then
    pass=$((pass + 1))
  else
    fail=$((fail + 1))
    echo "FAIL: expected $expected, got $actual: $command" >&2
  fi
}

# --- read-only calls must never require approval ---
decide allow 'gh api repos/a/b/x'
decide allow 'gh api repos/a/b/x --jq .name'
decide allow 'gh api --method GET -f a=b repos/a/b/x'
decide allow 'gh pr view 12'
decide allow 'gh pr list'
decide allow 'gh issue list'
decide allow 'gh run view 99'
decide allow 'gh repo view a/b'
decide allow 'gh release list'
decide allow 'gh label list'
decide allow 'gh cache list'
decide allow 'gh secret list'
decide allow 'gh variable list'
decide allow 'git status'
decide allow 'git log --oneline -5'
decide allow 'git push origin main'
decide allow 'git push --follow-tags origin main'
decide allow 'git branch -d merged-feature'

# --- GitHub writes must be gated ---
# gh api is a GET by default; every explicit write spelling is covered.
decide block "gh api -X PATCH repos/$tag/x -f state=dismissed"
decide block "gh api --method PATCH repos/$tag/x -f state=dismissed"
decide block "gh api --method=DELETE repos/$tag/x"
decide block "gh api -XPATCH repos/$tag/x"
decide block "gh api --method POST repos/$tag/x"
decide block "gh api repos/$tag/x -f state=dismissed"
decide block "gh api repos/$tag/x --field state=dismissed"
decide block "gh api repos/$tag/x -F state=dismissed"
decide block "gh api repos/$tag/x --input body.json"
decide block "gh api graphql -f query=mutation-$tag"
decide block 'gh secret set FOO --body bar'
decide block 'gh secret delete FOO'
decide block 'gh pr merge 12 --squash'
decide block 'gh pr comment 12 --body hi'
decide block 'gh issue close 5'
decide block 'gh issue reopen 5'
decide block "gh variable set FOO --body $tag"
decide block 'gh release create v1.0-$tag'
decide block 'gh workflow run ci.yml'
decide block 'gh run cancel 99'
decide block 'gh cache delete --all'
decide block 'gh label create bug'
decide block 'gh repo delete a/b --yes'
decide block 'gh repo fork a/b'
decide block 'gh repo archive a/b'
decide block 'gh repo rename newname'

# --- local history rewrites must be gated ---
decide block 'git push --force origin main'
decide block 'git push --force-with-lease origin main'
decide block 'git push -f origin main'
decide block 'git reset --hard HEAD~1'
decide block 'git reset --hard'
decide block 'git clean -fd'
decide block 'git clean -f -d'
decide block 'git branch -D feature'

# --- catastrophic commands are hard-blocked with no approval path ---
decide block 'rm -rf /'
decide block 'rm -rf /etc'
decide block 'rm -rf /usr'
decide block 'rm -rf /var/log'
decide block 'rm -rf /System'
decide block 'rm -rf /*'
decide block 'rm -fr /'
decide block 'rm -r -f /etc'
decide block 'rm -f /etc/hosts'
decide block 'mkfs.ext4 /dev/sda1'
decide block 'dd if=/dev/zero of=/dev/disk0'
decide block 'shutdown -h now'
decide block 'reboot'

# --- scoped deletes must stay allowed ---
decide allow 'rm -rf ./build'
decide allow 'rm -rf target/debug'
decide allow 'rm -rf /tmp/compile-cache'
decide allow 'rm -rf /Users/kooshapari/CodeProjects/foo/target'
decide allow 'rm -rf "$TMPDIR/scratch-1"'
decide allow 'rm -f ./stale.lock'

# phinbox queues asynchronously, so a record can land just after the hook
# returns. Settle before diffing or a leaked record would outlive the run.
sleep 3
ls -1 "$inbox"/*.json 2>/dev/null | sort > "$after_list" || true
created=$(comm -13 "$before_list" "$after_list")
if [ -n "$created" ]; then
  printf '%s\n' "$created" | while read -r record; do
    [ -f "$record" ] && rm -f "$record"
  done
fi

echo "jcode-tool-safety: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
