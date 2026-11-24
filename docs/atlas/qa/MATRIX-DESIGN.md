# Assurance matrix and reporting

The logical cell is `subject × capability/component × language/runtime × platform × build/feature profile × assurance family × metric × revision/artifact`. Do not materialize every impossible Cartesian combination. Use a reviewed support/applicability manifest to enumerate the required cells and prove why excluded cells do not apply.

Four coverage axes stay separate:

| Axis | Question |
|---|---|
| Inventory | Did we account for the artifact and its scope? |
| Rationale | Is its purpose and constraint known or explicitly unknown? |
| Verification | Does a meaningful oracle exist? |
| Execution | Has that oracle actually run against this candidate? |

A documentation link to a test proves neither the assertion quality nor execution. A test run on a different artifact/profile does not promote the candidate. State diagrams and branches require explicit critical-transition tests, including error, cancellation and restart states.

## Measurement statuses

PLANNED, NOT_RUN, RUNNING, PASS, FAIL, BLOCKED_ENVIRONMENT, MEASUREMENT_BLOCKED, UNSUPPORTED, SKIPPED_BY_POLICY, STALE, SUPERSEDED and AUTHORIZED_EXCEPTION are distinct. A waiver needs an authenticated authority outside this example schema, scope, reason, risk, expiry and compensating controls. Do not use it as a permanent denominator-deletion tool.

## Reporting

Show each gate, denominator size/source, coverage, required-check outcome, critical gaps, freshness and links. Use unknowns explicitly. Aggregate views are navigation only. Do not calculate an overall product percentage that permits faster rendering to offset data loss, or 99% unit coverage to offset absent E2E.

For uncertain/dynamic extraction, report both accounted and unresolved population rather than inventing a precise denominator. Requirements coverage and code coverage are related but not identical: code can be thoroughly executed without validating the user's promised behavior.

## CI optimization

Partition actual independent work, cache only under correct identity/trust rules, run impacted checks with transparent selection and retain periodic full qualification. Cancelling an obsolete preview differs from cancelling half a release publication. Optimize time to useful failure and validated artifact, not reported green speed.
