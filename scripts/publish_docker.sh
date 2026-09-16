#!/usr/bin/env bash
# publish_docker.sh — Build + push pheno-harness Docker image to GHCR locally.
#
# Run this on any machine with Docker installed + authenticated to GHCR.
# Cost: $0 (GHCR is free for public repos, free tier for private).
#
# Usage:
#   bash scripts/publish_docker.sh                  # build + push with tag=v0.37
#   TAG=v0.38 bash scripts/publish_docker.sh        # different tag
#   TAG=latest bash scripts/publish_docker.sh       # tag as 'latest'
#   BUILDX=0 bash scripts/publish_docker.sh         # use docker build (not buildx)
#
# Requirements:
#   - Docker 20+ with buildx support
#   - Authenticated to ghcr.io: echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
#
# Scorecard impact: Packaging check (currently -1/10) → 10/10 once image is published.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TAG="${TAG:-v0.37}"
IMAGE_NAME="ghcr.io/<REDACTED>/pheno-harness"
PLATFORMS="${PLATFORMS:-linux/amd64,linux/arm64}"

log()  { printf '\033[1;34m[%s]\033[0m %s\n' "$(date +%H:%M:%S)" "$*"; }
warn() { printf '\033[1;33m[%s]\033[0m %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
fail() { printf '\033[1;31m[%s]\033[0m %s\n' "$(date +%H:%M:%S)" "$*" >&2; exit 1; }

command -v docker >/dev/null 2>&1 || fail "Docker not installed"
docker info >/dev/null 2>&1 || fail "Docker daemon not running"

cd "$REPO_ROOT"

log "Step 1/5: Verify GHCR auth"
docker pull ghcr.io/<REDACTED>/pheno-harness:latest 2>&1 | head -3 || \
    warn "Not authenticated to GHCR. Run: echo \$GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin"

log "Step 2/5: Build + push multi-arch image"
if [[ "${BUILDX:-1}" == "1" ]]; then
    log "  docker buildx build --platform=$PLATFORMS --push"
    docker buildx create --use --name pheno-builder 2>/dev/null || true
    docker buildx build \
        --platform "$PLATFORMS" \
        --tag "${IMAGE_NAME}:${TAG}" \
        --tag "${IMAGE_NAME}:latest" \
        --provenance=true \
        --sbom=true \
        --label "org.opencontainers.image.title=pheno-harness" \
        --label "org.opencontainers.image.description=Local routing, compression stack, RLVR eval, and Harbor terminal-bench wrappers for OmniRoute Main" \
        --label "org.opencontainers.image.source=https://github.com/<REDACTED>/pheno-harness" \
        --label "org.opencontainers.image.licenses=MIT" \
        --label "org.opencontainers.image.version=${TAG}" \
        --push \
        .
else
    log "  docker build + docker push (single arch)"
    docker build \
        --tag "${IMAGE_NAME}:${TAG}" \
        --tag "${IMAGE_NAME}:latest" \
        --label "org.opencontainers.image.title=pheno-harness" \
        --label "org.opencontainers.image.source=https://github.com/<REDACTED>/pheno-harness" \
        --label "org.opencontainers.image.licenses=MIT" \
        --label "org.opencontainers.image.version=${TAG}" \
        .
    docker push "${IMAGE_NAME}:${TAG}"
    docker push "${IMAGE_NAME}:latest"
fi

log "Step 3/5: cosign keyless sign image"
command -v cosign >/dev/null 2>&1 || fail "cosign not installed. Install: brew install cosign"
cosign sign --yes "${IMAGE_NAME}:${TAG}"

log "Step 4/5: Verify"
cosign verify --insecure-ignore-tlog "${IMAGE_NAME}:${TAG}" 2>&1 | head -5

log "Step 5/5: Make public (if private)"
docker buildx imagetools inspect "${IMAGE_NAME}:${TAG}" 2>&1 | head -10

log "DONE."
log "  Image: $IMAGE_NAME:$TAG"
log "  GHCR : https://github.com/<REDACTED>/pheno-harness/pkgs/container/pheno-harness"