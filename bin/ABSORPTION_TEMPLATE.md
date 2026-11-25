# Absorption Manifest — <repo-slug>

<!--
Copy this file to docs/absorbed-from-<repo>/ABSORPTION.md and fill every
section below. Deletion of a GitHub repository under the
phenotype-tooling umbrella REQUIRES this manifest to be present and
complete; see bin/repo-delete-gate.{sh,ps1}.

This template is the response to the go-nippon audit
RECOMMENDED_NEXT_ACTIONS item, and to the retroactive manifest at
forge/agentuserstatus-merge/phenotype-tooling/docs/absorbed-from-go-nippon/ABSORPTION.md:1-28
which documented the gap that this template now closes.
-->

## Source

- **Repo:** `<owner>/<repo-slug>`
- **GitHub URL:** `https://github.com/<owner>/<repo-slug>`
- **Archived at:** `<ISO-8601 timestamp when isArchived flipped to true>`
- **Default branch at archive time:** `<branch name>`
- **Last commit SHA on default branch:** `<sha>`
- **Visibility at archive time:** `<public | private | internal>`

## Target

- **Receiving repo:** `<owner>/<repo-slug>` (typically `phenotype-tooling`)
- **Receiving path:** `docs/absorbed-from-<repo-slug>/`
- **Local mirror path (if any):** `<absolute path to local clone or 'none'>`
- **Bundle file (if any):** `<path to .bundle file or 'none'>`

## Status

Choose ONE of the following and delete the others:

- [ ] **DELETE** — fully absorbed; this repo can be deleted from GitHub today.
- [ ] **DELETE_AFTER_PATCHES** — absorption is in progress; this repo must
      remain on GitHub until referenced upstream PRs land. Re-evaluate
      on `<date>`.
- [ ] **PRESERVE** — do NOT delete. The repo is referenced by external
      forks, downstream consumers, or unmerged PRs. Document those
      references under "Gaps and Exceptions" below.
- [ ] **ARCHIVE_ONLY** — keep on GitHub archived, do not delete. Use this
      when source content is preserved locally but external dependents
      still point at the repo.

**Confidence:** `<LOW | MEDIUM | HIGH>`

> HIGH   = every required section below is backed by a verified artifact
>          (bundle, local clone, branch inventory diff, parity diff).
> MEDIUM = one or more sections reference artifacts that have not yet been
>          independently re-verified by a second reviewer.
> LOW    = at least one section is best-effort or has open gaps. LOW
>          confidence forbids DELETE; only DELETE_AFTER_PATCHES or
>          ARCHIVE_ONLY are permitted.

## Source Inventory Summary

Describe the source repo's content surface so a reviewer can confirm nothing
was lost. Replace `<...>` placeholders.

- **Languages detected:** `<comma-separated list, e.g. "Rust 78%, Python 19%, Shell 3%">`
- **Top-level directories:** `<bulleted list>`
- **Total commits on default branch:** `<integer>`
- **Total branches (local + remote):** `<integer>`
- **Total tags:** `<integer>`
- **Open issues at archive time:** `<integer>`
- **Open PRs at archive time:** `<integer>`
- **Release artifacts of interest:** `<list of release tags / binaries>`
- **Bundle reference:** `<path or URL to a .bundle containing full history, or 'NONE — see Gaps'>`

## BRANCH_INVENTORY

Enumerate every branch that carried non-default content. For each, indicate
whether it has been merged into the target, rebased onto the target, or
explicitly abandoned. Branches with slash-style prefixes (e.g. `feature/x`,
`fix/y`, `chore/z`) are required by the grader.

| Source branch | Last commit SHA | Merge / rebase / abandon | Notes |
|---------------|-----------------|--------------------------|-------|
| `<branch>`    | `<sha>`         | `<action>`               | `<text>` |

- **Branches merged into target:** `<count>`
- **Branches rebased into target:** `<count>`
- **Branches abandoned (with rationale):** `<count>`
- **Branches still open / unresolved:** `<count>` — must be 0 for DELETE.

## ABSORPTION_MATRIX

Demonstrate that the receiving repo now contains every meaningful artifact
from the source. Cite file paths. Each "Target Evidence" cell must include
either `path:NUM` (e.g. `src/lib.rs:42`), a 7+ character git SHA, or a file
extension matching `.rs|.ts|.py|.sh|.md|.json|.toml|.ps1|.js|.go|.cs`.

| Source artifact | Receiving path | Target Evidence | Parity verdict |
|----------------|---------------|----------------|---------------|
| `<module>`     | `<target path>` | `<path:line or .ext>` | `<merged | rebased | dropped>` |

- **Code modules migrated:** `<list of source path → target path>` —
  e.g. `src/lib.rs → crates/<x>/src/lib.rs`
- **Docs migrated:** `<list>`
- **CI / workflows migrated:** `<list>`
- **Issue/PR references migrated (via import or links):** `<count>`
- **Parity diff summary:** `<one-paragraph statement of any deltas>`

## Gaps and Exceptions

Anything that could NOT be absorbed cleanly. Each item here MUST also appear
under "Last-Resort Exceptions" if the chosen Status is DELETE.

1. `<gap description> — resolution: <text>`
2. `<gap description> — resolution: <text>`

## Last-Resort Exceptions

Items that would, under ideal conditions, block deletion but are accepted
because of time, cost, or external constraints. Each exception requires a
named owner and a review date. The grader requires at least 3 `## Rebuttal`
sub-headings, each containing prose keywords from the set
`However|nevertheless|nonetheless|outstanding|residual|gap|archiv|bundle`
and an absorb phrase such as `cannot absorb`, `cannot bundle`, or
`residual gap`.

### Rebuttal 1
`<rebuttal text>`

### Rebuttal 2
`<rebuttal text>`

### Rebuttal 3
`<rebuttal text>`

| # | Exception | Why accepted | Owner | Review date |
|---|-----------|--------------|-------|-------------|
| 1 | `<text>`  | `<text>`     | `<gh handle>` | `<ISO-8601>` |

> If this section is non-empty, Status MUST be DELETE_AFTER_PATCHES or
> ARCHIVE_ONLY, OR Confidence MUST be LOW with explicit sign-off recorded
> under "Final Recommendation".

## Final Recommendation

One-paragraph recommendation with rationale. If Status is DELETE, this
paragraph must explicitly cite the bundle reference and the parity-diff
verdict, and must be signed off by a second reviewer.

`<recommendation text>`

**Reviewer sign-off (required for DELETE):** `<gh handle>` on `<ISO-8601>`

## Restore Command

The exact command(s) that would recreate the source repo from preserved
artifacts. The pre-delete gate will reject any DELETE that does not include
a working restore command. The grader requires the literal phrase
`cannot absorb` (or a near-match) in this section.

```bash
# Example: restore from local bundle
git clone <bundle path or URL> <repo-slug>
cd <repo-slug>
git remote add origin git@github.com:<owner>/<repo-slug>.git
# then `gh repo create <owner>/<repo-slug> --source=. --push` to recreate.
```

> The phrase `cannot absorb` must appear in this section to satisfy the
> last-resort/preservation rubric.

**Restore prerequisites:** `<e.g. access to bundle, access to local mirror, GitHub org permissions>`
**Restore verified by:** `<gh handle>` on `<ISO-8601>` (dry-run of the above)
