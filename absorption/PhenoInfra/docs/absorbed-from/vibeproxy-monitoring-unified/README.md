# vibeproxy-monitoring-unified (retired)

| Field | Value |
|-------|-------|
| **Source repo** | https://github.com/KooshaPari/vibeproxy-monitoring-unified |
| **Retirement date** | 2026-06-18 |
| **Registry wave** | G19 (wave15 stub absorption) |
| **Disposition** | RETIRE |
| **Successor** | [cliproxyapi-plusplus](https://github.com/KooshaPari/cliproxyapi-plusplus) |

## Summary

`vibeproxy-monitoring-unified` was an archived governance stub for shared VibeProxy observability configuration. It never shipped dashboards, alert rules, or deployable monitoring assets. Per registry wave G19, the stub is retired without copying content into `phenotype-infra`.

VibeProxy client and proxy-plane absorption completed in wave G16; monitoring ownership follows the canonical proxy repo.

## Canonical pointer

All VibeProxy absorption — including client UX harvest and operator monitoring surfaces — is documented in cliproxyapi-plusplus:

**[VIBEPROXY_ABSORPTION.md](https://github.com/KooshaPari/cliproxyapi-plusplus/blob/main/docs/VIBEPROXY_ABSORPTION.md)**

Related merged work:

- cliproxyapi-plusplus G16 boundary ([#1026](https://github.com/KooshaPari/cliproxyapi-plusplus/pull/1026))
- vibeproxy redirect ([#14](https://github.com/KooshaPari/vibeproxy/pull/14))

## Registry reference

- `phenotype-registry` project stub: `projects/vibeproxy-monitoring-unified.json` (`disposition: RETIRE`)
- ECOSYSTEM_MAP P9: retire stub; no parallel monitoring repo

## Do not

- Recreate a standalone `vibeproxy-monitoring-unified` repo or fork.
- Add monitoring SSOT under `phenotype-infra` for VibeProxy — use cliproxyapi-plusplus operator docs instead.
