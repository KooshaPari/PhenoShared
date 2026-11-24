# Issue: Tracera containers have no resource limits

**Severity:** High
**Category:** Stability
**Reporter:** OWL (external audit)
**Date:** 2026-05-02

## Summary

Tracera's `docker-compose.yml` and `docker-compose.prod.yml` define no CPU or memory limits for any container. Under load, any service can consume all host resources, causing OOM kills or cascading failures.

## Affected Services

- `go-backend` (port 8080)
- `python-backend` (port 8000)
- `postgres`
- `dragonfly` (Redis)
- `nats`
- `nginx`

## Recommended Fix

Add resource limits to `docker-compose.prod.yml`:

```yaml
services:
  go-backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 256M
  postgres:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
  dragonfly:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
  nats:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M
  nginx:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 128M
```

## Acceptance Criteria

- [ ] All containers in `docker-compose.prod.yml` have `deploy.resources.limits`
- [ ] Memory limits are set based on observed peak usage + 50% headroom
- [ ] CPU limits prevent any single container from starving others
- [ ] Tested under load: no OOM kills at p99 traffic
