#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$(pwd)}"
ARCHIVE="$ROOT/.archive/history-cleanup-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$ARCHIVE"

read -r -p "Confirm archive+remove local .history artifacts for repos in $ROOT? [y/N] " ans
case "$ans" in [Yy]*) ;; *) echo "aborted"; exit 0;; esac

for dir in "$ROOT"/*/; do
  [ -d "$dir" ] || continue
  name="$(basename "$dir")"
  [[ "$name" == .* ]] && continue
  [[ "$name" == *-wtrees* ]] && continue

  if [ -d "$dir/.history" ]; then
    if git -C "$dir" check-ignore -q .history; then
      echo "skip ignored .history in $name"
    else
      mkdir -p "$ARCHIVE/$name"
      mv "$dir/.history" "$ARCHIVE/$name/"
      echo "archived .history -> $ARCHIVE/$name/.history"
    fi
  fi
  rm -f "$dir/.broken_md_refs.txt" "$dir/.build_output.log" || true
done
