#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 crates/<crate-name>" >&2
  exit 2
fi

crate_dir="${1%/}"
manifest="$crate_dir/Cargo.toml"
lib_rs="$crate_dir/src/lib.rs"

if [[ ! -f "$manifest" ]]; then
  echo "missing manifest: $manifest" >&2
  exit 1
fi

name="$(awk -F '"' '/^name = / { print $2; exit }' "$manifest")"
license="$(awk -F '"' '/^license = / { print $2; exit }' "$manifest")"
if [[ -z "$license" ]] && grep -q '^license.workspace = true' "$manifest"; then
  license="$(awk -F '"' '/^license = / { print $2; exit }' Cargo.toml)"
fi

msrv="$(awk -F '"' '/^rust-version = / { print $2; exit }' "$manifest")"
if [[ -z "$msrv" ]] && grep -q '^rust-version.workspace = true' "$manifest"; then
  msrv="$(awk -F '"' '/^rust-version = / { print $2; exit }' Cargo.toml)"
fi

features="$(awk '/^\[features\]/{flag=1; next} /^\[/{flag=0} flag && /^[A-Za-z0-9_-]+[[:space:]]*=/{print $1}' "$manifest" | paste -sd, -)"
api_lines=""
if [[ -f "$lib_rs" ]]; then
  api_lines="$(awk '
    /^pub mod / { gsub(/[;{]/, "", $3); print "- `" $3 "` - TODO: describe module." }
    /^pub use / { line=$0; sub(/^pub use /, "", line); sub(/;$/, "", line); print "- `" line "` - TODO: describe export." }
    /^pub (struct|enum|trait|type|fn) / { name=$3; sub(/\(.*/, "", name); print "- `" name "` - TODO: describe item." }
  ' "$lib_rs")"
fi

readme="$crate_dir/README.md"
{
  printf '# %s\n\n' "$name"
  printf '![MSRV](https://img.shields.io/badge/MSRV-%s-blue)\n' "${msrv:-1.75}"
  printf '![License](https://img.shields.io/badge/license-%s-blue)\n\n' "${license:-MIT}" | sed 's/ /%20/g'
  printf 'TODO: Add a concise crate summary.\n\n'
  printf '## Public API Index\n\n'
  if [[ -n "$api_lines" ]]; then
    printf '%s\n' "$api_lines"
  else
    printf -- '- TODO: Add public API items.\n'
  fi
  printf '\n## Build\n\n'
  printf '```bash\n'
  printf 'cargo build -p %s\n' "$name"
  if [[ -n "$features" ]]; then
    printf 'cargo build -p %s --features %s\n' "$name" "$features"
  fi
  printf '```\n'
} > "$readme"

echo "wrote $readme"

