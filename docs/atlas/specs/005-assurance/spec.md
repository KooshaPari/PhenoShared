# SPEC-05 — Independent assurance and meaningful oracles

Status: proposed program contract; no engine transition or product verification claimed.

## REQ-05-01 Unit floor

Meet at least 85 percent independent required unit structural/behavioral coverage; preserve stronger floors.

Acceptance: A below-floor unit cell blocks even if integration/E2E are high.

## REQ-05-02 Integration floor

Measure actual integration boundaries independently against their required inventories.

Acceptance: A unit mock run relabelled integration is rejected.

## REQ-05-03 E2E floor

Measure the real public product/consumer E2E independently.

Acceptance: A root library smoke test cannot qualify a native product artifact.

## REQ-05-04 Metric independence

Keep line, branch/decision, function and behavioral metrics distinct where supported.

Acceptance: High line coverage cannot hide required low branch coverage.

## REQ-05-05 Denominator provenance

Inventory eligible zero-hit units and freeze reviewed denominator before interpreting results.

Acceptance: Unknown/duplicate units and covered items outside denominator fail.

## REQ-05-06 Critical completeness

Cover and satisfy every finite enumerated critical obligation.

Acceptance: Any missing critical item blocks regardless of percentage.

## REQ-05-07 All mandatory checks

Run and pass required checks; missing, failed, skipped, crashed and timeout are nonaccepting.

Acceptance: Empty selected checks or a skipped mandatory case cannot pass.

## REQ-05-08 Independent run selection

Do not combine accumulators or use one run identity as three independent suites.

Acceptance: A mixed-family or reused run is rejected by the reference admission checks.

## REQ-05-09 Unsupported measurements

Expose measurement limitations and require an alternative/authorized exception.

Acceptance: Unsupported or zero-denominator output is not 100 percent.

## REQ-05-10 Negative controls

Prove verifier failure on missing/malformed inputs and actual bad behavior.

Acceptance: A seeded broken docs link or known-bad task causes the final gate to reject.

## REQ-05-11 Trust boundary

Separate payload integrity, producer authenticity and domain truth.

Acceptance: A valid hash on a fabricated report never grants lifecycle approval.

## REQ-05-12 Other required families

Track security, fault, compatibility, performance, docs and delivery obligations independently.

Acceptance: A required family absent from the support profile cannot disappear from acceptance silently.

## Scope discipline

Apply the actual subject support/role contract. Preserve richer existing source formats and authority. Generated spec bundles do not certify native AgilePlus compatibility; inspect the installed engine/schema first. Unknowns and failures remain explicit.
