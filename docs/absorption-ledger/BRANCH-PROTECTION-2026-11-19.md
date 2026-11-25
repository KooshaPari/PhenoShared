# Branch protection and required checks (PhenoShared `main`) — 2026-11-19

## Exact commands used (repro)

```bash
gh api repos/KooshaPari/PhenoShared/rulesets
gh api repos/KooshaPari/PhenoShared/branches/main/protection
gh api "repos/KooshaPari/PhenoShared/commits/main/check-runs" --jq ".check_runs[].name"
gh api "repos/KooshaPari/PhenoShared/commits/main/status" --jq ".statuses[].context"
gh api "repos/KooshaPari/PhenoShared/commits/<sha>/check-runs" --jq ".check_runs[].name"
```

## 1) Reconfirm facts (exact outputs)

### Rulesets list
- Command: `gh api repos/KooshaPari/PhenoShared/rulesets`
- Output (exact): `[]`

Interpretation: there are **no repository rulesets** configured (empty array). Protection is enforced via **classic branch protection** on `main` (see below).

### Branch protection (classic) — `required_status_checks` and `enforce_admins`
- Command: `gh api repos/KooshaPari/PhenoShared/branches/main/protection`
- Relevant excerpt (exact JSON fields observed):

```json
{
  "required_status_checks": {
    "url": "https://api.github.com/repos/KooshaPari/PhenoShared/branches/main/protection/required_status_checks",
    "strict": false,
    "contexts": [
      "Root workspace coverage (whole workspace — ≥37%)",
      "IAC workspace coverage (service — ≥10%)",
      "cargo-check"
    ],
    "contexts_url": "https://api.github.com/repos/KooshaPari/PhenoShared/branches/main/protection/required_status_checks/contexts",
    "checks": [
      { "context": "Root workspace coverage (whole workspace — ≥37%)", "app_id": 15368 },
      { "context": "IAC workspace coverage (service — ≥10%)", "app_id": 15368 },
      { "context": "cargo-check", "app_id": 15368 }
    ]
  },
  "enforce_admins": {
    "url": "https://api.github.com/repos/KooshaPari/PhenoShared/branches/main/protection/enforce_admins",
    "enabled": false
  },
  "required_linear_history": { "enabled": true },
  "allow_force_pushes": { "enabled": false },
  "allow_deletions": { "enabled": false }
}
```

**Observed (exact):**
- `required_status_checks.strict`: **false**
- `required_status_checks.contexts` (exact list):  
  1. `"Root workspace coverage (whole workspace — ≥37%)"`  
  2. `"IAC workspace coverage (service — ≥10%)"`  
  3. `"cargo-check"`
- `enforce_admins.enabled`: **false**

Other notable protection settings (from same response): `required_linear_history.enabled = true`, force pushes/deletions blocked, signatures not required, no conversation resolution requirement recorded as enabled in that payload.

## 2) The three required context names (exact)
From `required_status_checks.contexts` / `checks`:
1. `Root workspace coverage (whole workspace — ≥37%)`
2. `IAC workspace coverage (service — ≥10%)`
3. `cargo-check`

## 3) Have those three checks ever reported? (HEAD + recent commits)

### HEAD (`main` as of queries: `f06c3cc7fdf61d75e8aa9f8d0feade068760d308`)
- `GET .../commits/main/check-runs --jq ".check_runs[].name"` (from that commit) includes, among many others:  
  `Root workspace coverage (whole workspace — ≥37%)` **is present**.  
  (`IAC workspace coverage (service — ≥10%)` and `cargo-check` were **not** observed in that check-runs list for HEAD at query time.)
- `GET .../commits/main/status --jq ".statuses[].context"`: **no output** (no commit statuses recorded in that API response for HEAD).

### Sampled recent commits (from `gh api repos/KooshaPari/PhenoShared/commits?per_page=10`): `f06c3cc7`, `3ded2d0a`, `3abb7c3d`, `ae59e073`, `6b48fe9e`, `0ba15905`, `4ca78cfa`, `c8ef448e`, `29974a48`, `d62f1e84`

