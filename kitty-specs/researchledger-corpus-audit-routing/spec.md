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

This file is a local specification, not proof of live AgilePlus registration. The supported `specify` call accepted the command into its queue, but the subsequent supported `get_feature` returned gRPC `NOT_FOUND`. Registration is PENDING, not verified. No repeat write was submitted. Queue acceptance does not establish governance completion.

## Acceptance

- The WBS and inventory links resolve at `8822aa14baef2a964288076645edcc493c338688`.
- Infisical child output contains no fetched environment dump and no secret artifact is uploaded.
- Hosted validation and reviewer acceptance are recorded for the repair commit.
- Live feature registration remains an explicit open gate until read back successfully.
