# Cost Budget

## Target (Phase 1)

**$0/month** across all providers. All workloads fit inside documented free tiers.

## Free-tier limits (watch list)

| Provider | Resource | Free tier | Projected use | Headroom |
|----------|----------|-----------|---------------|----------|
| Oracle Cloud | Ampere A1 Flex | 4 OCPU, 24 GiB RAM, 200 GB storage | 4 OCPU, 24 GiB, 100 GB | OK |
| Oracle Cloud | Egress | 10 TB/mo | ~200 GB/mo | ample |
| GCP | e2-micro | 1 VM in us-west1/central1/east1 | 1 VM us-west1 | exact |
| GCP | Egress | 1 GB/mo to internet | <500 MB | ample (via CF Tunnel, mostly internal) |
| AWS | Lambda | 1M req/mo | ~10k req/mo | ample |
| AWS | API Gateway | 1M req/mo | ~10k req/mo | ample |
| Cloudflare | Workers | 100k req/day | ~5k req/day | ample |
| Cloudflare | Tunnel | unlimited | unlimited | ample |
| Cloudflare | R2 | 10 GB storage + 1M class-A ops (Phase 2) | Phase 2 | ample |
| Tailscale | devices | 100 | 7 | ample |
| Tailscale | users | 3 | 1 | ample |

## Paid escalation triggers (Phase 2)

Move to paid tier **only** when:

- Tailscale user count > 3 (unlikely; solo dev).
- Heavy queue depth regularly > 3 jobs over 10 min → provision Hetzner burst (€3-10/mo target).
- R2 storage > 10 GB → pay-per-GB (cheap).

## Monthly cost ceiling

Hard ceiling: **€20/month total.** Agents do NOT provision anything that would cross this without explicit user approval.

## Monitoring

- Each cloud provider: billing alerts at $5, $10, $20.
- Weekly cron (via gcp-e2 uptime sentinel) emits cost summary to Grafana.

## Related

- `docs/runbooks/phase2-hetzner-spillover.md`, `docs/governance/incident-response.md`
