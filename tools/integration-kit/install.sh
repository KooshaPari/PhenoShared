#!/usr/bin/env bash
# install.sh — install the shared integration kit into a target repo
#
# Usage: install.sh [--target DIR] [--source DIR] [--components LIST] [--dry-run] [--force]
#
# Components: workflows, lefthook, mcp, scripts, all
#
# Defaults:
#   --target   current working directory
#   --source   parent directory of this script (assumed to be the kit root)
#   --components all
#
# --dry-run prints what would happen and never touches the filesystem.
# It also does NOT run post-install verification, since the verification step
# would otherwise report missing files that --dry-run deliberately did not create.
#
# This script never touches the target's existing files unless --force is given
# or the file is being newly created. Conflicting installs are reported and
# skipped (run again with --force to overwrite).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Default source = parent of tools/integration-kit (the repo root containing .github/ and tools/)
SOURCE_DIR_DEFAULT="$(cd "$SCRIPT_DIR/../.." && pwd)"

TARGET_DIR=""
SOURCE_DIR="$SOURCE_DIR_DEFAULT"
COMPONENTS="all"
DRY_RUN="false"
FORCE="false"

usage() {
  cat <<EOF
Usage: $0 [options]

Options:
  --target DIR         Target repo directory (default: cwd)
  --source DIR         Source kit directory (default: \$SOURCE_DIR_DEFAULT)
  --components LIST    Comma-separated: workflows,lefthook,mcp,scripts (default: all)
  --dry-run            Print what would happen; do not modify any files
  --force              Overwrite existing files in target
  -h, --help           Show this help

Examples:
  $0 --target /path/to/other-repo --components workflows,lefthook
  $0 --target . --components mcp --dry-run
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --target)  TARGET_DIR="$2"; shift 2 ;;
      --source)  SOURCE_DIR="$2"; shift 2 ;;
      --components) COMPONENTS="$2"; shift 2 ;;
      --dry-run) DRY_RUN="true"; shift ;;
      --force) FORCE="true"; shift ;;
      -h|--help) usage; exit 0 ;;
      *) echo "Unknown arg: $1" >&2; usage >&2; exit 2 ;;
    esac
  done

  if [[ -z "$TARGET_DIR" ]]; then
    TARGET_DIR="$(pwd)"
  fi

  # Normalize components: trim whitespace, drop empty entries, lower-case.
  # Allows the user to pass "workflows, lefthook" or "workflows , lefthook".
  COMPONENTS="$(printf '%s' "$COMPONENTS" | tr '[:upper:]' '[:lower:]' | tr -s '[:space:]' ',' | sed 's/^,//;s/,$//;s/,,/,/g')"
}

assert_dirs() {
  if [[ ! -d "$SOURCE_DIR" ]]; then
    echo "ERROR: --source $SOURCE_DIR does not exist or is not a directory" >&2
    exit 2
  fi
  if [[ ! -d "$TARGET_DIR" ]]; then
    echo "ERROR: --target $TARGET_DIR does not exist" >&2
    exit 2
  fi
  if [[ ! -d "$SOURCE_DIR/.github/workflows" ]]; then
    echo "ERROR: --source $SOURCE_DIR does not contain .github/workflows with reusable-*.yml — is it a kit root?" >&2
    exit 2
  fi
  # Refuse to install into a system directory. realpath resolves any
  # ../../ traversal so the check catches paths that resolve into /etc, /usr,
  # /System, etc. even when spelled as a relative path.
  local abs_target abs_source
  abs_target="$(cd "$TARGET_DIR" && pwd -P)"
  abs_source="$(cd "$SOURCE_DIR" && pwd -P)"
  case "$abs_target" in
    /|/bin|/sbin|/usr|/etc|/var|/boot|/System|/Library|/private/etc)
      echo "ERROR: refusing to install into system directory $abs_target" >&2
      exit 2
      ;;
  esac
  TARGET_DIR="$abs_target"
  SOURCE_DIR="$abs_source"
}

want() {
  # want <component>  → returns 0 (true) if component is requested
  local c="$1"
  if [[ "$COMPONENTS" == "all" ]]; then return 0; fi
  if [[ ",$COMPONENTS," == *",$c,"* ]]; then return 0; fi
  return 1
}

# copy_file <src> <dst> <rel>
# rel is the human-readable path used in the install log.
copy_file() {
  local src="$1" dst="$2" rel="$3"
  if [[ -e "$dst" && "$FORCE" != "true" ]]; then
    echo "  SKIP (exists): $rel — re-run with --force to overwrite"
    return 0
  fi
  # Reject destination paths that traverse a symlink. Without this check, a
  # prepared symlink under --target (e.g. .github/workflows/lefthook.yml ->
  # /etc/anything) would let a forced install write outside the target repo.
  if [[ -L "$dst" ]] || [[ -e "$dst" && -L "$(dirname "$dst")" ]]; then
    echo "  REFUSE (symlink): $rel — refusing to overwrite through a symbolic link" >&2
    return 3
  fi
  if [[ "$DRY_RUN" == "true" ]]; then
    echo "  WOULD COPY: $rel"
    return 0
  fi
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
  echo "  COPIED: $rel"
}

