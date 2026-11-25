# Testing Strategy

## Packet Validation

- Verify all eight required session files exist.
- Verify the exact 20 repository names appear in the packet and no candidate is omitted.
- Verify exactly one READY action completed and is now `ARCHIVED-PRESERVED`; verify every other
  repository remains HOLD or VERIFY-ONLY and fork rules match the specification.
- Verify docket #1 is private, nonfork, archived, defaulted to `recovery/isolated-20260714`, with
  one branch, zero tags, unchanged `pushed_at`, exact commit/tree, and an old-name redirect.
- Verify canonical AgilePlus retains the exact recovery ref, commit, and tree.
- Run whitespace/error validation on the patch.
- Run targeted Markdown link and local-file-presence checks for this packet.

## Future Evidence Gates

For each possible disposition change, independently prove:

1. actual source default branch;
2. source and destination SHA parity;
3. source and destination content parity;
4. correct Batch A placement;
5. fork preservation and absence of remote mutation.

The known ecosystem-validator baseline and Vue missing-end-tag docs-build failure are pre-existing
blockers, not acceptance waivers.

## Completed Transaction Validation

Fresh preflight and postverification passed for docket #1. Rename and archive succeeded; no deletion,
force-push, or history rewrite occurred. The remaining 19 docket entries were not mutated.

## Tranche 2 Validation

- Enumerate all 16 heads, one tag, and zero releases across the six candidates.
- Resolve exact commit and tree objects in each designated parent.
- Treat missing refs, ancestor-only reachability, and selective absorption as non-parity.
- Verify the harmonizer's namespaced AgilePlus head and tag match exact source commits and trees.
- Verify no remote state changes while `archive=false` remains unresolved.
- Validate `artifacts/tranche-2-ref-evidence.tsv` contains one header plus 17 ref records: 16 heads
  and one tag, each with a commit, tree, and parent result.

## Tranche 3 Validation

- Enumerate 49 heads and confirm zero tags/releases across the six candidates.
- Require exact namespaced refs in addition to commit/tree object reachability.
- Verify seven-of-seven org-audit heads in `archive/phenotype-org-audits/`.
- Verify missing-object counts: registry 9, runtime 2, resilience 6, shared 2, user-status 7.
- Confirm no tranche-3 remote mutation occurred.
- Validate `artifacts/tranche-3-ref-evidence.tsv` contains one header plus 49 five-field records.

## Tranche 4 Validation

- Reverify live fork metadata rather than relying on stale registry assumptions.
- Count final-seven refs: 58 heads, four tags, and zero releases.
- Confirm recovery evidence stays private and its contents are not emitted during inventory.
- Confirm router-docs commit/tree absence from OmniRoute and template-commons object absence from
  phenokits-commons.
- Treat restored remotes and contradictory registry history as HOLD unless current exact parity is
  independently proven.
- Confirm no final-seven remote mutation occurred.
