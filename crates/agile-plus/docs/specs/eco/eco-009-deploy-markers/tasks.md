---
spec_id: eco-009
---

# Tasks — Deploy Markers

## WP-01: Close the 60/61 deploy-marker gap

### Phase 1 — Audit (Phase ID: PH-AUDIT)

- [ ] T-01 Enumerate all 61 repos under `repos/` and check for `docs/deployment.md`.
- [ ] T-02 Emit `worklogs/deploy-marker-scaffold-20260605.json` with initial per-repo status map.
- [ ] T-03 Publish the standard `docs/deployment.md` template in the spec directory.

### Phase 2 — Scaffold (Phase ID: PH-SCAFFOLD)

- [ ] T-04 Fan out parallel sub-agents (or direct file writes if disk is full) to add the marker to each missing repo.
- [ ] T-05 Update the worklog after each batch with timestamp, author, repo, and status.
- [ ] T-06 For explicitly excluded repos, create `docs/deployment.NA.md` with a justification note referencing the reason.
- [ ] T-07 Validate every created file is UTF-8 via `agileplus validate-encoding --all --fix`.

### Phase 3 — Verify (Phase ID: PH-VERIFY)

- [ ] T-08 Re-run the marker audit; confirm 61/61 confirmed or all remaining entries are excluded with justification.
- [ ] T-09 Patch the health scan to gate deploy-surface confirmation on marker presence (FR-DM-03).
- [ ] T-10 Add a unit test asserting a repo without the marker is not counted as confirmed.
- [ ] T-11 Spot-check three random `docs/deployment.md` files for required sections.
- [ ] T-12 Write the final worklog snapshot and mark WP-01 complete.
