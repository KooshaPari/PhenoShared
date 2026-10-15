# ResearchLedger corpus audit routing and review repair

Feature slug: `researchledger-corpus-audit-routing`.

This project-owned specification tracks the registry routing packet originally delivered by PR #550 and its forward repair. ResearchLedger retains the authoritative corpus WBS and implementation ownership.

## Requirements

- Route only VERIFIED destinations; preserve unresolved and unlinked evidence distinctions.
- Link the exact hosted ResearchLedger WBS and inventory revisions and the hosted Benchora owner artifact. Temporary/unpublished Benchora observations are historical.
- Verify Infisical access without printing environment values or uploading secret files.
- Preserve the current workflow trigger boundary: credentialed verification runs on explicit dispatch, reusable invocation, or matching main/master pushes, not pull requests.
- Require fresh hosted checks and review for the forward repair; historical checks are not current proof.

## Tracking status

Registration was subsequently verified by the AgilePlus CLI on 2026-09-12: the `specify` call persisted a Created → Specified transition; a separate `list` command confirmed feature ID **3**, slug `researchledger-corpus-audit-routing`, in the `specified` state. Earlier `get_feature` `NOT_FOUND` responses precede registration and are historical. MCP read-back timed out; transport and governance completion remain **unverified**. See merged [PhenoRegistry #566](https://github.com/KooshaPari/PhenoRegistry/pull/566). Do not re-enqueue the feature.

## Acceptance

- Historical WBS and inventory were observed at `8822aa14baef2a964288076645edcc493c338688` in September. That Git object currently fails access/recovery checks, so **current resolution is not verified**; recover it before treating links as live.
- Infisical child output contains no fetched environment dump and no secret artifact is uploaded.
- Hosted validation and reviewer acceptance are recorded for the repair commit.
- CLI registration is verified as `specified`; MCP transport and governance acceptance remain explicit open gates.

## Recovery continuity (October 13, 2026)

The old ResearchLedger repository is no longer accessible to the current GitHub connection. [PhenoShared #429](https://github.com/KooshaPari/PhenoShared/pull/429) has staged the verified historical Wave 5 evidence but has **not** integrated the later September research branch. [PhenoApps #166](https://github.com/KooshaPari/PhenoApps/pull/166) remains a separate unmerged application import. The logical ResearchLedger authority must be reconciled across the shared research engine, desktop shell and private source vault; this specification is not proof of completed absorption.
