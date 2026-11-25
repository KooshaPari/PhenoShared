# SonarCloud new-code gate diagnosis

Status: diagnosis, no change made.
Date: 2026-11-17
Owner of the fix: project admin (SonarCloud settings) plus one repo config decision.

## 1. The failing gate

Sonar project key `KooshaPari_pheno` (project name `PhenoShared`), branch `main`. The quality gate is ERROR with three failing conditions:

| Condition | Actual | Threshold |
|---|---|---|
| `new_reliability_rating` | 5 (E) | `> 1` (worse than A) |
| `new_security_rating` | 5 (E) | `> 1` (worse than A) |
| `new_duplicated_lines_density` | 14.7 | `> 3` |

Identity of the check: check run **134393762488** ("SonarCloud Code Analysis") on commit
**3ded2d0**, conclusion `failure`.

## 2. The gate blocks nothing

All three timestamps below are VERIFIED from the GitHub API, not inferred:

- The PR-head Sonar check concluded `failure` at **2026-11-17T20:57:54Z**.
- PR **#1122** merged at **2026-11-17T21:18:46Z** (merge commit 3ded2d0), 21 minutes later.
- On the merged commit the Sonar check failed again at **2026-11-17T21:47:41Z**, i.e. after
  the merge had already landed.

Required status contexts on `main` are only the two coverage contexts
("Root workspace coverage (whole workspace - >=37%)", "IAC workspace coverage (service - >=10%)")
plus `cargo-check`. Sonar is not among them, and the repo has no ruleset that adds it.
Fail-then-merge is therefore expected behaviour: Sonar is advisory paint, not a gate.

## 3. Root cause (a): the new-code window is degenerate

The project's new-code definition is leak period mode `previous_version` with
`leakPeriodDate` **2026-04-24T19:54:30**, which is the date of the project's first-ever analysis.
The only `VERSION` event in the entire analysis history is **"not provided"**, so the
previous-version boundary can never advance.

The consequence is measurable: new lines are **6,744,849** against an ncloc of **5,614,954**,
i.e. **96.96%** of the repository counts as new code.

A "new code" gate applied to 96.96% of the tree is not measuring a delta: it measures the
repository and relabels ~7 months of accumulated work as this week's changes.

## 4. Root cause (b): scope includes verbatim absorbed third-party trees

Analysis scope includes `docs/absorbed-from-*/**`, `apps/zz-ref-*/**` and `absorption*/**`.
These are verbatim third-party copies kept for provenance, and they dominate duplication:

- 14 locale `translations.ts` files under
  `docs/absorbed-from-*/.../packages/i18n/src/locales/*/translations.ts`, each 93-99% duplicated
  (e.g. `fr` 99.3%, `sk` 99.7%, `cs` 99.7%, `zh-CN` 99.7%, `en` 93.5%).
- One codex test suite duplicated across two crates:
  `apps/zz-ref-HeliosCLI/codex-rs/core/tests/suite/realtime_conversation.rs:71-106` is
  identical to
  `apps/zz-ref-HeliosCLI/codex-rs/app-server/tests/suite/v2/realtime_conversation.rs:99-134`;
  and `.../core/tests/suite/realtime_conversation.rs:243-3096` pairs with
  `.../core/tests/suite/pending_input.rs:53-71`.

So the duplication is overwhelmingly verbatim absorbed code, not hand-written repo code.

## 5. The properties-file trap: MEASURED, and OPEN

Measured:

- The root `sonar-project.properties` names a different project key, `<org>_phenodocs`, not
  `KooshaPari_pheno`. It is therefore not what produces this check.
- Its `sonar.exclusions=...docs/absorbed-from-**` has clearly not taken effect: absorbed paths
  are analysed and duplicated despite it.

Open (NOT concluded): whether `.sonarcloud.properties` is honoured under GitHub-App automatic
analysis is UNKNOWN. The only staff statement found is from 2023 and is scoped to Java:
"automatic analysis only takes the exclusion configuration in the UI into account but not in the
.sonarcloud.properties file". A 2023 Java-scoped statement does not settle a 2026 multi-language
project. Cheap test that settles it: add `.sonarcloud.properties` with one exclusion, wait for one
analysis, then compare the component tree before and after. One cycle, no pipeline change.

## 6. Ranked options

| # | Option | Legitimacy |
|---|---|---|
| 1 | Redefine the new-code window (fixed 30-day window, or set a real `sonar.projectVersion` so `previous_version` advances) | CORRECTIVE, but must never be presented as a code fix |
| 2 | Exclude the archived absorption trees (`docs/absorbed-from-*/**`, `apps/zz-ref-*/**`, `absorption*/**`) | legitimate: they are verbatim third-party copies |
| 3 | Relax the gate thresholds per-project to clear red | dodge |
| 4 | Fix the code until the gate is green | not a path to green: see below |
| 5 | Move to CI-based analysis with `sonar.qualitygate.wait` so the gate becomes real | legitimate, larger change |

- Redefining the new-code window is CORRECTIVE: the current definition is an objective config
  defect (96.96% "new", baseline pinned to day one). It is not a code fix, and must never be
  sold as one.
- Excluding the archived absorption trees is legitimate: they are verbatim third-party copies,
  so it removes most duplication and many BLOCKERs, but it does not green the gate on its own.

Relaxing the gate is a dodge: a per-project threshold downgrade just to clear red is not a fix.

## 7. Why "fix the code" is debt reduction, not a path to green

Rating A requires ZERO issues of the rated type in new code. In new code there are **1,685 bugs**
and **5,622 vulnerabilities**, so rating A needs all 7,307 gone. Even moving E to D would mean
clearing every BLOCKER (46 bugs, 214 vulnerabilities), and the duplication condition is an
independent third failure.

Excluding the absorbed trees does not help enough either: the repo's own `crates` still carry
**356 new bugs** and **3,251 new vulnerabilities** with the absorbed trees excluded, which alone
fails all three conditions.

No credential values appear here; project keys are masked as `<org>_<project>` where in doubt.
