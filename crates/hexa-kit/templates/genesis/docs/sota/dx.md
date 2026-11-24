# DX — SOTA ({{PROJECT_NAME}})

## Use case

How developers clone, bootstrap, test, and ship changes in this repo.

## Requirements

| Requirement | Weight |
|-------------|--------|
| Documented bootstrap path (<15 min to first green CI) | must |
| Local dev matches CI commands | should |
| Intent/SOTA docs discoverable from README | must |

## Workflow (chosen)

1. {{BOOTSTRAP_STEP_1 — e.g. copy genesis scaffold}}
2. {{BOOTSTRAP_STEP_2 — e.g. run prompt scraper}}
3. {{BOOTSTRAP_STEP_3 — e.g. language template from HexaKit}}
4. {{BOOTSTRAP_STEP_4 — e.g. task quality / smoke script}}

```bash
# Example — replace with repo-specific commands
cp -r templates/genesis/* .
python scripts/extract-intent-prompts.py --out-dir docs/intent/prompts --repo {{PROJECT_NAME}}
```

## Alternatives considered

| Alternative | Pros | Cons | Verdict |
|-------------|------|------|---------|
| README-only onboarding | zero maintenance | agents ignore; scope drift | rejected |
| AGENTS.md alone | familiar to Cursor | no review/SOTA linkage | rejected |
| Backstage software templates | enterprise catalog | heavy ops; not git-native | rejected |
| Cookiecutter / Copier only | fast codegen | weak governance doc linkage | partial |
| **Genesis doc set + templates** | linked charter/review/intent/SOTA | copy step manual until CLI | **chosen** |

## Pain points mitigated

| Pain | Mitigation |
|------|------------|
| Lost session prompts | `docs/intent/prompts/` scraper |
| Agent scope creep | [charter.md](../../../charter.md) + [review.md](../../../review.md) Block tier |
| Template drift | [okf/manifest.okf.yaml](../../../okf/manifest.okf.yaml) version pin |

## Evolution triggers

- `hexakit genesis init` ships → update workflow section
- New primary language template → add DX subsection
