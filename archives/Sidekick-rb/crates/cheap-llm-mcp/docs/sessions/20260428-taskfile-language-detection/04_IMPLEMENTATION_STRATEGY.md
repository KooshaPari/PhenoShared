# Implementation Strategy

Use a single `Taskfile.yml` with a shell-based manifest detector in `vars`. Each task then uses a
`case` statement to select the correct command set for the detected language. This keeps the file
simple and avoids adding extra helper scripts.
