#!/usr/bin/env sh
# promptscrape uninstaller.
#
# Removes the promptscrape binary from every known install location.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/KooshaPari/PhenoShared/main/scripts/uninstall-promptscrape.sh | sh
set -eu

BINARY="promptscrape"

die() {
  echo "error: $*" >&2
  exit 1
}

command -v uname >/dev/null 2>&1 || die "uname is required"

OS="$(uname -s | tr '[:upper:]' '[:lower:]')"

DIRS="${HOME}/.local/bin"
if [ "$OS" != "windows" ]; then
  DIRS="${DIRS} /usr/local/bin"
else
  DIRS="${DIRS} ${HOME}/AppData/Local/bin ${HOME}/go/bin"
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
