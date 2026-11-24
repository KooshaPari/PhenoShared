# Tasks — Action Hygiene (eco-011)

## WP-01 — Resolve SHAs and freeze audit input
- Identify the upstream default branch SHA for each of the five scoped
  actions: `actions/checkout`, `dtolnay/rust-toolchain`,
  `github/codeql-action/upload-sarif`, `Swatinem/rust-cache`.
- Persist SHAs to `worklogs/action-pin-shas-20260605.json`.
- Snapshot the audit JSON so rewrites are reproducible.
- DoD: SHA JSON exists, every entry is exactly 40 hex chars.

## WP-02 — Triage malformed refs
- Bucket the 384 malformed refs by intended action using path patterns,
  adjacent well-formed lines, and `git log -S` history.
- Decide: rewrite (known action) or quarantine (unknown).
- Emit `worklogs/action-pin-quarantine-20260605.json` for the unknown set.
- DoD: every malformed ref is either rewritten in step 3 or listed in
  quarantine with a reason.

## WP-03 — Fan-out rewrites
- Spawn one worker per repo containing any of the five scoped actions.
- Workers rewrite every `uses:` for the scoped actions to
  `uses: <action>@<40-char-sha>`.
- Malformed refs from WP-02 are rewritten in the same pass.
- Per-repo commit on the existing branch; no force-push, no reset.
- DoD: per-repo diff shows only `uses:` lines changed; no source code drift.

## WP-04 — Verify CI
- Each worker runs the repo's local quality gate.
- Aggregate: re-run `scripts/audit-action-pins.py` (or equivalent) over
  `.github/workflows/` across the org.
- DoD: per-repo gate green; audit shows unpinned < 5, malformed = 0.

## WP-05 — Roll-up and follow-up
- Open a roll-up branch aggregating the per-repo commits.
- Re-run audit; record before/after counts in
  `worklogs/DEPENDENCIES.md`.
- Draft `eco-012-action-hygiene-residual` spec for the long tail and the
  quarantined malformed refs.
- DoD: roll-up branch pushed; eco-012 spec created; worklog entry filed.
