# Tasks — <REDACTED> Oldest-First

## WP-01 — Enumeration
Run `gh repo list <REDACTED> --limit 200 --json name,pushedAt,isArchived`; record output path and UTC timestamp in worklog header.

## WP-02 — Filter and Sort
Drop `isArchived == true`; sort by `pushedAt` ascending; break ties by `name` ascending; declare N.

## WP-03 — Embed Top-N
Write the top-N list (name + pushedAt) into the sweep worklog header with the literal `gh` command and the capture timestamp.
