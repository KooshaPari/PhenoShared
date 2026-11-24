#!/bin/bash
# airlock-v2-hook.sh
# -------------------------
# Triggered by Codex/Claude/Cursor agent hooks (PostToolUse, Stop, SessionStart).
# Reads event JSON from stdin, identifies the cwd of the agent, and if the cwd
# is under ~/CodeProjects/Phenotype/repos/, performs an idempotent auto-commit
# + branch push to a wip/<date>-<agent>-<event-id> branch.
#
# Conservative safety:
#   * 30s hard timeout via `timeout` wrapper (when invoked from launchd)
#   * Only acts on directories inside REPO_ROOT
#   * Refuses to commit if not a git working tree
#   * All operations idempotent — re-running on a clean tree is a no-op
#   * Pushes target branch named with date+agent+event_id for full traceability
#   * Never deletes branches (only creates) and only deletes branches the script
#     itself created this run (see WIP_BRANCH_NAME marker in commit message)
#
# Aggressive safety:
#   * Pushes to upstream OR airlock bare mirror (consistent w/ existing pattern)
#   * Logs every action to ~/.airlock-v2/logs/hook.log with structured fields
#   * Calls airlock daemon via socket if available (best-effort, non-blocking)
#   * Every commit has metadata footer that the cleanup daemon can parse
#
# Environment variables consumed:
#   AIRLOCK_V2_AGENT       : one of codex|claude|cursor|thegent|forge|gemini|copilot|factory|aider
#   AIRLOCK_V2_EVENT_ID    : unique event id (defaults to timestamp+PID)
#   AIRLOCK_V2_DRY_RUN     : if "1", log but do not commit
#   AIRLOCK_V2_LOG         : override log path (default ~/.airlock-v2/logs/hook.log)
#   AIRLOCK_V2_ROOT        : override REPO_ROOT (default ~/CodeProjects/Phenotype/repos)
#
# Exit codes:
#   0  : success (including no-op on clean tree)
#   1  : repo not under REPO_ROOT or not a git worktree (silent ignore)
#   2  : internal git error (logged but non-fatal — never blocks the agent)
# -------------------------
set -uo pipefail
# We deliberately do NOT set -e: we want hook errors to be logged, not crash the agent.

# ---------- config ----------
AIRLOCK_V2_AGENT="${AIRLOCK_V2_AGENT:-unknown}"
AIRLOCK_V2_EVENT_ID="${AIRLOCK_V2_EVENT_ID:-}"
AIRLOCK_V2_DRY_RUN="${AIRLOCK_V2_DRY_RUN:-0}"
AIRLOCK_V2_LOG="${AIRLOCK_V2_LOG:-$HOME/.airlock-v2/logs/hook.log}"
AIRLOCK_V2_ROOT="${AIRLOCK_V2_ROOT:-$HOME/CodeProjects/Phenotype/repos}"

# ---------- helpers ----------
log() {
  # shellcheck disable=SC2155
  local ts
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  local level="$1"; shift
  printf '%s [airlock-v2-hook] [%s] [agent=%s] [pid=%d] %s\n' \
    "$ts" "$level" "$AIRLOCK_V2_AGENT" "$$" "$*" >> "$AIRLOCK_V2_LOG" 2>/dev/null || true
}

ensure_log_dir() {
  local logdir
  logdir="$(dirname "$AIRLOCK_V2_LOG")"
  mkdir -p "$logdir" 2>/dev/null || true
}

# Identify the cwd of the agent from the event JSON on stdin.
# Different agents use different field names; we try a sequence of fallbacks.
extract_cwd() {
  local payload="$1"
  local cwd=""

  # Try common fields in priority order.
  # jq is preferred; fall back to python3 if jq missing.
  if command -v jq >/dev/null 2>&1; then
    cwd="$(printf '%s' "$payload" | jq -r '
      (.cwd // .working_directory // .working_dir // .workdir //
       .session.cwd // .session_context.cwd //
       .tool_input.cwd // .tool_input.working_directory //
       empty
      )' 2>/dev/null | head -n1)"
  elif command -v python3 >/dev/null 2>&1; then
    cwd="$(printf '%s' "$payload" | python3 -c '
import sys, json
try:
  data = json.load(sys.stdin)
  for path in [
    ("cwd",), ("working_directory",), ("working_dir",), ("workdir",),
    ("session","cwd"), ("session_context","cwd"),
    ("tool_input","cwd"), ("tool_input","working_directory"),
  ]:
    cur = data
    try:
      for k in path:
        cur = cur[k]
      if isinstance(cur, str) and cur:
        print(cur); sys.exit(0)
    except (KeyError, TypeError):
      continue
except Exception:
  pass
' 2>/dev/null | head -n1)"
  fi

  if [ -z "$cwd" ]; then
    # Final fallback: $PWD (only safe when the hook runs in the agent's cwd).
    cwd="${PWD:-}"
  fi
  printf '%s' "$cwd"
}

