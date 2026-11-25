# Testing strategy

`scripts/release_macos.test.mjs` exercises the non-mutating dry-run plan and rejects unknown
arguments before release work. The focused suite must pass before any operator uses the production
gate. A production execution must independently provide the script's post-build verification output.
