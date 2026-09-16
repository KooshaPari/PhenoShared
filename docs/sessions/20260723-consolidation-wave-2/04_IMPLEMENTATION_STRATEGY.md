# Implementation Strategy

1. Preserve first: inventory all refs and local state before any archive action.
2. Archive only empty shells after both zero-ref and no-local-payload evidence converge.
3. For nonempty repositories, publish refs under owner-specific recovery namespaces before archive.
4. For split boundaries such as Httpora, map consumers and refs to every owner before choosing a target.
5. Perform only additive pushes; use atomic ref publication where supported.
6. Record immediate preflight and post-action GitHub evidence for every authorized mutation.

The current branch is documentation-only and stacked on the completed Wave 1 evidence commit.
