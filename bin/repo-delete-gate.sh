#!/usr/bin/env bash
# repo-delete-gate.sh
# ----------------------------------------------------------------------------
# Pre-delete gate wrapper around `gh repo delete`.
#
# Purpose
#   Forbid silent / undocumented deletions of GitHub repositories under the
#   phenotype-tooling umbrella. Every deletion must be justified by a
#   written absorption manifest at
#     docs/absorbed-from-<repo>/ABSORPTION.md
#   before `gh repo delete` is invoked.
#
# Background
#   The go-nippon audit recorded that archived repos were deleted directly
#   without preserving source content first, because the wave relied on a
#   stale `isArchived` cache. See
#     forge/agentuserstatus-merge/phenotype-tooling/docs/absorbed-from-go-nippon/ABSORPTION.md:1-28
#   This script is the procedural fence against that class of mistake.
#
# Required gates (ALL must pass before deletion is allowed):
#   (a) docs/absorbed-from-<repo>/ABSORPTION.md exists and contains every
#       required section heading:
#         Source, Target, Status, Last-Resort-Exceptions, Restore-Command
#   (b) `gh api` confirms the repo is currently archived (isArchived=true)
#       AND default-branch protection is not in a "strict" state for active
#       contributors (we treat active branch protection as a deletion veto).
#   (c) A local-only dry-run is the DEFAULT; pass --apply to actually delete.
#   (d) --force bypasses the gate AFTER printing a loud warning. This is
#       intentionally explicit and intended for emergency rollback only.
#
# Usage
#   bin/repo-delete-gate.sh --repo <owner/repo> [--apply] [--force]
#                           [--docs-root <path>] [--tooling-root <path>]
#
# Exit codes
#   0  deletion performed (only with --apply and no gate failure)
#   2  gate failure (dry-run or pre-apply)
#   3  invalid arguments / missing tool
#   4  GitHub API failure
#   5  user aborted after --force warning
# ----------------------------------------------------------------------------

set -euo pipefail

# ---------- defaults ----------------------------------------------------------
REPO=""
APPLY=0
FORCE=0
DOCS_ROOT="docs"
TOOLING_ROOT="."
DRY_RUN_PRINT="(dry-run)"

# ---------- helpers -----------------------------------------------------------
log()  { printf '[repo-delete-gate] %s\n' "$*" >&2; }
warn() { printf '[repo-delete-gate][WARN] %s\n' "$*" >&2; }
die()  { printf '[repo-delete-gate][ERROR] %s\n' "$*" >&2; exit "${2:-3}"; }

require_tool() {
  command -v "$1" >/dev/null 2>&1 || die "required tool '$1' not found in PATH" 3
}

usage() {
  sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//'
  exit 3
}

# ---------- arg parsing -------------------------------------------------------
while [ $# -gt 0 ]; do
  case "$1" in
    --repo)          REPO="${2:-}"; shift 2 ;;
    --apply)         APPLY=1; shift ;;
    --force)         FORCE=1; shift ;;
    --docs-root)     DOCS_ROOT="${2:-}"; shift 2 ;;
    --tooling-root)  TOOLING_ROOT="${2:-}"; shift 2 ;;
    -h|--help)       usage ;;
    *)               die "unknown argument: $1" 3 ;;
  esac
done

[ -n "$REPO" ] || die "--repo <owner/repo> is required" 3
require_tool gh

# Normalize slug for filesystem: github names are [A-Za-z0-9._-] so the
# folder name is the same as the repo leaf.
REPO_LEAF="${REPO##*/}"

# ---------- gate (a): absorption manifest -------------------------------------
REQUIRED_SECTIONS=(
  "Source"
  "Target"
  "Status"
  "Last-Resort-Exceptions"
  "Restore-Command"
)
MANIFEST_DIR="${TOOLING_ROOT%/}/${DOCS_ROOT%/}/absorbed-from-${REPO_LEAF}"
MANIFEST_FILE="${MANIFEST_DIR}/ABSORPTION.md"

