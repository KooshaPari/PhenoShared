# Forward repair after PR #550

PR #550 merged externally at `0ab9335f22d9d6f21c6efd2894e271be8ac51256` on 2026-09-12. This repair starts from main `28f092e43c655684316e2574612f8bce934a72fa` and restores valid fixes from preserved commit `7b7a1dce4f7fadb26c58bba9ceec5b18f5872e6a` without rewriting history.

## Evidence and scope

The alternative `PROGRAM-AUDIT-AND-WBS-2026-09-08.md` URL returned GitHub HTTP 404 at pinned revision `8822aa14baef2a964288076645edcc493c338688`. The verified repo-relative WBS is `WBS.md`; the inventory uses the same pinned revision. VERIFIED-only routing and the exact inventory evidence gate are restored.

Main still contained an Infisical child environment dump and failure upload of `.env`. Both are removed. The previously validated Ubuntu 24.04 runner is restored. The newer explicit environment-resolution step and removal of the credentialed pull-request trigger are preserved. No historical secret-exposure conclusion is claimed.

The [project specification](../../../kitty-specs/researchledger-corpus-audit-routing/spec.md) records this packet and repair. AgilePlus accepted `specify` into its queue, but the later supported `get_feature` returned gRPC `NOT_FOUND`. Live registration remains PENDING; queue acceptance is not governance completion. No repeat write was submitted.

Old worktree edits and its generated Cargo.lock are preserved separately. Kilo and Ghostty are excluded by user direction. Hosted verification and normal review/merge gates apply to this forward repair.