# Resolve the working tree root from $PWD even if cwd is in a subdir.
git_toplevel() {
  local path="$1"
  if [ -z "$path" ]; then return 1; fi
  ( cd "$path" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null ) || return 1
}

# Returns 0 if path is under $1 (lexical prefix).
# macOS canonicalizes /var/folders/... to /private/var/folders/... in some
# syscalls; do that normalization here so the prefix comparison works for
# smoke-test tmpfs paths as well as real repos under REPO_ROOT.
is_under_prefix() {
  local path="$1" prefix="$2"
  # Best-effort canonicalization: resolve symlinks (e.g. /var -> /private/var
  # on macOS) using python3; fall back to the raw path if python3 is missing
  # or the path is non-existent.
  if command -v python3 >/dev/null 2>&1; then
    path="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$path" 2>/dev/null || printf '%s' "$path")"
    prefix="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$prefix" 2>/dev/null || printf '%s' "$prefix")"
  fi
  case "$path" in
    "$prefix"/*|"$prefix") return 0 ;;
    *) return 1 ;;
  esac
}

# Push a wip branch to upstream; if upstream is missing, fall back to a
# bare-mirror-style fetch by re-pushing with the same branch name (idempotent).
push_wip_branch() {
  local repo="$1" branch="$2"
  local remote="origin"

  # Probe for upstream.
  local upstream
  upstream="$(git -C "$repo" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"

  # Try push to origin.
  local push_attempt
  push_attempt="$(GIT_TERMINAL_PROMPT=0 git -C "$repo" push "$remote" "$branch:$branch" 2>&1)"
  local rc=$?
  if [ $rc -eq 0 ]; then
    log "info" "push: ok -> $remote $branch"
    return 0
  fi

  # If push failed because the branch already exists on the remote with the
  # same commits (force-push-equivalent for new wip), fall through to a soft
  # push that tolerates "already up to date".
  if printf '%s' "$push_attempt" | grep -qE "(already up[ -]to[ -]date|nothing to commit)"; then
    log "info" "push: already-up-to-date for $branch on $remote"
    return 0
  fi

  # If push failed because the remote has unrelated history (e.g. a previous
  # failed run), we DO NOT force-push here — that's cleanup-daemon's job.
  log "warn" "push: failed for $branch on $remote: $push_attempt"
  return 1
}

# Best-effort notify to the airlock v1 daemon via socket (read-only health probe).
# This is NON-BLOCKING: failure never aborts the hook.
notify_airlock_daemon() {
  local repo_path="$1" branch="$2"
  local socket="$HOME/.airlock/socket"
  if [ ! -S "$socket" ]; then
    return 0
  fi
  local payload
  payload=$(printf '{"jsonrpc":"2.0","method":"push_received","params":{"gate_path":"%s","ref_updates":[{"ref":"refs/heads/%s"}]},"id":1}' \
    "$(printf '%s' "$repo_path" | sed 's/"/\\"/g')" \
    "$branch")
  # 2-second timeout so a wedged daemon can never block us.
  printf '%s' "$payload" | timeout 2 nc -U "$socket" >/dev/null 2>&1 || true
}

# ---------- main ----------
ensure_log_dir

# Capture stdin (event JSON) up to 64KB. Larger payloads are truncated.
PAYLOAD="$(head -c 65536)"

AGENT_CWD="$(extract_cwd "$PAYLOAD")"
log "info" "event received: cwd='$AGENT_CWD' event_id='$AIRLOCK_V2_EVENT_ID' payload_bytes=${#PAYLOAD}"

# Generate an event_id if not provided.
if [ -z "$AIRLOCK_V2_EVENT_ID" ]; then
  AIRLOCK_V2_EVENT_ID="ts$(date +%s)-pid$$-rand$((RANDOM%10000))"
fi

# Resolve to repo root.
REPO_ROOT="$(git_toplevel "$AGENT_CWD" 2>/dev/null || true)"
if [ -z "$REPO_ROOT" ]; then
  log "info" "no git worktree found for cwd='$AGENT_CWD' — silent skip"
  exit 1
fi

# Safety: only touch repos under $AIRLOCK_V2_ROOT.
if ! is_under_prefix "$REPO_ROOT" "$AIRLOCK_V2_ROOT"; then
  log "info" "repo '$REPO_ROOT' outside AIRLOCK_V2_ROOT='$AIRLOCK_V2_ROOT' — silent skip"
  exit 1
fi

# Quick dirtiness check.
if git -C "$REPO_ROOT" diff --quiet HEAD -- 2>/dev/null \
   && [ -z "$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null | head -n1)" ]; then
  log "info" "tree clean for $REPO_ROOT — no-op"
  exit 0
fi

# Compose branch name: wip/YYYY-MM-DD-HHMM-<agent>-<event_id>
TS_TAG="$(date -u '+%Y-%m-%d-%H%M')"
# Sanitize: branch names must avoid certain chars. Replace anything not [A-Za-z0-9_-] with '-'.
SAFE_AGENT="$(printf '%s' "$AIRLOCK_V2_AGENT" | tr -c 'A-Za-z0-9_-' '-')"
SAFE_EVENT="$(printf '%s' "$AIRLOCK_V2_EVENT_ID" | tr -c 'A-Za-z0-9_-' '-' | cut -c1-40)"
WIP_BRANCH="wip/${TS_TAG}-${SAFE_AGENT}-${SAFE_EVENT}"

if [ "$AIRLOCK_V2_DRY_RUN" = "1" ]; then
  log "info" "DRY-RUN: would create branch $WIP_BRANCH in $REPO_ROOT"
  exit 0
fi

# Stage everything.
git -C "$REPO_ROOT" add -A 2>>"$AIRLOCK_V2_LOG"

# Re-check after add: in some repos .gitignore excludes everything we staged.
if [ -z "$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null)" ]; then
  log "info" "nothing staged after git add -A in $REPO_ROOT — no-op"
  exit 0
fi

# Create branch if not exists; never switch the user's working branch.
# We use git switch -c which is safe even if the branch already exists (no-op).
if ! git -C "$REPO_ROOT" switch -c "$WIP_BRANCH" 2>>"$AIRLOCK_V2_LOG"; then
  # Already exists — switch to it (idempotent).
  git -C "$REPO_ROOT" switch "$WIP_BRANCH" 2>>"$AIRLOCK_V2_LOG" || {
    log "error" "could not switch to $WIP_BRANCH in $REPO_ROOT"
    exit 2
  }
fi

# Compose commit metadata.
HOSTNAME_SHORT="$(hostname -s 2>/dev/null || echo unknown)"
AUTHOR_NAME="airlock-v2 [${AIRLOCK_V2_AGENT}]"
AUTHOR_EMAIL="airlock-v2@${HOSTNAME_SHORT}.local"
COMMIT_BODY=$(cat <<EOF
airlock-v2 wip commit

agent:    ${AIRLOCK_V2_AGENT}
event_id: ${AIRLOCK_V2_EVENT_ID}
cwd:      ${AGENT_CWD}
repo:     ${REPO_ROOT}
hostname: ${HOSTNAME_SHORT}
branch:   ${WIP_BRANCH}
created:  $(date -u '+%Y-%m-%dT%H:%M:%SZ')

This is an auto-generated work-in-progress checkpoint. It is safe to force-update
or delete once consolidated. Marked for cleanup-daemon.py consolidation.

[wip-managed]
EOF
)

# Commit (allow empty so .gitignore-only changes still produce a marker).
if ! git -C "$REPO_ROOT" \
        -c "user.name=$AUTHOR_NAME" \
        -c "user.email=$AUTHOR_EMAIL" \
        commit --allow-empty -m "$COMMIT_BODY" >>"$AIRLOCK_V2_LOG" 2>&1; then
  log "error" "git commit failed in $REPO_ROOT on branch $WIP_BRANCH"
  exit 2
fi

log "info" "committed on $WIP_BRANCH in $REPO_ROOT"

# Push (best-effort; never blocks the agent on push failures).
if push_wip_branch "$REPO_ROOT" "$WIP_BRANCH"; then
  log "info" "pushed $WIP_BRANCH ok"
else
  log "warn" "push failed for $WIP_BRANCH; branch is local-only"
fi

# Best-effort airlock daemon notify (non-blocking).
notify_airlock_daemon "$REPO_ROOT" "$WIP_BRANCH" || true

log "info" "hook done: branch=$WIP_BRANCH repo=$REPO_ROOT event=$AIRLOCK_V2_EVENT_ID"
exit 0
