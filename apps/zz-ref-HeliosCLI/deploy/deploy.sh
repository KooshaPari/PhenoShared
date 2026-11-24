#!/usr/bin/env bash
# Helios CLI — Production OTel Collector Deployment Script
# Usage:
#   ./deploy.sh                  # Deploy with .env defaults
#   ./deploy.sh --env .env.prod  # Deploy with custom env file
#   ./deploy.sh --dry-run        # Show what would be deployed
#   ./deploy.sh --health-only    # Run health checks only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Defaults ─────────────────────────────────────────────
ENV_FILE="${SCRIPT_DIR}/.env"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.production.yml"
DRY_RUN=false
HEALTH_ONLY=false
WAIT_READY=true
WAIT_TIMEOUT=60

# ── Colors ───────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── Argument parsing ─────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)        ENV_FILE="$2"; shift 2 ;;
    --dry-run)    DRY_RUN=true; shift ;;
    --health-only) HEALTH_ONLY=true; shift ;;
    --no-wait)    WAIT_READY=false; shift ;;
    --timeout)    WAIT_TIMEOUT="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: $0 [--env FILE] [--dry-run] [--health-only] [--no-wait] [--timeout SECS]"
      exit 0 ;;
    *) err "Unknown option: $1"; exit 1 ;;
  esac
done

# ── Prerequisites check ──────────────────────────────────
check_prerequisites() {
  info "Checking prerequisites..."

  if ! command -v docker &>/dev/null; then
    err "Docker is not installed. See https://docs.docker.com/get-docker/"
    exit 1
  fi

  if ! docker info &>/dev/null 2>&1; then
    err "Docker daemon is not running."
    exit 1
  fi

  if ! docker compose version &>/dev/null 2>&1; then
    err "Docker Compose v2 is required. Run: docker compose version"
    exit 1
  fi

  ok "All prerequisites met."
}

# ── Validate environment ──────────────────────────────────
validate_env() {
  if [[ ! -f "$ENV_FILE" ]]; then
    warn "No .env file found at ${ENV_FILE}"
    warn "Copying from .env.production template..."
    cp "${SCRIPT_DIR}/.env.production" "$ENV_FILE"
    warn "Please edit ${ENV_FILE} with production values before deploying."
    exit 1
  fi

  # shellcheck disable=SC1090
  source "$ENV_FILE"

  if [[ "${GF_SECURITY_ADMIN_PASSWORD:-}" == "CHANGE_ME" ]]; then
    err "Grafana admin password is still 'CHANGE_ME'. Edit ${ENV_FILE} first."
    exit 1
  fi

  ok "Environment validated."
}

# ── Deploy ────────────────────────────────────────────────
deploy() {
  info "Deploying Helios CLI OTel stack..."
  info "  Compose file: ${COMPOSE_FILE}"
  info "  Env file:     ${ENV_FILE}"

  local compose_args=(-f "$COMPOSE_FILE" --env-file "$ENV_FILE")

  if $DRY_RUN; then
    info "Dry run — would execute:"
    docker compose "${compose_args[@]}" config --services
    return 0
  fi

  # Pull latest pinned images
  info "Pulling images..."
  docker compose "${compose_args[@]}" pull

  # Start the stack
  info "Starting services..."
  docker compose "${compose_args[@]}" up -d --remove-orphans

  ok "Services started."
}

# ── Health check ──────────────────────────────────────────
wait_for_ready() {
  if ! $WAIT_READY; then return 0; fi

  info "Waiting for services to become healthy (timeout: ${WAIT_TIMEOUT}s)..."

  local compose_args=(-f "$COMPOSE_FILE" --env-file "$ENV_FILE")
  local elapsed=0
  local interval=3

  while [[ $elapsed -lt $WAIT_TIMEOUT ]]; do
    local all_healthy=true

    for svc in collector jaeger prometheus grafana; do
      local health
      health=$(docker compose "${compose_args[@]}" ps --format json "$svc" 2>/dev/null \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Health',''))" 2>/dev/null || echo "")

      if [[ "$health" != "healthy" ]]; then
        all_healthy=false
        break
      fi
    done

    if $all_healthy; then
      ok "All services healthy."
      return 0
    fi

    sleep "$interval"
    elapsed=$((elapsed + interval))
    printf "."
  done

  echo ""
  warn "Timeout reached. Some services may not be healthy yet."
  warn "Run './health-check.sh' for detailed status."
  return 1
}

# ── Print summary ─────────────────────────────────────────
print_summary() {
  echo ""
  echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
  echo -e "${GREEN}  Helios CLI OTel Stack — Deployment Complete${NC}"
  echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
  echo ""
  echo "  Collector OTLP gRPC:  localhost:4317"
  echo "  Collector OTLP HTTP:  localhost:4318"
  echo "  Collector Health:     localhost:13133"
  echo "  Collector Metrics:    localhost:8889"
  echo "  Jaeger UI:            localhost:16686"
  echo "  Prometheus:           localhost:9090"
  echo "  Grafana:              localhost:3000"
  echo ""
  echo "  Configuration: ${COMPOSE_FILE}"
  echo "  Environment:   ${ENV_FILE}"
  echo ""
}

# ── Main ──────────────────────────────────────────────────
main() {
  echo ""
  echo -e "${BLUE}Helios CLI — OTel Collector Production Deployment${NC}"
  echo ""

  check_prerequisites

  if $HEALTH_ONLY; then
    bash "${SCRIPT_DIR}/health-check.sh"
    exit $?
  fi

  validate_env
  deploy
  wait_for_ready
  print_summary
}

main "$@"
