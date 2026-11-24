# Genesis documentation scaffold

Copy this entire directory into a new repository root (or use `hexakit genesis init` when available).

HexaKit role: **project scaffolding and templates only** — not domain SDK libraries. See [charter.md](charter.md) boundary class `genesis`.

**Master spec:** [docs/genesis/STANDARD.md](../../docs/genesis/STANDARD.md)

## Contents

| File / dir | Role |
|------------|------|
| [charter.md](charter.md) | Scope + governance hub — links all artifacts |
| [review.md](review.md) | Kilo Code Stand (`kilo-code-stand@1`) |
| [intent.md](intent.md) | Why + prompt index |
| [SOTA.md](SOTA.md) | Executive optimality summary |
| [docs/intent/](docs/intent/README.md) | Prompt provenance + synthesis + assumptions |
| [docs/sota/](docs/sota/README.md) | Dimensional research (technical, DX, UX, AX, …) |
| [okf/manifest.okf.yaml](okf/manifest.okf.yaml) | Open Knowledge Format machine index |
| [okf/wiki/](okf/wiki/README.md) | LLM wiki chunk index |

## Artifact linkage

`charter.md` references:

- [review.md](review.md)
- [intent.md](intent.md)
- [SOTA.md](SOTA.md)
- [okf/manifest.okf.yaml](okf/manifest.okf.yaml)

## After copy

1. Replace `{{PLACEHOLDER}}` values in charter, intent, SOTA, and dimension files
2. Run prompt scraper:

   ```bash
   python scripts/extract-intent-prompts.py \
     --out-dir docs/intent/prompts \
     --repo <RepoName> \
     --sources cursor,forge,claude,codex
   ```

3. Fill [docs/intent/synthesis.md](docs/intent/synthesis.md) and [docs/intent/assumptions.md](docs/intent/assumptions.md)
4. Customize [review.md](review.md) Warn/Info tiers — keep `standard_id: kilo-code-stand@1`
5. Update [okf/manifest.okf.yaml](okf/manifest.okf.yaml) summaries and `provenance.last_scrape`

## Specs (HexaKit)

| Spec | Topic |
|------|-------|
| [STANDARD.md](../../docs/genesis/STANDARD.md) | Master standard |
| [OKF.md](../../docs/genesis/OKF.md) | Open Knowledge Format |
| [CHARTER_SPEC.md](../../docs/genesis/CHARTER_SPEC.md) | Charter requirements |
| [REVIEW_SPEC.md](../../docs/genesis/REVIEW_SPEC.md) | Kilo Code Stand |
| [INTENT_SPEC.md](../../docs/genesis/INTENT_SPEC.md) | Intent + prompts |
| [SOTA_SPEC.md](../../docs/genesis/SOTA_SPEC.md) | SOTA dimensions |

## AgilePlus

When tracked in AgilePlus, set `project.agileplus_spec` in OKF manifest and cite FR IDs in charter in-scope bullets (e.g. `FR-GENESIS-001`).
