#!/usr/bin/env bash
# Helios CLI — OTel Stack Teardown (Linux/macOS)
# Usage:
#   ./teardown.sh              # Stop and remove containers
#   ./teardown.sh --volumes    # Also remove persistent volumes
#   ./teardown.sh --all        # Remove containers, volumes, and network

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }

REMOVE_VOLUMES=false
REMOVE_ALL=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --volumes) REMOVE_VOLUMES=true; shift ;;
    --all)     REMOVE_ALL=true; shift ;;
    -h|--help)
      echo "Usage: $0 [--volumes] [--all]"
      echo "  --volumes   Also remove persistent data volumes"
      echo "  --all       Remove containers, volumes, and network"
      exit 0 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.production.yml"
ENV_FILE="${SCRIPT_DIR}/.env"

# Resolve compose command
compose_cmd() {
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" "$@"
}

echo ""
echo -e "${BLUE}Helios CLI — OTel Stack Teardown${NC}"
echo ""

if [[ ! -f "$COMPOSE_FILE" ]]; then
  warn "Compose file not found: ${COMPOSE_FILE}"
  warn "Attempting to stop containers by name..."
  docker stop helios-otel-collector helios-jaeger helios-prometheus helios-grafana 2>/dev/null || true
  docker rm helios-otel-collector helios-jaeger helios-prometheus helios-grafana 2>/dev/null || true
  ok "Containers stopped and removed."
  exit 0
fi

info "Stopping services..."
compose_cmd down --remove-orphans
ok "Services stopped."

if $REMOVE_VOLUMES || $REMOVE_ALL; then
  info "Removing persistent volumes..."
  compose_cmd down -v
  ok "Volumes removed."
fi

if $REMOVE_ALL; then
  info "Pruning orphaned images..."
  docker image prune -f --filter "label=com.docker.compose.project=helios-otel" 2>/dev/null || true
  ok "Orphaned resources cleaned."
fi

echo ""
ok "Teardown complete."
echo ""
