# phenoStandards Boundary Correction (2026-07-27)

**Audit ID:** ABS-JUS-phenoStandards-2026-07-27  
**Source:** `https://github.com/KooshaPari/phenoStandards`  
**Audited remote SHA:** `23c0dda23bfd7bd060f53a608032102287498f85` (`main`)  
**Verdict:** `KEEP_STANDALONE_PENDING_BOUNDARY_REVIEW`  
**Confidence:** HIGH for liveness/content; MEDIUM for final owner

## Findings

- `gh repo view` reports the repository as public, non-archived, with a live `main`
  branch and last push `2026-07-22T00:53:25Z`.
- The repository has four commits (initial standards scaffold, CI, changelog, and
  CODEOWNERS/SECURITY updates) and 3 remote branches.
- The root contains shared `.github` templates and CODEOWNERS, `.editorconfig`,
  `.pre-commit-config.yaml`, `mise.toml`, `cliff.toml`, `SPEC.md`, `PLAN.md`,
  `README.md`, `CHANGELOG.md`, and `SECURITY.md`.
- `README.md` declares MIT, but no `LICENSE` file is present; this is a governance
  gap, not evidence that the repository is empty.
- CI invokes `task install`, `task lint`, and `task test`, but no Taskfile is present
  in the audited tree. The CI contract is therefore currently unverified.
- The remote description says `DEPRECATED: Empty skeleton - standards in
  KooshaPari/HexaKit/governance/`. The audited HexaKit tree did not expose a
  `governance/` path or equivalent content proof. The prior registry row's 404 and
  "empty skeleton absorbed" claim is stale and contradicted by the current remote.

## Boundary decision

Keep the source repository preserved and visible as a standalone standards
distribution boundary while the canonical owner is decided. Do not archive, delete,
or absorb it based on the former stub record. A future absorption PR must first
provide a content-equivalence manifest and an owner-approved HexaKit or registry
governance destination, plus repair the missing license/Taskfile contract or record
those gaps explicitly.

## Provenance

This correction supersedes the prior `projects/phenoStandards.json` and
`registry/disposition-index.json` RETIRE/HexaKit claim without deleting the old
history. No local checkout or unpushed worktree was found under `repos/` during this
audit, so no Airlock snapshot was required.
