#!/bin/zsh

set -euo pipefail

if (( $# != 1 )); then
  print -u2 -r -- "usage: $0 ROOT"
  exit 64
fi

scan_root=$1
[[ -d "$scan_root" ]] || {
  print -u2 -r -- "not a directory: $scan_root"
  exit 66
}

scan_root_abs=${scan_root:A}
working_dir_abs=${PWD:A}
if [[ "$scan_root_abs" == / || "$working_dir_abs" == "$scan_root_abs" || \
  "$working_dir_abs" == "$scan_root_abs"/* ]]; then
  print -u2 -r -- "refusing to write a manifest inside the scanned root"
  exit 73
fi

output_dir="$PWD/manifests"
mkdir -p -- "$output_dir"
output_dir_abs=${output_dir:A}
if [[ "$scan_root_abs" == / || "$output_dir_abs" == "$scan_root_abs" || \
  "$output_dir_abs" == "$scan_root_abs"/* ]]; then
  print -u2 -r -- "refusing to write a manifest inside the scanned root"
  exit 73
fi
output_dir=$output_dir_abs
output="$output_dir/home_entries.tsv"

rows_tmp=$(mktemp "${TMPDIR:-/tmp}/home-manifest.rows.XXXXXX")
sorted_tmp=$(mktemp "${TMPDIR:-/tmp}/home-manifest.sorted.XXXXXX")
output_tmp=$(mktemp "$output_dir/.home_entries.tsv.XXXXXX")
trap 'rm -f -- "$rows_tmp" "$sorted_tmp" "$output_tmp"' EXIT

while IFS= read -r -d '' entry_path; do
  path_b64=$(print -rn -- "$entry_path" | base64 | tr -d '\n')
  digest=$(print -rn -- "$entry_path" | shasum -a 256)
  ledger_id="home-${digest%% *}"
  display_path=$(printf '%q' "$entry_path")

  if [[ -L "$entry_path" ]]; then
    entry_type=symlink
  elif [[ -d "$entry_path" ]]; then
    entry_type=directory
  elif [[ -f "$entry_path" ]]; then
    entry_type=file
  else
    entry_type=other
  fi

  basename=${entry_path:t}
  if [[ "$basename" == .* ]]; then
    hidden=true
  else
    hidden=false
  fi

  size_bytes=$(stat -f '%z' -- "$entry_path")
  modified_epoch=$(stat -f '%m' -- "$entry_path")

  print -r -- \
    "$ledger_id"$'\t'"$path_b64"$'\t'"$display_path"$'\t'"$entry_type"$'\t'"$hidden"$'\t'\
"$size_bytes"$'\t'"$modified_epoch"\
$'\tUNKNOWN\tUNKNOWN\tUNKNOWN\tUNKNOWN\tUNKNOWN\tUNKNOWN\tPENDING'\
$'\tPENDING\tPENDING\tPENDING\tPENDING\t' >> "$rows_tmp"
done < <(find "$scan_root_abs" -mindepth 1 -maxdepth 1 -print0)

LC_ALL=C sort -t $'\t' -k2,2 "$rows_tmp" > "$sorted_tmp"
print -r -- \
  $'ledger_id\tpath_b64\tdisplay_path\tentry_type\thidden\tsize_bytes\tmodified_epoch'\
$'\tcategory\tgit_kind\tgit_head\tgit_common_dir\tupstream_state\trisk\tdisposition'\
$'\tdestination\tbackup_ref\tverification\tstatus\tnotes' > "$output_tmp"
cat "$sorted_tmp" >> "$output_tmp"
mv -f -- "$output_tmp" "$output"
