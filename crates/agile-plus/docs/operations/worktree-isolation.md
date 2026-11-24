# Worktree Isolation

Substantive AgilePlus work must run from a named feature worktree, not from the
canonical main checkout. Each change record should include the worktree path,
branch name, linked kitty spec, and local validation command output.

Before cargo or worktree-heavy tasks, run the disk gate from eco-017 when it is
available and record the 20 GiB floor result in the worklog. If free space falls
below 10 GiB, prune build artifacts before continuing.
