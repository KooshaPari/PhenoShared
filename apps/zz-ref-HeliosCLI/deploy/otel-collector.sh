#!/usr/bin/env bash
set -euo pipefail

# OTel Collector Deployment Script for Helios CLI
# Usage: ./deploy/otel-collector.sh [up|down|restart|status]

if [ -f "$(dirname "$0")/.env" ]; then
  set -a
  source "$(dirname "$0")/.env"
  set +a
fi

export OTEL_EXPORTER_OTLP_ENDPOINT="${OTEL_EXPORTER_OTLP_ENDPOINT:-localhost:4317}"
export JAEGER_URL="${JAEGER_URL:-localhost:16686}"
export PROMETHEUS_URL="${PROMETHEUS_URL:-localhost:9090}"

ACTION="${1:-up}"

case "$ACTION" in
  up)
    echo "Starting OTel Collector via Docker Compose..."
    docker-compose -f "$(dirname "$0")/docker-compose.yml" up -d
    ;;
  down)
    echo "Stopping OTel Collector..."
    docker-compose -f "$(dirname "$0")/docker-compose.yml" down
    ;;
  restart)
    echo "Restarting OTel Collector..."
    docker-compose -f "$(dirname "$0")/docker-compose.yml" restart
    ;;
  status)
    echo "OTel Collector Status:"
    docker-compose -f "$(dirname "$0")/docker-compose.yml" ps
    ;;
  *)
    echo "Usage: $0 {up|down|restart|status}"
    exit 1
    ;;
esac
