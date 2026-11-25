# Tasks — eco-014 UX/DX/AX Richness

| WP | Task | Description | Depends On | Status |
|----|------|-------------|-----------|--------|
| WP-01 | Inventory public apps | Walk `repos/`, classify each app as public/library, produce `backlog/apps-needing-docs.md` with current 0/3 / 3/3 score. | — | PENDING |
| WP-02 | Author three templates | Create `AgilePlus/docs/templates/ux.md`, `dx.md`, `ax.md` with required heading skeleton, Mermaid sample, JSON schema sample, and a "How to use" preamble. | WP-01 | PENDING |
| WP-03 | Implement checker | Add `task spec:check eco-014` to the `task` runner: per-app existence + heading-coverage check, tabular output, non-zero exit on miss; no CI hook required. | WP-02 | PENDING |
| WP-04 | Backfill apps | For each row in `apps-needing-docs.md`, copy the relevant template(s) into the app's `docs/` and fill required sections. Re-run checker until 100% pass. | WP-03 | PENDING |
