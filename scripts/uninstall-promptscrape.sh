#!/usr/bin/env sh
# promptscrape uninstaller.
#
# Removes the promptscrape binary from every known install location, or from a
# single directory given with --dir.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/KooshaPari/PhenoShared/main/scripts/uninstall-promptscrape.sh | sh
#   curl -fsSL .../uninstall-promptscrape.sh | sh -s -- --dir /opt/promptscrape/bin
set -eu

BINARY="promptscrape"
ONLY_DIR=""

die() {
  echo "error: $*" >&2
  exit 1
}

while [ $# -gt 0 ]; do
  case "$1" in
    --dir)
      ONLY_DIR="${2:?--dir needs a value}"
      shift 2
      ;;
    --dir=*)
      ONLY_DIR="${1#*=}"
      shift
      ;;
    -h|--help)
      echo "Usage: uninstall-promptscrape.sh [--dir <path>]"
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

command -v uname >/dev/null 2>&1 || die "uname is required"

if [ -n "$ONLY_DIR" ]; then
  DIRS="$ONLY_DIR"
else
  OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
  DIRS="${HOME}/.local/bin"
  if [ "$OS" != "windows" ]; then
    DIRS="${DIRS} /usr/local/bin"
  else
    DIRS="${DIRS} ${HOME}/AppData/Local/bin ${HOME}/go/bin"
  fi
fi

FOUND=0
for dir in $DIRS; do
  for name in "$BINARY" "${BINARY}.exe"; do
    target="${dir}/${name}"
    if [ -f "$target" ]; then
      if rm -f "$target"; then
        echo "Removed ${target}"
        FOUND=1
      else
        echo "error: cannot remove ${target} (try with sudo)" >&2
      fi
    fi
  done
done

if [ "$FOUND" -eq 0 ]; then
  echo "promptscrape was not found in any known install location"
fi

exit 0
