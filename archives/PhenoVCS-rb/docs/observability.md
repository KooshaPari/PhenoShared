# PhenoVCS Observability

`PhenoVCS` exports OpenTelemetry-compatible traces via `pheno-tracing` (ADR-012, ADR-036).

## Quickstart

```bash
docker run --rm -p 4317:4317 otel/opentelemetry-collector-contrib:0.96.0
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_SERVICE_NAME=phenovcs
wtm ...
```

## CI smoke

`.github/workflows/observability-smoke.yml` spins up `otel/opentelemetry-collector-contrib:0.96.0` and asserts OTLP gRPC port 4317 is reachable.
