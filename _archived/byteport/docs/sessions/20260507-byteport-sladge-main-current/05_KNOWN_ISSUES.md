# Known Issues

- Normal BytePort worktree checkout may report LFS pointer warnings for archived
  `backend/byteport/tmp/` artifacts. The recreated worktree uses
  `GIT_LFS_SKIP_SMUDGE=1` and remains clean under `git lfs status`.
- The repository Taskfile still describes Cargo gates, while the current
  project guidance in `CLAUDE.md` identifies Go as the active backend stack.
- Broad `backend/nvms` validation still fails on pre-existing import cycles,
  provider type redeclarations, and an upstream `spin-go-sdk` export comment
  issue. This session validates the touched `backend/byteport` module.
