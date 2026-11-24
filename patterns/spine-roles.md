# The 4-role spec/governance spine

**Status:** adopted · **Purpose:** stop the spine repos from competing as overlapping "indexes."

The org's source-of-truth layer is **four repos, each with one role**. They reference each other; they do not duplicate each other.

| Repo | Role | Owns |
|------|------|------|
| **phenotype-registry** | **INDEX** | The canonical ecosystem index — `ECOSYSTEM_MAP.md` (repo roles + dependency graph). The entrypoint for "what exists and how it connects." |
| **PhenoSpecs** | **ADRs / contracts / specs** | Architecture Decision Records (canonical home: `adrs/`), API contracts, specifications. |
| **PhenoHandbook** | **CONVENTIONS** | Patterns, methodologies, anti-patterns — *how we build* (this repo). |
| **phenotype-org-governance** | **ENFORCEMENT** | Reusable policy workflows + the `deny.toml`/license baseline that sibling repos consume. |

## Authority rule

When two documents disagree, authority follows role: the **registry** is authoritative for the ecosystem index, **PhenoSpecs** for decisions/contracts, **this handbook** for conventions, **governance** for enforced policy. A repo must not maintain its own competing copy of another repo's role.

> Historical note: a stale `registry.yaml` index lived in PhenoSpecs; the canonical ecosystem index is `phenotype-registry/ECOSYSTEM_MAP.md`. Don't reintroduce competing top-level indexes.