Check-runs observations (exact names seen per sampled SHA):

- `f06c3cc7` (HEAD): contains **`Root workspace coverage (whole workspace — ≥37%)`**; does **not** list `IAC workspace coverage (service — ≥10%)` or `cargo-check` in the returned check-run names.
- `3ded2d0a`: contains **`Root workspace coverage (whole workspace — ≥37%)`**; does **not** list `IAC workspace coverage (service — ≥10%)` or `cargo-check`.
- `3abb7c3d`: contains **`Root workspace coverage (whole workspace — ≥37%)`**; does **not** list `IAC workspace coverage (service — ≥10%)` or `cargo-check`.
- `ae59e073`: contains **`Root workspace coverage (whole workspace — ≥37%)`**; does **not** list `IAC workspace coverage (service — ≥10%)` or `cargo-check`.
- `6b48fe9e`: contains **`Root workspace coverage (whole workspace — ≥37%)`**, **`IAC workspace coverage (service — ≥10%)`**, and also shows related coverage group jobs (e.g. `Root coverage group — …`, `Coverage membership …`) in the same check-run set; **`cargo-check` was not listed** among check-run names in that response.

Commit statuses (`.../status`) returned **no contexts** for the HEAD sample checked (`f06c3cc7`) and are generally empty in the sampled checks above (no `statuses[].context` output observed).

**Summary (as observed):**
- **`Root workspace coverage (whole workspace — ≥37%)`**: **has reported on `main` recently** (observed on every sampled recent commit checked: `f06c3cc7`, `3ded2d0a`, `3abb7c3d`, `ae59e073`, `6b48fe9e`).
- **`IAC workspace coverage (service — ≥10%)`**: **observed on at least one sampled commit** (`6b48fe9e`). **Not observed** in the other sampled recent commits above (`f06c3cc7`, `3ded2d0a`, `3abb7c3d`, `ae59e073`) at the time of checking (absent from their check-run name lists). This suggests it may run only on certain workflows/paths or not on every push context sampled.
- **`cargo-check`**: **not observed** in check-runs for any of the sampled recent commits (`f06c3cc7`, `3ded2d0a`, `3abb7c3d`, `ae59e073`, `6b48fe9e`). No commit-status contexts were observed for HEAD. Taken together, there is **no evidence in sampled `main` commits** that `cargo-check` has produced a check-run/status context matching that exact name recently; it may be defined but not emitted in current CI, emitted under a different name, or only expected in a flow that is not running on these pushes.

## 4) Mechanism, consequence, options, recommendation

### Mechanism (why the push message is expected)
- Branch protection on `main` requires the three status check contexts listed above (`strict: false`).
- **`enforce_admins.enabled` is `false`**. GitHub’s admin enforcement means protections (including required status checks) do **not** apply to users with admin privileges when this is disabled; administrators can push/merge in ways that bypass those required checks. The repository also shows **no rulesets** (`[]`) to impose stricter org/repo rules that would override this behavior.
- Result: pushes made by administrators (or tokens acting with admin bypass in practice) can satisfy the “bypassed rule violations…” messaging while not having all required checks satisfied in the normal PR gate sense — this is **expected behavior given current settings**, not necessarily a CI malfunction, but it is a **policy bypass**.

### Three required contexts (recap)
1. `Root workspace coverage (whole workspace — ≥37%)`
2. `IAC workspace coverage (service — ≥10%)`
3. `cargo-check`

### Whether they actually run (recap)
- `Root workspace coverage (whole workspace — ≥37%)`: **yes, observed on sampled recent `main` commits** (including HEAD).
- `IAC workspace coverage (service — ≥10%)`: **observed on at least `6b48fe9e`**; **not observed** on several other sampled recent `main` commits — inconsistent/not universally present in the sampled push history.
- `cargo-check`: **no evidence observed** on sampled recent `main` commits (not present in those check-run lists; no commit statuses). Likely missing, renamed, or not triggered by current workflows.

