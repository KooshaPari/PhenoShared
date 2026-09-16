# SPEC-01 — Identity, scope and incremental observation

Status: proposed program contract; no engine transition or product verification claimed.

## REQ-01-01 Stable subject identity

Bind each subject to immutable repository/product identity; names and counts are observations.

Acceptance: Renaming a fixture retains its subject relationships and source lineage.

## REQ-01-02 Current scope binding

Resolve current accepted parent outcome, role and actual permissions before execution.

Acceptance: A task without scope approval remains unclaimable for mutation.

## REQ-01-03 Freshness boundary

Record source revision, tool/config identity, timestamp and partial acquisition coverage.

Acceptance: A stale observation cannot silently satisfy a current-revision query.

## REQ-01-04 Local overlay identity

Represent dirty/untracked authorized state separately from its base commit.

Acceptance: Tests for the base commit cannot qualify changed overlay bytes.

## REQ-01-05 Incremental invalidation

Invalidate affected derived claims from changed inputs without erasing old evidence.

Acceptance: A changed source invalidates dependent evidence and leaves unrelated valid evidence reusable.

## REQ-01-06 Alias and lifecycle distinction

Do not infer activity, archive, deletion or permission solely from topics/prefixes/404.

Acceptance: Ambiguous access or conflicting role is explicit rather than classified as deleted.

## REQ-01-07 Complete acquisition accounting

Enumerate discovered, processed, inaccessible, excluded and unresolved sources.

Acceptance: A partial source scan cannot be reported as a complete repository scan.

## REQ-01-08 No duplicate authority

Reuse accepted source/work/evidence owners and generate projections.

Acceptance: A generated document edit does not mutate real engine state.

## Scope discipline

Apply the actual subject support/role contract. Preserve richer existing source formats and authority. Generated spec bundles do not certify native AgilePlus compatibility; inspect the installed engine/schema first. Unknowns and failures remain explicit.