install_workflows() {
  echo "[install] workflows → $TARGET_DIR/.github/workflows/ (reusable-*.yml)"
  # No mkdir in --dry-run mode: copy_file is the only place that creates dirs.
  for f in "$SOURCE_DIR/.github/workflows/reusable-"*.yml; do
    [[ -e "$f" ]] || continue
    fname="$(basename "$f")"
    copy_file "$f" "$TARGET_DIR/.github/workflows/$fname" ".github/workflows/$fname"
  done
}

install_lefthook() {
  echo "[install] lefthook → $TARGET_DIR/lefthook.yml"
  copy_file "$SOURCE_DIR/tools/integration-kit/lefthook.yml" "$TARGET_DIR/lefthook.yml" "lefthook.yml"
}

install_mcp() {
  echo "[install] mcp hooks → $TARGET_DIR/.mcp-hooks.json"
  copy_file "$SOURCE_DIR/tools/integration-kit/mcp-hooks.json" "$TARGET_DIR/.mcp-hooks.json" ".mcp-hooks.json"
}

install_scripts() {
  echo "[install] scripts → $TARGET_DIR/tools/integration-kit/"
  # When --source points to a different kit root, prefer that kit's installer
  # so the installed version matches the rest of the bundle. Otherwise, copy
  # the running script (the canonical installer for this checkout).
  local installer_src="$SCRIPT_DIR/install.sh"
  if [[ -n "$SOURCE_DIR" && -e "$SOURCE_DIR/tools/integration-kit/install.sh" ]]; then
    installer_src="$SOURCE_DIR/tools/integration-kit/install.sh"
  fi
  copy_file "$installer_src" "$TARGET_DIR/tools/integration-kit/install.sh" "tools/integration-kit/install.sh"
  if [[ "$DRY_RUN" == "true" ]]; then
    return 0
  fi
  # Only chmod if we actually copied the file (or it exists and --force was used).
  if [[ -x "$TARGET_DIR/tools/integration-kit/install.sh" ]]; then
    : # already executable, no-op
  else
    chmod +x "$TARGET_DIR/tools/integration-kit/install.sh"
  fi
}

post_install_check() {
  echo ""
  echo "[install] post-install verification:"
  local ok=1
  if want workflows; then
    for f in reusable-lint.yml reusable-test.yml reusable-release.yml; do
      if [[ -f "$TARGET_DIR/.github/workflows/$f" ]]; then
        echo "  ✓ .github/workflows/$f present"
      else
        echo "  ✗ .github/workflows/$f MISSING"
        ok=0
      fi
    done
  fi
  if want lefthook; then
    if [[ -f "$TARGET_DIR/lefthook.yml" ]]; then
      echo "  ✓ lefthook.yml present"
    else
      echo "  ✗ lefthook.yml MISSING"
      ok=0
    fi
  fi
  if want mcp; then
    if [[ -f "$TARGET_DIR/.mcp-hooks.json" ]]; then
      if python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$TARGET_DIR/.mcp-hooks.json" 2>/dev/null; then
        echo "  ✓ .mcp-hooks.json present and valid JSON"
      else
        echo "  ✗ .mcp-hooks.json present but INVALID JSON"
        ok=0
      fi
    else
      echo "  ✗ .mcp-hooks.json MISSING"
      ok=0
    fi
  fi
  if want scripts; then
    if [[ -x "$TARGET_DIR/tools/integration-kit/install.sh" ]]; then
      echo "  ✓ tools/integration-kit/install.sh present and executable"
    else
      echo "  ✗ tools/integration-kit/install.sh MISSING or not executable"
      ok=0
    fi
  fi
  if [[ $ok -eq 0 ]]; then
    echo ""
    echo "[install] some components are missing — review the output above."
    return 1
  fi
  echo ""
  echo "[install] DONE. Next steps:"
  echo "  - In the target repo, call a reusable workflow from your main workflow:"
  echo "      uses: <owner>/<repo>/.github/workflows/reusable-lint.yml@<ref>"
  echo "  - If you installed lefthook, run: lefthook install"
  echo "  - If you installed MCP hooks, copy .mcp-hooks.json into your harness config dir"
  echo "    (see the _comment_install_paths field for paths per harness)."
  return 0
}

main() {
  parse_args "$@"
  assert_dirs

  echo "install.sh configuration:"
  echo "  source:      $SOURCE_DIR"
  echo "  target:      $TARGET_DIR"
  echo "  components:  $COMPONENTS"
  echo "  dry-run:     $DRY_RUN"
  echo "  force:       $FORCE"
  echo ""

  if want workflows; then install_workflows; fi
  if want lefthook; then install_lefthook; fi
  if want mcp; then install_mcp; fi
  if want scripts; then install_scripts; fi

  # --dry-run must NOT verify files it did not copy. Skipping the check is
  # the simplest correct behavior; the WOULD COPY log line is the verification.
  if [[ "$DRY_RUN" == "true" ]]; then
    echo ""
    echo "[install] dry-run complete. No files were modified."
    return 0
  fi

  post_install_check
}

main "$@"
