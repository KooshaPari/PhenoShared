#!/usr/bin/env bash
# Mirror all upstream Rust MCP SDK branches and tags into the PhenoFastMCP-rust fork.
# Pattern mirrors scripts/mirror-upstream.sh — clones --mirror, retargets origin, pushes
# heads and tags. Does NOT push refs/pull/* (GitHub rejects hidden refs on forks).
#
# Default upstream is modelcontextprotocol/rust-sdk. Override UPSTREAM to mirror
# rmcp or another fork (e.g. UPSTREAM=https://github.com/rmcp-rs/rmcp.git).
set -euo pipefail

UPSTREAM="${UPSTREAM:-https://github.com/modelcontextprotocol/rust-sdk.git}"
FORK="${FORK:-https://github.com/KooshaPari/PhenoFastMCP-rust.git}"
WORKDIR="${WORKDIR:-/tmp/pheno-rust-mirror.git}"

rm -rf "$WORKDIR"
git clone --mirror "$UPSTREAM" "$WORKDIR"
cd "$WORKDIR"

git remote set-url origin "$FORK"
git config remote.origin.mirror false

branch_count=$(git for-each-ref --format='%(refname:short)' refs/heads/ | wc -l)
tag_count=$(git for-each-ref --format='%(refname:short)' refs/tags/ | wc -l)
pull_count=$(git for-each-ref --format='%(refname)' refs/pull/ | wc -l)

echo "Pushing $branch_count branches from $UPSTREAM -> $FORK"
git push origin 'refs/heads/*:refs/heads/*'

echo "Pushing $tag_count tags"
git push origin 'refs/tags/*:refs/tags/*'

echo "Pull refs preserved locally only (not pushed): $pull_count"
echo "Mirror complete."
