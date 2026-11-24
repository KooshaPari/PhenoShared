# Specifications

## Functional requirements

1. Record exactly 20 candidate repositories.
2. Record canonical parent and non-destructive disposition for each candidate.
3. Preserve source SHA/ref provenance before imports.
4. Import only into namespaced archive or recovery refs.
5. Verify imported SHAs through the GitHub API.
6. Keep archive, rename, delete, and active-branch merge actions outside W0-W2.

## Acceptance criteria

- JSON parses with `jq` and contains 20 candidates.
- Every candidate has a target, disposition, gates, and W1/W2 status.
- Empty shells remain blocked on a local-payload search.
- No source repository settings or refs change during W0.

## Cockpit source-boundary requirements

7. Preserve a time-stamped source-to-renderer-to-output hash chain before any migration.
8. Record live rehash drift as a separate observation; never relabel a historical hash as current.
9. Keep `phenotype-dag/`, `beads/`, and `cockpit/` intact and non-Git until an explicit boundary
   repository decision is approved.
10. Treat AgilePlus as the operational successor, phenotype-registry as schema/governance owner,
    and Tracera as a future consumer.
11. Require atomic writer and renderer migration before a source/output replacement claim.

### Cockpit acceptance criteria

- The 06:53 snapshot contains the exact three SHA-256 values, generation timestamp, and counts.
- Any later byte difference is preserved as drift evidence with its own observation timestamp.
- No `git init`, move, deletion, replacement, source ref mutation, or GitHub repository creation
  occurs as part of this packet.
- A future migration has an explicit source-boundary decision and a stable atomic write/render
  contract before producer or consumer cutover.

## Out of scope

Repository archival/deletion, consumer migrations, semantic feature merges, source/output
replacement, `git init` for source directories, and cleanup of local worktrees or recovery bundles.
