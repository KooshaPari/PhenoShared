---
name: pd-repository-integration
description: "Integrate the visual-production kit into phenoDesign and the partial journey migration without overwriting concurrent work."
license: MIT (original guidance; linked tools and assets keep their own licenses)
---

# Repository Integration

Refresh repository heads, worktrees, open PRs and accepted ownership before applying changes. The inspected September 15 snapshot has PR87 open on absorb-phenojourneys-vue, not merged to main. Its viewer, recorder and Remotion packages are the integration targets; the Rust CLI is routed elsewhere.

Run the supplied installer in dry-run mode. It refuses missing migration prerequisites, unexpected file hashes, symlinked destinations and conflicting skill files. Reconcile drift instead of forcing the patch. Preserve existing tokens, theme exports and consumer behavior. Add the Remotion workspace deliberately and align its package versions/lockfile on device.

PhenoDesign should expose the full authoring-to-consumer workflow. Existing docs assign render workers to asset-engine and graphics SDK work to phenotype-gfx; reuse them behind that surface or write a real ownership migration before moving implementations. Do not let stale archived README text redefine the user's current direction.

Run package tests, typechecking, actual native/media/browser canaries and consumer checks from the real checkout. Record changed files and remaining defects with exact acceptance steps. This kit is a local overlay/handoff, not evidence that GitHub was already updated or that a merged PR passed production validation.

## Related contracts

Read the repository's `docs/visual-production/E2E-CONTRACT.md`, `ALL-FORMS.md`, and source catalog for the selected tool. In the standalone kit these are under `docs/` and `resources/`. Preserve exact failure/blocked states and the existing source/evidence owners.
