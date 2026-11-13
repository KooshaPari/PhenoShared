# Personal — partial absorb (public code only)

Source: `KooshaPari/Personal`, formerly `job-cockpit` (private), default branch
`main` at `967fff25`.

The operator asked for a partial absorb and for the repository to remain a
private double. The split is therefore deliberate:

| Bucket | Files | Disposition |
|---|---:|---|
| S — reusable engine and public-safe code | 185 | **here** |
| R — archival personal records | 23 | stays private |
| P — live operational state | 50 | stays in `Personal` |

This directory is outside `absorption/` on purpose. `absorption/` means the tree
is a complete absorption of its source, and `verify_absorption.py` enforces that.
This is 185 of 258 paths by design, so claiming the namespace would break a check
that has previously caught 788 silently missing files.

## Scrubbing

Identifiers were replaced consistently before publication: service hostnames to
`example.com`, UUIDs to a nil-shaped UUID, launchd labels to `com.example.*`,
home paths to `/Users/example`.

Two blind spots in the first pass are worth recording, because both were real
disclosure rather than fixtures: `/Users/kooshapari` paths were missed because
only the Windows form was matched, and an escaped dot inside a regex literal
defeated the hostname and email patterns. A second pass fixed both.

Verified after scrubbing by two independent means: a residue scan (clean for home
paths, real UUIDs and the handle in hostnames) and
`scripts/scan_absorption_secrets.py` over all 185 files (0 findings).

Every file was then verified byte-identical to the scrubbed source by SHA-256.
