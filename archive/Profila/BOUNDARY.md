# Boundary Lock: Runtime process profiling

**Status:** ACTIVE — canonical runtime profiling boundary.

## Owns
- Live CPU / memory / RSS / FD / network / disk I/O profiling
- Code complexity analysis + continuous CSV pipeline

## Does NOT own
- Rust micro-benchmarks (`Benchora`)
- CI job observability (`phenotype-runs`)

## Fleet integration
Copy under `PhenoObservability/profiling/` for observability stack wiring.