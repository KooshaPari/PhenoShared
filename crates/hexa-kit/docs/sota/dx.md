# DX — SOTA (HexaKit genesis)

## Workflow

1. `cp -r templates/genesis/*` into new repo (CLI planned: `hexakit genesis init`)
2. `python scripts/extract-intent-prompts.py --out-dir docs/intent/prompts --repo <Name>`
3. Edit `charter.md` scope table; fill `docs/intent/synthesis.md`
4. Language template from `templates/<lang>/`

## Alternatives

| Tool | Verdict |
|------|---------|
| Manual README scope | Rejected |
| Only AGENTS.md | Rejected — no review/SOTA |
| **Genesis doc set + scraper** | Chosen |

## Pain points mitigated

- Session prompts lost → scraper writes verbatim files
- Agent scope creep → charter + review block rules
- Template drift → OKF manifest version pin
