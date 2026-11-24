#!/usr/bin/env bash
# Justification (≤5-line glue): single jq-based JSON edit + git commit; a Rust
# rewrite would be net negative for this trivial config flip. If this hook
# grows beyond ~10 lines, port to Rust under `iac/oci-post-acquire/src/bin/`.
set -euo pipefail
REPO="${PROJECTS_LANDING_REPO:-$HOME/CodeProjects/Phenotype/repos/projects-landing}"
DATA="$REPO/data/repos.json"
[ -f "$DATA" ] || { echo "skip: $DATA missing" >&2; exit 0; }
tmp="$(mktemp)" && jq --arg ip "$OCI_PUBLIC_IP" --arg region "$OCI_REGION" \
  '(.nodes[] | select(.provider=="oci")) |= (.mesh="✅" | .public_ip=$ip | .region=$region)' \
  "$DATA" > "$tmp" && mv "$tmp" "$DATA"
git -C "$REPO" add data/repos.json && git -C "$REPO" commit -m "chore(portfolio): OCI mesh ✅ ($OCI_REGION)"
