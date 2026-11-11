# SessionLedger — Infrastructure Guide

This document covers how SessionLedger ships, runs, and is operated.

## Container Image

Build with the existing `Containerfile` (multi-stage rust:1.85-slim → debian:bookworm-slim):

```bash
docker build -f Containerfile -t ghcr.io/kooshapari/sessionledger:latest .
```

The image exposes port `7654` (HTTP ingest + health probes).

## Local Stack (`docker-compose.yml`)

Two services:

| Service | Image | Port | Purpose |
|---|---|---|---|
| `sl-daemon` | local Containerfile build | 7654 | ingest + query |
| `otel-collector` | otel/opentelemetry-collector-contrib:0.96.0 | 4317 / 4318 / 13133 | OTLP receiver for traces/metrics/logs, file exporter |

Bring it up:

```bash
docker compose up -d
docker compose ps
docker compose logs -f sl-daemon
```

Health endpoints exposed by the daemon:

- `GET /healthz` — process liveness
- `GET /readyz` — storage + cache readiness

Both are wired into the compose `healthcheck:` and the k8s probes.

## Kubernetes (`deploy/k8s/`)

Manifests:

- `deployment.yaml` — 2-replica Deployment with rolling updates, pod anti-affinity, liveness/readiness probes, PodDisruptionBudget
- `pvc.yaml` — 50Gi RWX PVC for `sl-data`
- `kustomization.yaml` — kustomize root

Apply:

```bash
kubectl create namespace sessionledger
kubectl apply -k deploy/k8s/
kubectl -n sessionledger get pods,svc,pvc
```

Images are pulled from `ghcr.io/kooshapari/sessionledger:latest`. Override with `--image` on kustomize edit.

### Production Hardening Notes

1. **TLS** — terminate at an Ingress (nginx, traefik, or cloud LB) in front of port 7654. Enable HSTS at the LB.
2. **Auth** — the daemon speaks plain HTTP locally; place behind a sidecar (oauth2-proxy, Pomerium) for token enforcement.
3. **Storage** — the PVC is `ReadWriteOnce`; for multi-replica write scaling, move to a network filesystem (NFS, CephFS, EFS) or migrate storage to Postgres.
4. **Observability** — `OTEL_EXPORTER_OTLP_ENDPOINT` is set to the in-cluster collector. Replace with your production collector (Datadog, Honeycomb, Grafana Cloud).
5. **Resource limits** — set to `cpu=1, memory=512Mi`. Bump `cpu` if ingest >10k events/sec.
6. **Backups** — snapshot `/var/lib/sessionledger` to S3/GCS nightly via a CronJob mounting the PVC.

## Build Matrix

| Target | Command |
|---|---|
| Debug build | `cargo build` |
| Release build | `cargo build --release` |
| Cross-compile (linux/amd64) | `cross build --release --target x86_64-unknown-linux-gnu` |
| Cross-compile (linux/arm64) | `cross build --release --target aarch64-unknown-linux-gnu` |
| Container image | `docker build -f Containerfile -t sessionledger:latest .` |
| K8s deploy | `kubectl apply -k deploy/k8s/` |

## Operational Runbook

### Pod CrashLoopBackOff

```bash
kubectl -n sessionledger describe pod <pod>
kubectl -n sessionledger logs <pod> --previous
```

Common causes: PVC not bound, OOM (raise `memory.limits`), missing RBAC.

### /readyz returning 503

Storage backend unreachable. Check the PVC is bound (`kubectl get pvc`) and the volume mount succeeded.

### OTLP pipeline failing

```bash
docker compose logs otel-collector
docker compose exec otel-collector wget -qO- localhost:13133/status
```

Verify `SL_OTEL_EXPORTER_OTLP_ENDPOINT` matches the collector service DNS.

## Local Dev with `devcontainer.json`

Open the repo in VS Code + Dev Containers. The container installs rustup + the sqlx-cli so migrations and queries work immediately.

## Related Files

- `Containerfile` — multi-stage Docker build
- `docker-compose.yml` — local stack
- `deploy/k8s/` — production manifests
- `devcontainer.json` — VS Code remote container
- `migrations/` — SQL schema
- `schema/` — typed Rust row structs
