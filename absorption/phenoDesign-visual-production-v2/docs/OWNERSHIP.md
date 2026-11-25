# One coherent experience; one owner per responsibility

The user wants phenoDesign to cover the full creative workflow. Do not answer that request by leaving it as a narrow token package. Equally, “put all capabilities behind phenoDesign” does not require independently cloning every lower-level system into that repository.

| Responsibility | Recommended authoritative home / integration |
|---|---|
| Art direction, accepted design grammar, tokens, UI patterns, creative skills | phenoDesign |
| Asset/source/export contracts, design-facing requests and preview/critique UX | phenoDesign; compose existing identity/asset records |
| Absorbed web journey recorder, viewer, presentation generation | Existing phenoDesign migration packages |
| Native/render worker execution and process/GPU/session scheduling | Reuse accepted asset-engine/broker ownership; expose through phenoDesign |
| Reusable low-level graphics functionality | phenotype-gfx rather than a competing SDK |
| Rust CLI/core tooling from journeys migration | Current phenotype-tooling migration owner; verify actual head |
| Product-level dissatisfaction/requirements and durable product model | Existing Tracera ownership |
| Immediate repo-scoped work/spec execution | Existing AgilePlus ownership |
| Deployment/docs hosting | Existing hosting/PhenoDocs owners, not new publication authority |

This is a recommended consolidation boundary, not a permanent veto on moving code. The inspected repository's current docs explicitly assign render workers to asset-engine. If current user-directed consolidation changes that, write a migration ADR, preserve source provenance, move consumers/tests/builds, and retire the old authority. Do not run two silently diverging engines or let stale archived docs override current product intent.

`worker-recipes/` is intentionally outside the phenoDesign overlay. Receiving agents should adapt it into the accepted execution owner after inspecting that repository. The overlay's visual-production package supplies small validators, geometry and staging helpers; it is private and is not a new registry, scheduler, renderer SDK or signing authority.
