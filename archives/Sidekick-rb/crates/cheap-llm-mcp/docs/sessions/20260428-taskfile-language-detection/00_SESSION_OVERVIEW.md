# Session Overview

Goal: update the repo's task automation so `build`, `test`, `lint`, and `clean` work from a
language-aware `Taskfile.yml`.

Success criteria:
- `Taskfile.yml` detects the repo language from manifest files.
- Common tasks dispatch to sensible commands for the detected language.
- The change is validated locally and merged through a PR.
