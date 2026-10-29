#!/usr/bin/env sh
set -e

BINARY="promptscrape"
INSTALL_DIRS="$HOME/.local/bin /usr/local/bin"

for dir in $INSTALL_DIRS; do
  target="$dir/$BINARY"
  if [ -f "$target" ]; then
    echo "Removing $target"
    rm -f "$target" || sudo rm -f "$target"
  fi
  target="$dir/${BINARY}.exe"
  if [ -f "$target" ]; then
    echo "Removing $target"
    rm -f "$target" || sudo rm -f "$target"
  fi
done

echo "Done"
