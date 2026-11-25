# phenokits-commons boundary decision

Date: 2026-06-20
Decision: `PRESERVE_ACTIVE_NARROWED`

## Rationale

`phenokits-commons` looked like a broad super-repo because it contained runtime libraries under `libs/go`, `libs/python`, and `libs/typescript`. Those runtime surfaces are now removed from commons via `phenokits-commons#6` after absorption/preservation evidence closed source-loss risk.

The remaining intended boundary is governance/templates/policies/docs/shared artifact patterns. This is still broad, but it is not a runtime package substrate and should not receive executable libraries.

## Matrix

| Source Item | Source Evidence | Category | Source State | Target Repo | Target Evidence | Status | Deletion Justification | Risk if Deleted | Required Action |
|---|---|---|---|---|---|---|---|---|---|
| Go runtime libs | `libs/go/*` | Runtime libraries | removed | `phenotype-go-sdk` | `phenotype-go-sdk#21` merged | `DONE` | Removed from commons after SDK absorption | low | none |
| Python config kit | `libs/python/phenokit-config-kit` | Runtime/scaffold package | removed | `phenotype-python-sdk` | `phenotype-python-sdk#28` merged | `DONE` | Removed from commons after SDK absorption | low | none |
| Other Python libs | `libs/python/*` | Runtime libraries | removed | `phenotype-python-sdk` | file-equivalent target packages observed | `SUPERSEDED_PARITY` | Removed from commons after parity | low | none |
| TypeScript libs | `libs/typescript/*` | Runtime libraries | removed | `phenotype-registry` preservation | `docs/absorption/PhenoKits/typescript-preservation/` | `LAST_RESORT_EXCEPTION` | Removed from commons, preserved pending real TS target | medium | create real TS target if needed |
| Governance docs/templates | `governance/`, `hexagon/`, `docs/governance/` | Governance artifacts | active | `phenokits-commons` | repo remains active after runtime cleanup | `DONE` | This is the narrowed surviving purpose | high if deleted | preserve repo |
| Templates/policies/config examples | `templates/`, `policies/`, `configs/`, `security/`, `secrets/`, `credentials/` | Shared artifact patterns | active | `phenokits-commons` | remaining repo boundary | `DONE` | This is the narrowed surviving purpose | high if deleted | preserve repo |

## Final recommendation

Do not delete `phenokits-commons`. Keep it active but narrowed. Future runtime libraries must go to tight SDK/package repos, not this commons repo.
