#!/usr/bin/env bash
# Helios CLI — OTel Stack Health Check
# Verifies all services are running and responding.
# Exit code: 0 = all healthy, 1 = failures detected

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.production.yml"
ENV_FILE="${SCRIPT_DIR}/.env"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

FAILURES=0

check() {
  local name="$1"
  local url="$2"
  local expected="${3:-200}"

  local status
  status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "$url" 2>/dev/null || echo "000")

  if [[ "$status" == "$expected" ]]; then
    echo -e "  ${GREEN}✓${NC} ${name} — HTTP ${status}"
    return 0
  else
    echo -e "  ${RED}✗${NC} ${name} — HTTP ${status} (expected ${expected})"
    FAILURES=$((FAILURES + 1))
    return 1
  fi
}

check_container() {
  local name="$1"
  local container="$2"

  local status
  status=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "missing")

  local health
  health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$container" 2>/dev/null || echo "missing")

  if [[ "$status" == "running" && ("$health" == "healthy" || "$health" == "no-healthcheck") ]]; then
    echo -e "  ${GREEN}✓${NC} ${name} — running (${health})"
    return 0
  elif [[ "$status" == "running" ]]; then
    echo -e "  ${YELLOW}~${NC} ${name} — running (${health})"
    return 0
  else
    echo -e "  ${RED}✗${NC} ${name} — ${status}"
    FAILURES=$((FAILURES + 1))
    return 1
  fi
}

echo ""
echo -e "${BLUE}Helios CLI — OTel Stack Health Check${NC}"
echo ""

# ── Container status ──────────────────────────────────────
echo -e "${BLUE}Container Status:${NC}"
check_container "OTel Collector"   "helios-otel-collector"
check_container "Jaeger"           "helios-jaeger"
check_container "Prometheus"       "helios-prometheus"
check_container "Grafana"          "helios-grafana"
echo ""

# ── HTTP endpoints ────────────────────────────────────────
echo -e "${BLUE}HTTP Endpoints:${NC}"
check "Collector Health"     "http://localhost:13133"
check "Collector Metrics"   "http://localhost:8889/metrics"
check "Jaeger UI"           "http://localhost:16686"
check "Prometheus"          "http://localhost:9090/-/healthy"
check "Grafana"             "http://localhost:3000/api/health"
echo ""

# ── OTLP receivers ───────────────────────────────────────
echo -e "${BLUE}OTLP Receivers:${NC}"

# Test OTLP gRPC (just check port is open)
if command -v nc &>/dev/null; then
  if nc -z -w3 localhost 4317 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} OTLP gRPC (port 4317) — open"
  else
    echo -e "  ${RED}✗${NC} OTLP gRPC (port 4317) — closed"
    FAILURES=$((FAILURES + 1))
  fi
else
  echo -e "  ${YELLOW}~${NC} OTLP gRPC (port 4317) — skipped (nc not available)"
fi

# Test OTLP HTTP
check "OTLP HTTP (port 4318)" "http://localhost:4318" "405"
echo ""

# ── Prometheus targets ────────────────────────────────────
echo -e "${BLUE}Prometheus Targets:${NC}"
targets=$(curl -s --connect-timeout 5 --max-time 10 \
  "http://localhost:9090/api/v1/targets" 2>/dev/null || echo "{}")

if echo "$targets" | grep -q '"health":"up"'; then
  up_count=$(echo "$targets" | grep -o '"health":"up"' | wc -l)
  echo -e "  ${GREEN}✓${NC} ${up_count} target(s) UP"
elif echo "$targets" | grep -q '"health"'; then
  echo -e "  ${YELLOW}~${NC} Prometheus targets available but none UP"
else
  echo -e "  ${RED}✗${NC} Could not query Prometheus targets"
  FAILURES=$((FAILURES + 1))
fi
echo ""

# ── Summary ───────────────────────────────────────────────
if [[ $FAILURES -eq 0 ]]; then
  echo -e "${GREEN}═══════════════════════════════════════${NC}"
  echo -e "${GREEN}  All checks passed.${NC}"
  echo -e "${GREEN}═══════════════════════════════════════${NC}"
else
  echo -e "${RED}═══════════════════════════════════════${NC}"
  echo -e "${RED}  ${FAILURES} check(s) failed.${NC}"
  echo -e "${RED}═══════════════════════════════════════${NC}"
fi

echo ""
exit $FAILURES
