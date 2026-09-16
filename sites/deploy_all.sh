#!/usr/bin/env bash
# Deploy all new PhenoDocs landing pages to Vercel.
# Run from PhenoInfra/sites/ directory.
# Requires: vercel CLI authenticated (`vercel login`)
set -euo pipefail

SITES_DIR="$(cd "$(dirname "$0")" && pwd)"
CREATED=0
SKIPPED=0
FAILED=0

# Only deploy newly scaffolded sites (not the 11 that already existed)
NEW_SITES=(
  byterail-landing
  phenoinfra-landing
  pine-landing
  phenotooling-landing
  phenoai-landing
  phenofabric-landing
  phenoregistry-landing
  phenodesign-landing
  phenogfx-landing
  phenomlx-landing
  phenolab-landing
  helioscli-landing
  helioslite-landing
  helioslab-landing
  sharecli-landing
  kcode-landing
  khostty-landing
  substrate-landing
  portage-landing
  researchledger-landing
  sessionledger-landing
  civis-landing
  dino-landing
  omniroute-landing
  melosviz-landing
  civicwarfare-landing
)

echo "=== PhenoDocs Vercel Deploy ==="
echo "Sites to deploy: ${#NEW_SITES[@]}"
echo ""

for site in "${NEW_SITES[@]}"; do
  dir="$SITES_DIR/$site"
  if [ ! -d "$dir" ]; then
    echo "  SKIP  $site (dir not found)"
    SKIPPED=$((SKIPPED + 1))
    continue
  fi

  echo -n "  DEPLOY $site ... "

  # Install deps and deploy
  cd "$dir"
  if bun install --frozen-lockfile 2>/dev/null || bun install 2>/dev/null; then
    if vercel --yes --name "$site" 2>/dev/null; then
      echo "OK"
      CREATED=$((CREATED + 1))
    else
      echo "FAILED (vercel deploy)"
      FAILED=$((FAILED + 1))
    fi
  else
    echo "FAILED (bun install)"
    FAILED=$((FAILED + 1))
  fi
done

echo ""
echo "Done: $CREATED deployed, $FAILED failed, $SKIPPED skipped"
echo ""
echo "Next: Configure CNAME records for each domain:"
echo "  <slug>.phenotype.space -> cname.vercel-dns.com"
