# PhenoKits → phenokits-commons gap port

**Date:** 2026-06-16  
**Source:** `<REDACTED>/PhenoKits` (archived)  
**Target:** `<REDACTED>/phenokits-commons`

## Ported in this change

| Gap category | Files | Destination |
|--------------|------:|-------------|
| Root validation tests | 7 | `tests/` |
| Polyglot `phenotype-id` | 8 | `libs/go/phenotype-id/`, `libs/typescript/phenotype-id/`, `libs/python/phenotype-id/` |
| Docs site test harness | 6 | `docs/tests/`, `docs/landing.json` |
| Hexagon CI + template tests | 9 | `hexagon/.github/workflows/`, `hexagon/templates/*/docs/tests/`, Swift `Tests/` |
| Webapp template CI scaffold | 12 | `templates/webapp/.github/` |
| Webapp + hexagonal template tests | 6 | `templates/webapp/docs/tests/`, `templates/hexagonal/.../tests/` |
| App config | 4 | `configs/app/phenotype-config/` |
| HexaKit submodule pointer | 1 | `.gitmodules` |

## Absorbed elsewhere (path redirect only)

Python libraries under `libs/python/*` (except `phenotype-id`) → see `libs/python/README.md`
→ `phenotype-python-sdk/packages/*`.

## Audit criterion

After this port, strict path parity against PhenoKits (excluding `.github/` CI at repo root
and `libs/python` SDK redirects) should reach **100%**.
