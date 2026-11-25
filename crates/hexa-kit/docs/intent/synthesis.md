# Intent synthesis — HexaKit

> Last updated: 2026-06-16. Sources: `docs/intent/prompts/cursor/` (43+ scraped sessions).

## Themes

### Theme: Archive audit & boundary ownership

**Prompts:** [b561a593 audit thread](prompts/cursor/20260617-b561a593-1729-44da-b90d-0cfbdf9d72ef-t1.md)

Fleet-wide repo retirement with 100% absorption targets; delete only when boundary covered. User rejected "delete because stub" — wants canonical **boundary owners**.

### Theme: HexaKit = genesis not lib warehouse

**Prompts:** [genesis manual capture](prompts/cursor/20260616-genesis-standard-manual.md)

HexaKit should bootstrap projects/templates; domain kits belong in SDK monorepos with dynamic optional installs.

### Theme: Genesis documentation standard

**Prompts:** [genesis manual capture](prompts/cursor/20260616-genesis-standard-manual.md)

Per-repo: `intent.md`, `docs/intent/`, `charter.md`, `review.md` (Kilo Code Stand), OKF + LLM wiki, `SOTA.md` + `docs/sota/` with dimensional research. Scrape Codex/Claude/Cursor/forge logs for verbatim prompts.

### Theme: Agent orchestration

**Prompts:** [genesis manual capture](prompts/cursor/20260616-genesis-standard-manual.md)

Parent → Cursor subagents (long horizon) → `forge -p` workers (second level). Avoid compressing tasks.

## Confirmed goals

1. **Genesis doc set on every repo** — charter, review, intent, SOTA, OKF
2. **Deterministic prompt provenance** — scrape four agent tools
3. **HexaKit scope = scaffolding** — SDKs own domain boundaries
4. **Kilo Code Stand** — automated PR agents read `review.md`

## Inferred goals (validate)

| Goal | Evidence | Action taken |
|------|----------|--------------|
| Create `phenotype-rust-sdk` | SDK hypo + charter transitional note | Documented in charter/SOTA; not yet created |
| `hexakit genesis init` CLI | template copy need | `templates/genesis/` created; CLI planned |
| Supersede RATIONALIZATION_PLAN HexaKit crate absorption | user message | Charter attestation added |

## Conflicts

| Tension | Resolution path |
|---------|-----------------|
| README says "46-crate infrakit" vs genesis charter | Charter attestation; migrate crates to rust-sdk |
| phenotype-registry still lists HexaKit as SDK class | Update ECOSYSTEM_MAP in follow-up PR |

## Next actions (agents)

1. PR HexaKit genesis standard to `main`
2. Roll `templates/genesis/` into `hexakit new` / registry scaffold
3. Run extract-intent on each canonical repo after bootstrap
4. Forge lanes for SOTA dimension research per major feature

## LLM grounding

Before adding crates to HexaKit: read [charter.md](../../charter.md). Before deleting archives: verify boundary owner + 100% coverage. Before expanding SDK: update [SOTA.md](../../SOTA.md) alternatives table.
