# Infrastructure stubs

## Temporal
Temporal coordinates the workflow runtime and durable orchestration surface. This stub exists so the docs tree points at the right system without turning the docs into the source of truth.

## Hatchet
Hatchet provides the job execution layer that owns background work and queueing behavior. Keep implementation details in the service code and use this page only as a lightweight pointer.

## Jaeger
Jaeger is the tracing view for request and workflow diagnostics. Treat this as a landing stub and defer operational specifics to the runtime and observability configuration.
