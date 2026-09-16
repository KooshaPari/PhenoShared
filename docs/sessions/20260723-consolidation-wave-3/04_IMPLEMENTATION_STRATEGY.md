# Implementation Strategy

Use a preserve-first two-stage flow:

1. Inspect status, refs, remotes, stashes, and Airlock state.
2. Snapshot dirty payloads through Airlock.
3. Scan the unpublished commit set with a clean gitleaks configuration.
4. Push local heads atomically under a repository-specific recovery namespace.
5. Verify every remote ref and only then evaluate canonical boundary absorption.

No source branch is reset, rebased destructively, deleted, or force-pushed.

