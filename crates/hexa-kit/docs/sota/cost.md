# Cost — SOTA (HexaKit genesis)

## Comparison

| Model | Governance copies | Maintenance |
|-------|-------------------|-------------|
| 9× `*Kit` archived repos | 9× CI, 9× README, 9× agents | High — audit showed drift |
| HexaKit genesis + 2 SDK monorepos | 1 template + optional SDK extras | Lower — single scrape/review standard |

## Verdict

Consolidating genesis into HexaKit and domain into SDK workspaces minimizes duplicate governance while preserving optional installs for small modules.

## Evolution triggers

- SDK monorepo exceeds ~30 packages → evaluate feature-group publishing only (not new Kit repos)
