# OTel Collector Deployment Guide for Helios CLI

This document provides instructions for deploying the OpenTelemetry Collector for the Helios CLI project.

## Quick Start

1. **Start the Collector**:
   ```bash
   ./deploy/otel-collector.sh up
   ```

2. **Check Status**:
   ```bash
   ./deploy/otel-collector.sh status
   ```

3. **Stop the Collector**:
   ```bash
   ./deploy/otel-collector.sh down
   ```

## Configuration

- `OTEL_EXPORTER_OTLP_ENDPOINT`: OTLP endpoint (default: `localhost:4317`)
- `JAEGER_URL`: Jaeger UI (default: `localhost:16686`)
- `PROMETHEUS_URL`: Prometheus UI (default: `localhost:9090`)

## Systemd Service (Linux)

For production Linux hosts:
```bash
sudo cp deploy/otel-collector.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now otel-collector
```