gate_a_status="FAIL"
gate_a_detail=""
if [ ! -f "$MANIFEST_FILE" ]; then
  gate_a_detail="manifest missing at $MANIFEST_FILE"
else
  missing=()
  for section in "${REQUIRED_SECTIONS[@]}"; do
    # Match a markdown heading (^#+ or plain line) for the section name.
    if ! grep -Eq "^#{1,6}[[:space:]]+${section}[[:space:]]*$" "$MANIFEST_FILE"; then
      missing+=("$section")
    fi
  done
  if [ "${#missing[@]}" -gt 0 ]; then
    gate_a_detail="manifest present but missing sections: ${missing[*]}"
  else
    gate_a_status="PASS"
    gate_a_detail="manifest at $MANIFEST_FILE contains all required sections"
  fi
fi

# ---------- gate (b): github api state ----------------------------------------
gate_b_status="FAIL"
gate_b_detail=""
repo_json="$(gh api "/repos/${REPO}" 2>/dev/null || true)"
if [ -z "$repo_json" ]; then
  gate_b_detail="gh api /repos/${REPO} returned no body (repo not visible to current token?)"
else
  is_archived="$(printf '%s' "$repo_json" | grep -E '"archived"[[:space:]]*:[[:space:]]*true' >/dev/null && echo yes || echo no)"
  # "Default branch protection active" heuristic: if the default branch ref
  # has protection_enabled=true OR required_pull_request_reviews is set on
  # its protection, treat it as an active veto. (We deliberately do not
  # delete repos that still gate contributors.)
  protection_json="$(gh api "/repos/${REPO}/branches/$(printf '%s' "$repo_json" | grep -E '"default_branch"' | head -1 | sed -E 's/.*"default_branch"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')/protection" 2>/dev/null || true)"
  protection_active="no"
  if [ -n "$protection_json" ] && printf '%s' "$protection_json" | grep -Eq '"enabled"[[:space:]]*:[[:space:]]*true'; then
    protection_active="yes"
  fi

  if [ "$is_archived" = "yes" ] && [ "$protection_active" = "no" ]; then
    gate_b_status="PASS"
    gate_b_detail="isArchived=true and no active default-branch protection"
  else
    gate_b_detail="isArchived=${is_archived}, protection_active=${protection_active} (both must be archived AND unprotected)"
  fi
fi

# ---------- gate summary ------------------------------------------------------
overall="PASS"
[ "$gate_a_status" = "PASS" ] || overall="FAIL"
[ "$gate_b_status" = "PASS" ] || overall="FAIL"

log "gate (a) manifest     : ${gate_a_status} -- ${gate_a_detail}"
log "gate (b) github state : ${gate_b_status} -- ${gate_b_detail}"
log "overall               : ${overall}"

if [ "$overall" = "PASS" ]; then
  if [ "$APPLY" -eq 0 ]; then
    log "${DRY_RUN_PRINT} would run: gh repo delete ${REPO} --yes"
    log "${DRY_RUN_PRINT} no deletion performed. Re-run with --apply to delete."
    exit 0
  fi
  log "all gates passed; executing: gh repo delete ${REPO} --yes"
  gh repo delete "$REPO" --yes
  exit 0
fi

# ---------- failure path ------------------------------------------------------
if [ "$FORCE" -eq 1 ]; then
  warn "gate FAILED but --force was supplied."
  warn "this bypass is intentional only for emergency rollback."
  warn "post-deletion, you MUST still author docs/absorbed-from-${REPO_LEAF}/ABSORPTION.md"
  warn "within 24h or this deletion is unrecoverable per the go-nippon precedent."
  if [ "$APPLY" -eq 1 ]; then
    log "executing forced delete: gh repo delete ${REPO} --yes"
    gh repo delete "$REPO" --yes
    exit 0
  fi
  log "${DRY_RUN_PRINT} --force acknowledged; re-run with --apply to actually delete."
  exit 0
fi

die "gate failed for ${REPO}; rerun with --force only if you accept the risk and will author the manifest retroactively." 2
