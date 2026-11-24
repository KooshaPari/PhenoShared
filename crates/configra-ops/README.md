# configra-ops

Observability and operations primitives for Configra (audit areas G + K).

## Features

- Structured logging (`tracing` + `tracing-subscriber`, JSON or pretty)
- Correlation ID propagation
- Metrics hook trait + in-process registry
- Liveness / readiness health reports
- Graceful shutdown (SIGINT/SIGTERM + drain timeout)
- CLI: `configra-ops health`, `configra-ops version`

## Quick start

```bash
cargo run -p configra-ops -- health --ready --json
```

See [docs/deploy.md](../../docs/deploy.md) and [docs/remediation/OBSERVABILITY.md](../../docs/remediation/OBSERVABILITY.md).
