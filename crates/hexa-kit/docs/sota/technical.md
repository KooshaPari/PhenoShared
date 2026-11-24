# Technical — SOTA (HexaKit genesis)

## Use case

Deliver repeatable repo skeletons that embed governance docs and language-specific layout.

## Requirements

| Requirement | Weight |
|-------------|--------|
| Git-native templates (no opaque codegen) | must |
| Multi-language layers composable | must |
| OKF machine index | must |
| Single binary CLI optional | should |

## Alternatives

| Alternative | Type | Verdict |
|-------------|------|---------|
| [Cookiecutter](https://github.com/cookiecutter/cookiecutter) | OSS | Rejected — Jinja-only; weak governance doc linkage |
| [Copier](https://github.com/copier-org/copier) | OSS | Partial — good updates; adopt patterns not full stack |
| Backstage Scaffolder | OSS/CNCF | Rejected — service-catalog centric; heavy ops |
| Monorepo `packages/` only | internal | Rejected — duplicates per-repo governance |
| **HexaKit `templates/` + genesis set** | chosen | Git copies + linked charter/review/intent/SOTA |

## Chosen strategy

Layered template trees (`templates/rust`, `templates/python`, `templates/genesis`) with shared `templates/quality/`. Projects copy genesis docs at bootstrap; OKF manifest enables agent injection.

## Evolution triggers

- Copier-style update flow needed → add `hexakit genesis upgrade`
- ~~rust-sdk split / domain evictions~~ → Waves 2–7 closed settly, Traceon, stashly, Metron, agileplus workspace paths
- Remaining transitional `crates/*` → disposition index in phenotype-registry