### Consequence
- With `enforce_admins: false` and admin/bypass-capable pushes, **direct pushes to `main` are not reliably gated** by the three required contexts. Even when some checks appear, `strict: false` means merges/pushes are not required to be up to date with base in that strict sense, and the admin exemption removes enforcement for admins.
- Per the report context: **roughly 25 commits** are described as being in an **unverified** state relative to those required checks (policy allows bypass). This increases risk of regressions, coverage regressions, or build breakage landing on `main` without the intended green checks.

### Options (pros/cons)

#### (A) Set `enforce_admins: true` (checks bind for admins) and move to PR flow
- **Pros**
  - Required status checks (`strict` still false unless changed) apply to admins too; pushes that would violate required checks are blocked in the enforced path, restoring the intended gate.
  - Aligns `main` with “checks must be satisfied” policy; pairs naturally with required PR reviews/rulesets later if desired.
  - Makes `cargo-check` / missing checks visible as blocking failures instead of silently bypassed.
- **Cons**
  - **Blocks direct pushes to `main`** for everyone subject to enforcement; requires a PR (and any other branch protection/ruleset rules) workflow. Slows hotfixes and personal/admin direct-commit habits.
  - Will fail until CI produces the **exact** required context names (notably `cargo-check` if it never runs) or protection is updated to match real job names.
  - May require adjusting automation (bots/tokens) to use PRs or appropriate bypass permissions outside admin exemption.
  - `strict: false` remains permissive about being behind base unless changed separately.

#### (B) Leave as is (accept unverified direct pushes)
- **Pros**
  - No workflow disruption; admins can push directly as today.
  - No immediate CI/protection renaming work required.
- **Cons**
  - **`main` remains unverified by policy** for admin pushes; the three contexts are informational at best in practice.
  - Ongoing drift risk: coverage/build regressions can land without required checks passing.
  - `cargo-check` (and possibly `IAC workspace coverage`) may be effectively non-enforced; the “required” list becomes misleading.
  - Incident/compliance posture is weaker if anyone assumes checks are enforced.

#### (C) Keep admin bypass (`enforce_admins: false`) but add a pre-push local gate running the same checks
- **Pros**
  - No GitHub policy change; preserves current push flexibility for admins.
  - Shifts verification left: developers run the same logical checks locally before push (e.g. repo script/hook invoking the same commands/workflows’ equivalents where feasible).
  - Can be tailored per developer machine and updated quickly without org/repo admin changes.
- **Cons**
  - **Not enforceable**: easy to forget, bypass with `--no-verify`, or run different commands than CI (environment differences). Provides no server-side guarantee.
  - Local reproduction of CI (especially coverage gates, service-specific IAC coverage, and any `cargo-check` job defined in Actions) can be brittle or expensive.
  - Does not fix missing/non-running CI contexts (`cargo-check` absent in samples) unless local gate is defined separately.
  - Security/compliance: malicious or careless pushes are still possible; only social/process control improves.

### Recommendation
**Prefer (A) with follow-through**: set **`enforce_admins: true`** and adopt a PR-based flow for `main`, **but only after** (1) auditing GitHub Actions/workflows so the three required contexts are **actually produced with those exact names** on the relevant events (especially fixing or renaming/replacing **`cargo-check`**, and clarifying when **`IAC workspace coverage (service — ≥10%)`** runs), and (2) deciding whether **`strict: true`** is desired. This is the only option that makes the existing “required checks” meaningful for everyone, including admins, and directly addresses the root cause implied by the push warning (“expected” under bypass) becoming a real gate.

If immediate enforcement is impossible operationally, **do not choose (B) silently**: treat (B) as a documented exception and track remediation. Use **(C)** only as a **temporary** mitigation alongside a concrete plan to move to (A) (or to rulesets with explicit bypass roles), because (C) does not prevent unverified `main` history.

**Do not apply any change** (per task): this document records findings and recommendations only.

