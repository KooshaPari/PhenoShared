#!/usr/bin/env bash
# Generate CycloneDX JSON (spec 1.5) for every package in the repo root Cargo workspace.
# Used by .github/workflows/sbom.yml and release.yml — single source of truth vs duplicating matrix YAML.
#
# Usage: generate-workspace-sboms.sh [REPO_ROOT] [OUTPUT_DIR]
#   REPO_ROOT   — directory containing root Cargo.toml (default: .)
#   OUTPUT_DIR  — flat directory for cyclonedx-sbom-<crate>.json (default: sbom-out)
#
# Requires: cargo, cargo-cyclonedx on PATH, jq.
set -euo pipefail

ROOT="${1:-.}"
OUT_DIR="${2:-sbom-out}"

cd "$ROOT"

if ! command -v jq >/dev/null 2>&1; then
  echo "generate-workspace-sboms.sh: jq is required" >&2
  exit 1
fi

if ! command -v cargo >/dev/null 2>&1; then
  echo "generate-workspace-sboms.sh: cargo is required" >&2
  exit 1
fi

if ! cargo cyclonedx --version >/dev/null 2>&1; then
  echo "generate-workspace-sboms.sh: cargo-cyclonedx is required (cargo install cargo-cyclonedx --version 0.5.9)" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
rm -f "${OUT_DIR}"/cyclonedx-sbom-*.json
find crates -name '*.cdx.json' -type f -delete

workspace_crates="$(mktemp)"
trap 'rm -f "$workspace_crates"' EXIT

cargo metadata --no-deps --format-version 1 | jq -r '
  .workspace_members[] as $id
  | .packages[]
  | select(.id == $id)
  | "\(.name)\t\(.manifest_path)"
' >"$workspace_crates"

expected_count=$(wc -l <"$workspace_crates" | tr -d '[:space:]')
if [[ "$expected_count" -lt 1 ]]; then
  echo "generate-workspace-sboms.sh: cargo metadata returned no workspace crates" >&2
  exit 1
fi

cargo cyclonedx \
  -f json \
  --spec-version 1.5

while IFS=$'\t' read -r name path; do
  [[ -z "${name:-}" ]] || [[ -z "${path:-}" ]] && continue
  path=$(realpath "$path")
  echo "SBOM: ${name} (${path})"
  mdir=$(dirname "$path")
  src="${mdir}/${name}.cdx.json"
  if [[ ! -f "$src" ]]; then
    echo "generate-workspace-sboms.sh: expected output missing: ${src}" >&2
    exit 1
  fi
  cp "$src" "${OUT_DIR}/cyclonedx-sbom-${name}.json"
  rm -f "$src"
done <"$workspace_crates"

shopt -s nullglob
files=("${OUT_DIR}"/cyclonedx-sbom-*.json)
if [[ ${#files[@]} -lt 1 ]]; then
  echo "generate-workspace-sboms.sh: no SBOM files produced under ${OUT_DIR}" >&2
  exit 1
fi
if [[ ${#files[@]} -ne "$expected_count" ]]; then
  echo "generate-workspace-sboms.sh: expected ${expected_count} SBOM file(s), found ${#files[@]}" >&2
  exit 1
fi
echo "generate-workspace-sboms.sh: wrote ${#files[@]} file(s) to ${OUT_DIR}"
