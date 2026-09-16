#!/usr/bin/env bash
# Reversible installer for the tracked Codex repository-deletion PreToolUse guard.
set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SOURCE_GUARD="$SCRIPT_DIR/codex-repo-delete-guard.sh"
readonly TEST_CORPUS="$SCRIPT_DIR/../tests/test_codex_repo_delete_guard.py"
readonly EXPECTED_SOURCE_SHA256="0ba0fd1eb0e4189c363bad31ee1d84aa51f7d8064508548802ef8525c2f1189b"
readonly EXPECTED_SOURCE_MODE="755"
readonly AWK_FIRST_FIELD='{print $1}'

TARGET_ROOT="${HOME:?HOME must be set}"
ACTION="dry-run"
ROLLBACK_MANIFEST=""

fail() {
  printf 'codex guard installer: %s\n' "$*" >&2
  exit 1
}

usage() {
  printf '%s\n' "usage: $0 [--target-root ABSOLUTE_ROOT] [--install | --rollback MANIFEST]"
}

validate_parent() {
  [[ "$TARGET_ROOT" == /* ]] || fail "target root must be absolute"
  TARGET_PARENT="$TARGET_ROOT/.codex/bin"
  TARGET="$TARGET_PARENT/codex-repo-delete-guard.sh"
  [[ -d "$TARGET_PARENT" && ! -L "$TARGET_PARENT" ]] || fail "target parent is not a real directory: $TARGET_PARENT"
  [[ -w "$TARGET_PARENT" ]] || fail "target parent is not writable: $TARGET_PARENT"
  [[ ! -L "$TARGET" ]] || fail "refusing symlink target: $TARGET"
  [[ ! -e "$TARGET" || -f "$TARGET" ]] || fail "target must be a regular file: $TARGET"
}

source_sha256() {
  /usr/bin/shasum -a 256 "$SOURCE_GUARD" | /usr/bin/awk "$AWK_FIRST_FIELD"
}

validate_source() {
  [[ -f "$SOURCE_GUARD" && ! -L "$SOURCE_GUARD" ]] || fail "source guard is not a regular file"
  [[ -f "$TEST_CORPUS" ]] || fail "portable guard corpus is missing"
  local actual_sha actual_mode
  actual_sha="$(source_sha256)"
  actual_mode="$(/usr/bin/stat -f '%Lp' "$SOURCE_GUARD")"
  [[ "$actual_sha" == "$EXPECTED_SOURCE_SHA256" ]] || fail "source SHA-256 mismatch"
  [[ "$actual_mode" == "$EXPECTED_SOURCE_MODE" ]] || fail "source mode mismatch"
  command -v python3 >/dev/null 2>&1 || fail "python3 is required to validate the installed guard"
}

restore_original() {
  local original_existed="$1" backup="$2" temporary
  if [[ "$original_existed" == "1" ]]; then
    [[ -f "$backup" && ! -L "$backup" ]] || fail "recorded backup is unavailable"
    temporary="$(/usr/bin/mktemp "$TARGET_PARENT/.codex-repo-delete-guard.restore.XXXXXX")"
    /bin/cp -p "$backup" "$temporary"
    /bin/mv -f "$temporary" "$TARGET"
  else
    /bin/rm -f "$TARGET"
  fi
}

install() {
  validate_source
  validate_parent

  local timestamp original_existed=0 backup="" backup_sha256="" backup_mode="" temporary manifest_temporary manifest
  timestamp="$(/bin/date -u +%Y%m%dT%H%M%SZ)-$$"
  manifest="$TARGET.install-$timestamp.manifest"

  if [[ -e "$TARGET" ]]; then
    original_existed=1
    backup="$TARGET.backup-$timestamp"
    /bin/cp -p "$TARGET" "$backup"
    backup_sha256="$(/usr/bin/shasum -a 256 "$backup" | /usr/bin/awk "$AWK_FIRST_FIELD")"
    backup_mode="$(/usr/bin/stat -f '%Lp' "$backup")"
  fi

  temporary="$(/usr/bin/mktemp "$TARGET_PARENT/.codex-repo-delete-guard.install.XXXXXX")"
  /bin/cp "$SOURCE_GUARD" "$temporary"
  /bin/chmod 0755 "$temporary"
  /bin/bash -n "$temporary"
  /bin/mv -f "$temporary" "$TARGET"

  if ! /bin/bash -n "$TARGET" || ! CODEX_REPO_DELETE_GUARD="$TARGET" python3 "$TEST_CORPUS"; then
    restore_original "$original_existed" "$backup"
    fail "installed guard failed validation and was restored"
  fi

  manifest_temporary="$(/usr/bin/mktemp "$TARGET_PARENT/.codex-repo-delete-guard.manifest.XXXXXX")"
  {
    printf 'format=codex-repo-delete-guard-install-v1\n'
    printf 'target=%s\n' "$TARGET"
    printf 'backup=%s\n' "$backup"
    printf 'backup_sha256=%s\n' "$backup_sha256"
    printf 'backup_mode=%s\n' "$backup_mode"
    printf 'original_existed=%s\n' "$original_existed"
    printf 'installed_sha256=%s\n' "$EXPECTED_SOURCE_SHA256"
    printf 'installed_mode=0755\n'
  } >"$manifest_temporary"
  /bin/chmod 0600 "$manifest_temporary"
  /bin/mv -f "$manifest_temporary" "$manifest"
  printf 'INSTALLED=%s\nMANIFEST=%s\n' "$TARGET" "$manifest"
}

rollback() {
  [[ -f "$ROLLBACK_MANIFEST" && ! -L "$ROLLBACK_MANIFEST" ]] || fail "manifest is not a regular file"

  local format="" recorded_target="" backup="" backup_sha256="" backup_mode="" original_existed="" installed_sha="" installed_mode=""
  local key value
  while IFS='=' read -r key value; do
    case "$key" in
      format) format="$value" ;;
      target) recorded_target="$value" ;;
      backup) backup="$value" ;;
      backup_sha256) backup_sha256="$value" ;;
      backup_mode) backup_mode="$value" ;;
      original_existed) original_existed="$value" ;;
      installed_sha256) installed_sha="$value" ;;
      installed_mode) installed_mode="$value" ;;
      *) fail "manifest has an unsupported field" ;;
    esac
  done <"$ROLLBACK_MANIFEST"

  [[ "$format" == "codex-repo-delete-guard-install-v1" ]] || fail "unsupported manifest format"
  [[ "$recorded_target" == /* && "$recorded_target" == */.codex/bin/codex-repo-delete-guard.sh ]] || fail "manifest target is not a Codex guard"
  [[ "$original_existed" == "0" || "$original_existed" == "1" ]] || fail "manifest original state is invalid"
  [[ "$installed_sha" =~ ^[0-9a-f]{64}$ && "$installed_mode" == "0755" ]] || fail "manifest install metadata is invalid"

  TARGET="$recorded_target"
  TARGET_PARENT="$(dirname "$TARGET")"
  [[ -d "$TARGET_PARENT" && ! -L "$TARGET_PARENT" ]] || fail "recorded target parent is not a real directory"
  [[ "$(dirname "$ROLLBACK_MANIFEST")" == "$TARGET_PARENT" ]] || fail "manifest is not beside its recorded target"
  [[ "$(basename "$ROLLBACK_MANIFEST")" == "$(basename "$TARGET").install-"*.manifest ]] || fail "manifest name is invalid"
  [[ ! -L "$TARGET" && -f "$TARGET" ]] || fail "recorded target is not a regular file"
  [[ "$(/usr/bin/shasum -a 256 "$TARGET" | /usr/bin/awk "$AWK_FIRST_FIELD")" == "$installed_sha" ]] || fail "recorded target changed since install"
  if [[ "$original_existed" == "1" ]]; then
    [[ "$backup" == "$TARGET".backup-* && -f "$backup" && ! -L "$backup" ]] || fail "recorded backup is invalid"
    [[ "$backup_sha256" =~ ^[0-9a-f]{64}$ && "$backup_mode" =~ ^[0-7]{3,4}$ ]] || fail "recorded backup metadata is invalid"
    [[ "$(/usr/bin/shasum -a 256 "$backup" | /usr/bin/awk "$AWK_FIRST_FIELD")" == "$backup_sha256" ]] || fail "recorded backup changed since install"
    [[ "$(/usr/bin/stat -f '%Lp' "$backup")" == "$backup_mode" ]] || fail "recorded backup mode changed since install"
  else
    [[ -z "$backup" && -z "$backup_sha256" && -z "$backup_mode" ]] || fail "manifest unexpectedly records a backup"
  fi

  restore_original "$original_existed" "$backup"
  printf 'ROLLED_BACK=%s\n' "$TARGET"
}

while (($#)); do
  case "$1" in
    --target-root)
      (($# >= 2)) || fail "--target-root requires a value"
      TARGET_ROOT="$2"
      shift 2
      ;;
    --install)
      [[ "$ACTION" == "dry-run" ]] || fail "choose one action"
      ACTION="install"
      shift
      ;;
    --rollback)
      (($# >= 2)) || fail "--rollback requires a manifest path"
      [[ "$ACTION" == "dry-run" ]] || fail "choose one action"
      ACTION="rollback"
      ROLLBACK_MANIFEST="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      usage >&2
      fail "unknown argument: $1"
      ;;
  esac
done

case "$ACTION" in
  dry-run)
    validate_source
    validate_parent
    printf 'DRY-RUN: would install %s to %s\n' "$SOURCE_GUARD" "$TARGET"
    ;;
  install)
    install
    ;;
  rollback)
    rollback
    ;;
  *)
    fail "unsupported action: $ACTION"
    ;;
esac
