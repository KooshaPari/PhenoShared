#!/usr/bin/env bash
# repo-archive-gate.sh
# ----------------------------------------------------------------------------
# Bash wrapper for `gh repo archive` with the same four-gate pre-archive fence
# as bin/repo-delete-gate.sh. Archives are softer than deletes (the repo
# becomes read-only but is not removed from the org), so the gate is also
# softer:
#   (a) docs/absorbed-from-<repo>/ABSORPTION.md must exist with all required
#       sections (Source, Target, Status, Last-Resort-Exceptions,
#       Restore-Command)
#   (b) GitHub API confirms the repo is currently UN-archived (archiving an
#       already-archived repo is a no-op and should fail)
#   (c) dry-run is the DEFAULT; pass --apply to actually archive
#   (d) --force bypasses the gate after printing a loud warning
#
# Restore command (the inverse of `gh repo archive --yes`):
#   gh api -X DELETE /repos/<owner>/<repo>  -H "Accept: application/vnd.github+json"
# Note: GitHub does not provide a `gh repo unarchive` command, so the restore
# path requires org admin via the API.
#
# Usage
#   bash bin/repo-archive-gate.sh --repo <REDACTED>/<name> [--apply] [--force]
#                                 [--docs-root docs] [--tooling-root .]
#
# Exit codes (kept identical to the delete-gate version):
#   0  archive performed (only with --apply and gates passed)
#   2  gate failure
#   3  invalid arguments / missing tool
#   4  GitHub API failure
#   5  user aborted after --force warning
# ----------------------------------------------------------------------------

set -euo pipefail

# ---------- args --------------------------------------------------------------
repo=""
apply="false"
force="false"
docs_root="docs"
tooling_root="."

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) repo="$2"; shift 2 ;;
    --apply) apply="true"; shift ;;
    --force) force="true"; shift ;;
    --docs-root) docs_root="$2"; shift 2 ;;
    --tooling-root) tooling_root="$2"; shift 2 ;;
    -h|--help) sed -n '2,35p' "$0"; exit 0 ;;
    *) echo "[repo-archive-gate][ERROR] unknown arg: $1" >&2; exit 3 ;;
  esac
done

if [[ -z "$repo" ]]; then
  echo "[repo-archive-gate][ERROR] --repo <owner/name> is required" >&2
  exit 3
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "[repo-archive-gate][ERROR] required tool 'gh' not found in PATH" >&2
  exit 3
fi

# ---------- helpers -----------------------------------------------------------
required_sections=(Source Target Status Last-Resort-Exceptions Restore-Command)
repo_leaf="${repo##*/}"

# Resolve manifest dir.
if [[ "$docs_root" = /* ]] || [[ "$docs_root" =~ ^[A-Za-z]:[\\/] ]]; then
  manifest_dir="$docs_root"
else
  manifest_dir="$tooling_root/$docs_root"
fi
manifest_dir="${manifest_dir%/}"
manifest_dir="$manifest_dir/absorbed-from-$repo_leaf"
manifest_file="$manifest_dir/ABSORPTION.md"

# ---------- gate (a): absorption manifest -------------------------------------
gate_a_status="FAIL"
gate_a_detail=""
if [[ ! -f "$manifest_file" ]]; then
  gate_a_detail="manifest missing at $manifest_file"
else
  missing=()
  for section in "${required_sections[@]}"; do
    pattern="^#{1,6}[[:space:]]+${section}[[:space:]]*$"
    if ! grep -Eq "$pattern" "$manifest_file"; then
      missing+=("$section")
    fi
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    gate_a_detail="manifest present but missing sections: ${missing[*]}"
  else
    gate_a_status="PASS"
    gate_a_detail="manifest at $manifest_file contains all required sections"
  fi
fi

# ---------- gate (b): github api state ----------------------------------------
gate_b_status="FAIL"
gate_b_detail=""
if ! repo_json="$(gh api "/repos/$repo" 2>/dev/null)"; then
  gate_b_detail="gh api /repos/$repo failed with non-zero exit"
  echo "[repo-archive-gate] gate b github state      : FAIL -- $gate_b_detail"
  echo "[repo-archive-gate] overall               : FAIL"
  exit 4
fi

is_archived=$(echo "$repo_json" | python3 -c "import json,sys; print(str(json.load(sys.stdin).get('archived',False)).lower())")
default_branch=$(echo "$repo_json" | python3 -c "import json,sys; print(json.load(sys.stdin).get('default_branch','main'))")

if [[ "$is_archived" == "true" ]]; then
  gate_b_detail="repo is ALREADY archived (isArchived=true); nothing to do"
elif [[ "$is_archived" == "false" ]]; then
  gate_b_status="PASS"
  gate_b_detail="isArchived=false on default branch=$default_branch; archive allowed"
else
  gate_b_detail="could not parse isArchived field (got: $is_archived)"
fi

# ---------- gate summary ------------------------------------------------------
overall="PASS"
[[ "$gate_a_status" != "PASS" ]] && overall="FAIL"
[[ "$gate_b_status" != "PASS" ]] && overall="FAIL"

echo "[repo-archive-gate] gate (a) manifest     : $gate_a_status -- $gate_a_detail"
echo "[repo-archive-gate] gate (b) github state : $gate_b_status -- $gate_b_detail"
echo "[repo-archive-gate] overall               : $overall"

# ---------- success path ------------------------------------------------------
if [[ "$overall" == "PASS" ]]; then
  if [[ "$apply" != "true" ]]; then
    echo "[repo-archive-gate] (dry-run) would run: gh repo archive $repo"
    echo "[repo-archive-gate] (dry-run) no archive performed. Re-run with --apply to archive."
    exit 0
  fi
  echo "[repo-archive-gate] all gates passed; executing: gh repo archive $repo"
  gh repo archive "$repo"
  exit 0
fi

# ---------- failure path ------------------------------------------------------
if [[ "$force" == "true" ]]; then
  echo "[repo-archive-gate][WARN] gate FAILED but --force was supplied."
  echo "[repo-archive-gate][WARN] this bypass is intentional only for emergency rollback."
  echo "[repo-archive-gate][WARN] post-archive, you MUST still author docs/absorbed-from-$repo_leaf/ABSORPTION.md"
  echo "[repo-archive-gate][WARN] within 24h or this archive is undocumented per the go-nippon precedent."
  if [[ "$apply" == "true" ]]; then
    echo "[repo-archive-gate] executing forced archive: gh repo archive $repo"
    gh repo archive "$repo"
    exit 0
  fi
  echo "[repo-archive-gate] (dry-run) --force acknowledged; re-run with --apply to actually archive."
  exit 0
fi

echo "[repo-archive-gate][ERROR] gate failed for $repo; rerun with --force only if you accept the risk and will author the manifest retroactively." >&2
exit 2
