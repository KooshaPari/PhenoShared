#!/bin/zsh

set -euo pipefail

repo_root=${0:A:h:h}
generator="$repo_root/tooling/build_home_manifest.zsh"
tmp_dir=$(mktemp -d)
tmp_dir=${tmp_dir:A}
trap 'rm -rf -- "$tmp_dir"' EXIT

fail() {
  print -u2 -r -- "FAIL: $*"
  exit 1
}

fixture="$tmp_dir/scanned root"
work_dir="$tmp_dir/work"
mkdir -p -- "$fixture/nested" "$work_dir/manifests"

names=(
  plain
  'with space'
  $'with\ttab'
  $'with\nnewline'
  'percent%name'
  'shell;$(touch HACKED)&*?[x]'
  .hidden
)
for name in "${names[@]}"; do
  : > "$fixture/$name"
done
: > "$fixture/nested/not-an-immediate-child"
ln -s -- plain "$fixture/link to plain"

(
  cd -- "$work_dir"
  zsh "$generator" "$fixture"
)

manifest="$work_dir/manifests/home_entries.tsv"
[[ -f "$manifest" ]] || fail "manifest was not created"
[[ ! -e "$work_dir/HACKED" ]] || fail "a filename was evaluated as shell code"

expected_count=$(( ${#names[@]} + 2 ))
actual_count=$(( $(wc -l < "$manifest") - 1 ))
(( actual_count == expected_count )) || fail "expected $expected_count entries, got $actual_count"

typeset -A seen_paths seen_ids
previous_b64=''
while IFS=$'\t' read -r ledger_id path_b64 display_path entry_type hidden size_bytes \
    modified_epoch category git_kind git_head git_common_dir upstream_state risk disposition \
    destination backup_ref verification row_status notes; do
  [[ "$ledger_id" =~ '^home-[0-9a-f]{64}$' ]] || fail "invalid ledger id: $ledger_id"
  [[ -z ${seen_ids[$ledger_id]-} ]] || fail "duplicate ledger id: $ledger_id"
  seen_ids[$ledger_id]=1

  decoded=$(print -rn -- "$path_b64" | base64 -D)
  expected_digest=$(print -rn -- "$decoded" | shasum -a 256)
  [[ "$ledger_id" == "home-${expected_digest%% *}" ]] || fail "ledger id is not path-derived"
  [[ -z ${seen_paths[$decoded]-} ]] || fail "duplicate decoded path: $decoded"
  seen_paths[$decoded]=1
  [[ "$decoded" == "$fixture"/* ]] || fail "decoded path is outside fixture: $decoded"
  [[ "${decoded#$fixture/}" != */* ]] || fail "nested path was inventoried: $decoded"
  [[ "$display_path" != *$'\t'* && "$display_path" != *$'\n'* ]] || \
    fail "display path is not TSV-safe"
  [[ "$entry_type" == file || "$entry_type" == directory || "$entry_type" == symlink || \
    "$entry_type" == other ]] || fail "invalid entry type: $entry_type"
  [[ "$hidden" == true || "$hidden" == false ]] || fail "invalid hidden value: $hidden"
  [[ "$size_bytes" == <-> ]] || fail "invalid size: $size_bytes"
  [[ "$modified_epoch" == <-> ]] || fail "invalid mtime: $modified_epoch"
  [[ "$category" == UNKNOWN && "$git_kind" == UNKNOWN && "$git_head" == UNKNOWN && \
    "$git_common_dir" == UNKNOWN && "$upstream_state" == UNKNOWN && "$risk" == UNKNOWN && \
    "$disposition" == PENDING ]] || fail "classification fields were pre-populated"
  [[ -z "$previous_b64" || "$previous_b64" < "$path_b64" ]] || fail "paths are not sorted"
  previous_b64=$path_b64
done < <(tail -n +2 "$manifest")

(( ${#seen_paths} == expected_count )) || fail "decoded path count does not match"
for name in "${names[@]}" nested 'link to plain'; do
  [[ -n ${seen_paths[$fixture/$name]-} ]] || fail "missing weird path: $name"
done
[[ -z ${seen_paths[$fixture/nested/not-an-immediate-child]-} ]] || fail "nested child included"

cp -- "$manifest" "$tmp_dir/first-manifest.tsv"
(
  cd -- "$work_dir"
  zsh "$generator" "$fixture"
)
cmp -s -- "$tmp_dir/first-manifest.tsv" "$manifest" || fail "repeated output is not stable"

for cwd_kind in root descendant; do
  guarded_root="$tmp_dir/guarded-$cwd_kind"
  mkdir -p -- "$guarded_root/child"
  if [[ "$cwd_kind" == root ]]; then
    guarded_cwd=$guarded_root
  else
    guarded_cwd="$guarded_root/child"
  fi

  if (cd -- "$guarded_cwd" && zsh "$generator" "$guarded_root") >/dev/null 2>&1; then
    fail "generator accepted $cwd_kind CWD inside the scanned root"
  fi
  [[ ! -e "$guarded_cwd/manifests" ]] || fail "generator modified scanned root from $cwd_kind CWD"
done

symlink_scan_root="$tmp_dir/symlink-output-root"
symlink_work_dir="$tmp_dir/symlink-output-work"
symlink_target="$symlink_scan_root/output-target"
mkdir -p -- "$symlink_target" "$symlink_work_dir"
ln -s -- "$symlink_target" "$symlink_work_dir/manifests"
if (cd -- "$symlink_work_dir" && zsh "$generator" "$symlink_scan_root") >/dev/null 2>&1; then
  fail "generator accepted an output symlink into the scanned root"
fi
[[ -L "$symlink_work_dir/manifests" ]] || fail "generator replaced the unsafe output symlink"
[[ -z $(find "$symlink_target" -mindepth 1 -print -quit) ]] || \
  fail "generator followed the unsafe output symlink"

identity_root="$tmp_dir/identity-source"
identity_link="$tmp_dir/identity-link"
mkdir -p -- "$identity_root"
: > "$identity_root/plain"
ln -s -- "$identity_root" "$identity_link"
for root_kind in absolute relative symlink; do
  identity_work="$tmp_dir/identity-work-$root_kind"
  mkdir -p -- "$identity_work"
  case "$root_kind" in
    absolute) root_arg=$identity_root ;;
    relative) root_arg='../identity-source' ;;
    symlink) root_arg=$identity_link ;;
  esac
  (cd -- "$identity_work" && zsh "$generator" "$root_arg")
done
canonical_manifest="$tmp_dir/identity-work-absolute/manifests/home_entries.tsv"
cmp -s -- "$canonical_manifest" \
  "$tmp_dir/identity-work-relative/manifests/home_entries.tsv" || \
  fail "relative ROOT produced different path identities"
cmp -s -- "$canonical_manifest" \
  "$tmp_dir/identity-work-symlink/manifests/home_entries.tsv" || \
  fail "symlink ROOT produced different path identities"

print -r -- "PASS: manifest inventory is byte-safe and immediate-only"
