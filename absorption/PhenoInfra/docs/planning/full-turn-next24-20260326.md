# Next 24 — full-turn + shipping hygiene (PhenoDocs)

**Layout:** four child agents × six items = **24**. **Six agents × four items** is equivalent.

**Norm:** [Full-turn delivery](../guides/full-turn-delivery.md)

## Child agent 1 — Merge + GitHub

1. Land pending doc/theme changes via **PR → `main`**; paste PR URL into `CHANGELOG.md` Unreleased or PR description.
2. Add **`gh pr view` / `gh pr list`** to contributor habit in `README.md` Quick Start (one line).
3. Optional GitHub **label** `full-turn` on merge PRs—document as optional in full-turn guide.
4. Verify **deploy workflow** runs post-merge (`deploy.yml` badge already on README).
5. Record **release branch** name convention (`release/x.y`) in full-turn guide if used.
6. **Stacked PRs:** cross-link Phenotype Git protocol in `AGENTS.md` (already present)—add “each stack layer merges before closing turn” sentence.

## Child agent 2 — Changelog + version

7. Keep **`CHANGELOG.md`** **[Unreleased]** updated every merged PR (even docs-only).
8. On **version bump**, align `package.json` with tag strategy (CalVer vs SemVer for hub).
9. Document **when not to bump** (typo fix, internal-only) in PR template suggestion.
10. Optional: **`changesets`** or **git-cliff**—research-only row; pick one in a follow-up ADR.
11. Link **CHANGELOG** from **Workspace views → changelog** page.
12. **Pages build:** confirm `pnpm run build` in CI matches local.

## Child agent 3 — Docs + views

13. **Full-turn guide** linked from [views index](/views/) footer or callout.
14. **Roadmap** row: “Full-turn discipline” under Next milestones.
15. **`docs/views/commits`:** CI job sketch to refresh `commit-log.json` (issue or session note).
16. **Lint:** `pnpm run lint` on PR when only `docs/**/*.md` touched.
17. **Dead links:** run `check-links` script when available before merge.
18. **Sidebar:** keep **Workspace views** + **Planning** in sync with new pages.

## Child agent 4 — Verification + org

19. **Dogfood:** one PR that **only** adds full-turn doc + this Next 24; merge; record URL.
20. Cross-link **AgilePlus** `full-turn-delivery` from PhenoDocs guide (optional single sentence “org norm”).
21. **Security:** no tokens in PR bodies; `gh` auth via keyring.
22. Post-merge: **`git pull origin main`** on integrator clone.
23. **Metrics:** merged PR count per month in roadmap narrative (manual).
24. **Rotate:** next wave picks three items from **rich workspace views** plan for implementation PRs.

## Done when

- Every closed wave has **≥1 merged PR** reference and **CHANGELOG** touch when user-visible.
- **`gh`** history shows merges; site deploy reflects **`main`**.
