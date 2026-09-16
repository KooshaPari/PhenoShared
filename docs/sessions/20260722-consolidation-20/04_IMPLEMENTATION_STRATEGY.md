# Implementation Strategy

## Approach

1. Treat repository metadata as evidence, not authorization.
2. Resolve the actual default branch for each source before comparison; eight are not `main`.
3. Correct Batch A placement errors before reusing its conclusions.
4. Under 98% disk usage and about 22 GiB free, fetch only partial bare-clone objects needed for proof.
5. Compare source and destination commit SHAs, then compare content independently.
6. Preserve HOLD and VERIFY-ONLY states unless both proof classes satisfy binary acceptance.
7. For docket #1 only, revalidate immediately, rename to the preservation name, archive, and
   postverify metadata plus ref/commit/tree identity.

## Execution Record

Docket #1 completed the authorized transaction and is `ARCHIVED-PRESERVED`. The renamed repository
is private and nonfork, retains default branch `recovery/isolated-20260714`, one branch, zero tags,
unchanged `pushed_at=2026-07-16T00:20:23Z`, exact commit
`0aafdf9692c11abb6e426f36857aeec7bb6cd942`, and exact tree
`eb82ced16353219d85aa83c925819ae48cb36c16`. The canonical AgilePlus recovery ref, commit, and tree
are unchanged, and the old source name redirects. The remaining 19 dispositions did not change.

## Safety Boundaries

- No repository deletion.
- No force-push or history rewrite.
- No further remote mutation; the only completed remote mutation was the authorized docket #1
  rename and archive.
- No mutation of the `PriceyApp` fork or the incomplete router-docs/template-commons absorptions.
- No READY classification inferred from naming, reachability, or prior Batch A placement alone.

## Tranche 2 Strategy

Enumerate every source head, tag, and release; resolve its registry-designated parent; then require
exact ref plus commit/tree reachability. Technical parity does not override a stricter concurrent
governance packet: the harmonizer archive therefore remains mutation-blocked by `archive=false`.

Tranche 3 applies the same gate to branch-heavy archives: object reachability without a complete
namespaced ref set is insufficient. Any future additive import requires an explicit sponsor-approved
execution packet; this specification does not itself authorize cross-repository ref creation. No
deletion, force-push, or source-ref removal is authorized.

Tranche 4 distinguishes footprint reduction from forced absorption. Unique products and forensic
evidence remain standalone when that is the mature boundary; only proven duplicate history becomes
an archive candidate.
