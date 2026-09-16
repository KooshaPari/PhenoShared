# pheno-harness — Infrastructure Guide

## Container Image

Multi-stage build with `uv` for deterministic dependency resolution:

```bash
docker build -t ghcr.io/kooshapari/pheno-harness:latest .
```

Layer order is tuned for cache hits:

1. `pyproject.toml` + `uv.lock` + `README.md`
2. `bench/`, `harness/`, `docs/`, `migrations/`

The image exposes port `8000` and runs `python -m bench serve --bind 0.0.0.0:8000` by default.

## Local Stack (`docker-compose.yml`)

| Service | Image | Port | Purpose |
|---|---|---|---|
| `pheno-harness` | local Dockerfile build | 8000 | bench server + metrics |
| `prometheus` | prom/prometheus:v2.51.0 | 9090 | scrape /metrics, TSDB persistence |

Bring it up:

```bash
docker compose up -d
curl -fsS http://localhost:8000/healthz
open http://localhost:9090/graph
```

The Prometheus config at `deploy/prometheus/prometheus.yml` scrapes `pheno-harness:8000/metrics` every 15s.

### Volumes

| Volume | Path in container | Purpose |
|---|---|---|
| `pheno-data` | `/var/lib/pheno-harness` | bench runs + audit logs |
| `pheno-cache` | `/var/lib/pheno-harness/cache` | HF model cache |
| `pheno-prom-data` | `/prometheus` | Prometheus TSDB |

## Kubernetes (`deploy/k8s/`)

- `deployment.yaml` — 2-replica Deployment + Service + PodDisruptionBudget + PVC, with init container that runs migrations on startup
- `kustomization.yaml` — kustomize root

```bash
kubectl apply -k deploy/k8s/
kubectl get pods,svc,pvc
```

### Production Hardening

1. **GPU** — for ML benchmarks, set `nodeSelector: nvidia.com/gpu.product: <gpu-name>` and add `nvidia.com/gpu: "1"` to container resources.
2. **HF cache** — for multi-replica, mount an NFS/EFS volume at `/var/lib/pheno-harness/cache` to share model weights.
3. **Network** — the Service is ClusterIP; front with an Ingress or use `kubectl port-forward` for local.
4. **Resource limits** — defaults are 4 CPU / 8Gi RAM. Bump for larger models.
5. **Migrations** — the init container runs `python -m bench.migrations apply`. Make migration files backward-compatible (additive only).
6. **Backup** — snapshot `/var/lib/pheno-harness/runs` to cold storage nightly.

## Dev Container

`.devcontainer/devcontainer.json` provides a preconfigured Python 3.12 + uv environment. Open in VS Code + Dev Containers extension for a one-click setup.

## Build Matrix

| Target | Command |
|---|---|
| Local | `docker build -t pheno-harness:dev .` |
| Compose stack | `docker compose up -d` |
| K8s deploy | `kubectl apply -k deploy/k8s/` |
| Migrations | `docker compose exec pheno-harness python -m bench.migrations apply` |
| Rollback | `docker compose exec pheno-harness python -m bench.migrations rollback <id>` |

## Related Files

- `Dockerfile` — multi-stage build with uv
- `docker-compose.yml` — local stack
- `deploy/k8s/` — production manifests
- `deploy/prometheus/prometheus.yml` — scrape config
- `.devcontainer/devcontainer.json` — VS Code remote container
- `bench/migrations.py` — schema migration runner
- `migrations/` — JSON migration files
