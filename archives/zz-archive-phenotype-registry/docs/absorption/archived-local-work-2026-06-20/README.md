# Archived local work preservation - 2026-06-20

These patchsets preserve local work found in archived/read-only repositories that could not be pushed back to their origin branches.

## Repositories

| Repository | Local branch | Upstream | Reason preserved | Required follow-up |
| --- | --- | --- | --- | --- |
| PhenoSchema | chore/dependabot-2026-06-08 | origin/chore/dependabot-2026-06-08 | Local branch was ahead by 2 commits, but GitHub reported the repository is archived/read-only. | Apply only if PhenoSchema is reactivated or map relevant governance/security deltas to a canonical schema target. |
| phenotype-bus | chore/l7-105-phenotype-bus-pre-archive-cleanup-2026-06-18 | origin/chore/l7-105-phenotype-bus-pre-archive-cleanup-2026-06-18 | Local branch was ahead by 3 commits, but GitHub reported the repository is archived/read-only. | Use as preservation evidence for event-bus substrate migration; do not lose src/config.rs and governance deltas. |
| phenotype-dep-guard | main | origin/main | Local main was ahead by 1 commit, but GitHub reported the repository is archived/read-only. | Decide whether dep-guard remains archived or whether its governance bundle belongs in a canonical dependency/security repo. |

Each subdirectory contains status.txt, log.txt, diffstat.txt, name-status.txt, and local-commits.patch.
