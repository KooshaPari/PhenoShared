# Happy-path-collapse Governance Checklist

## Purpose

This checklist prevents AI-DD happy-path collapse. Any claim in code, PR text, tests, docs, or scripts that implies completion must be grounded in user-traceable, fresh, measurable, and user-visible outcomes.

## Core rules (AI-DD hardening)

1. USER’S EYES = GROUND TRUTH
- Contract: only close or claim `fixed/done/passed` after user-visible confirmation. Use `getUserConfirmation` or equivalent explicit human acceptance.
- Fail pattern: `✅ Fixed`, `done`, `all good`, `pass` without user confirmation evidence.
- PASS evidence: `getUserConfirmation` result, explicit human review note, or review-approved acceptance token in diff/comments.

2. PROVE FRESH CODE
- Contract: always prove stale-code risk and freshness before accepting claims.
- Fail pattern: `tests pass`/`build ok`/`fixed` when only status flags are refreshed and no stale-code checks were run.
- PASS evidence: explicit cache purge, stale-clear command, or output with version/hash/banner/provenance in the same context.

3. TELEMETRY ≠ TRUTH
- Contract: telemetry/events alone are insufficient proof.
- Fail pattern: build/test success reported from metrics/flags only (e.g., `flag=true`, `ok`, `200`) without last-link observables.
- PASS evidence: build/test claim includes last-link evidence (artifact id, run URL, log excerpt, trace id, or user-visible output).

4. STUDY EXISTING SOLUTIONS / EARLY STEERS
- Contract: prefer known substrate over endless local reinvention.
- Fail pattern: replacing/patching established patterns without checking equivalent internal/OSS precedent.
- PASS evidence: link to reused source (`/docs`, ADR, existing module, or platform standard) and scoped diff.

5. ROOT-CAUSE, not blunt-force constants
- Contract: remove root cause, not symptoms.
- Fail pattern: `magic` or large constants/multipliers introduced without measured rationale.
- PASS evidence: threshold derived from observed metrics and traceable bug root-cause notes.

6. TRACK SIZE / PERF / ROBUSTNESS every build
- Contract: include size and latency/throughput evidence for build/test claims.
- Fail pattern: build/test/check claim without size/frame/latency/perf artifact.
- PASS evidence: size/build artifact delta, frameMs/latency, and loadability or stability metric.

7. DON’T GRIND
- Contract: repeated retries/iterations must stop unless `confirmedWins` / user confirmation exists.
- Fail pattern: high `iterCount/retryCount/attempts` thresholds with no `confirmedWins/userConfirmed`.
- PASS evidence: bounded iteration policy and explicit user-confirmed checkpoint(s).

## Pitfall-focused checks

- Stale/freshness check-in rule:
  - Pass when claim includes hash/version/banner/clear-cache or kill-stale markers.
  - Fail when stale-code claims are made without proving runtime freshness.
- Motion-without-result rule:
  - Pass when feature flags are shipped only after measured outcome evidence.
  - Fail when `flag=false` / `enabled=false` / `TODO` gating is shipped as final state.

## FAIL patterns ⇄ PASS evidence

- Fixed claims without confirmation
  - Fail: “Implemented and fixed ✅”
  - Pass: “Awaiting getUserConfirmation before status update”

- Build/test check with no evidence
  - Fail: “build passed”, “tests passed”, “lint ok”
  - Pass: “build passed + bundle size + frameMs + regression run link/artifact hash”

- Freshness-only claims
  - Fail: “validated now” after code edits
  - Pass: “cleared stale cache + printed version/hash/banner from running process”

- Iteration grind
  - Fail: `while (attempt < 100)` with no stop and no user-confirmation signal
  - Pass: bounded attempts + `userConfirmed/retryEscalation` path + evidence

- Flag disabling defaults
  - Fail: `featureEnabled = false` / `TODO` merged as default shipping state
  - Pass: explicit user confirmation or rollout gating rationale in docs

## SOTA research summary notes

- CNCF secure software supply chain guidance emphasizes layered controls, provenance, and supply-chain trust boundaries, which aligns with freshness/provable output requirements. Example source: `https://www.cncf.io/announcements/2021/05/14/cncf-paper-defines-best-practices-for-supply-chain-security/`
- CNCF supply-chain best practices highlight integrity of source and artifact lineage, reinforcing "prove fresh code before claiming fixed." Example source: `https://www.cncf.io/blog/2023/04/19/building-secure-software-supply-chains-in-cncf-with-slsa-assessments/`
- OpenSSF Scorecard focuses on automated security posture checks and repeatable guardrails for open-source health, consistent with pre-commit-style governance automation. Source: `https://openssf.org/scorecard/`
- Google SLI/SLO guidance emphasizes user-centric reliability metrics and avoiding purely internal/system-only interpretations. Source: `https://docs.cloud.google.com/stackdriver/docs/solutions/slo-monitoring/sli-metrics/overview`
- Microsoft Azure Well-Architected Reliability guidance highlights monitoring/target-setting and design-for-recovery practices that map to PASS evidence expectations. Source: `https://learn.microsoft.com/en-us/azure/well-architected/reliability/`

## Governance checklist (quick checklist)

- [ ] All fixed/done/pass claims include user confirmation evidence.
- [ ] Every freshness-related claim includes kill-stale/clear-cache/version/hash/banner proof.
- [ ] No telemetry-only pass markers; each pass links to last-link observable output.
- [ ] Any high constant or multiplier change has root-cause rationale and measurement.
- [ ] Iteration/retry loops are bounded and tied to confirmed wins.
- [ ] Every build/test claim reports size + perf/latency/robustness evidence.
- [ ] No feature flags defaulting disabled/false are treated as final without explicit confirmation.
- [ ] Existing canonical solution was reviewed and referenced before local custom patching.

## Guard script mapping

- Checklist rule coverage is enforced by: `governance/happy-path-precommit.sh`
- This script inspects staged diff (`git diff --cached`) and blocks likely collapses before commit/PR.
- Evidence tokens, iteration threshold, and regex behavior are configurable via environment variables.
