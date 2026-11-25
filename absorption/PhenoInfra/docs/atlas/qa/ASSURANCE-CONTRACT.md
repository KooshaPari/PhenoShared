# Independent QA/QC/QE contract

QA prevents defects through clear contracts, review and process controls. QC checks artifacts/behavior. QE makes the instrumentation, runners, fixtures and failure propagation trustworthy. These are operational definitions for this program, not claims about every industry's terminology.

## Independent coverage

Every required unit, integration and E2E family has its own at-least-85% structural and behavioral coverage where applicable. Existing accepted stronger floors remain. Line, branch/decision and function measurements are distinct. Profile/component/platform cells cannot average away missing capabilities. A combined report is supplemental only.

Denominators come from approved eligible inventories, including zero-hit units, not only observed successes. Scope them to the actual supported component/platform/build profile. Identify generated/vendor code and review exclusions before evaluation. An unsupported instrument produces MEASUREMENT_BLOCKED, not N/A or 100%. A zero-opportunity metric requires an explicit reviewed interpretation; 0/0 is not a numeric success.

## Passing is not coverage

All mandatory selected checks must run and pass; skips, unavailable backends, empty collections, collection failures, crashes, timeouts and quarantined flakes do not count as passes. Known current-target defects cannot hide in the uncovered 15%. Critical security, data integrity, isolation, compatibility, install and recovery obligations require full satisfaction.

The same fixture may support several test families, but each family actually executes its own boundary and produces isolated measurement. A child-process test can be E2E for the bounded CLI behavior it exercises, not proof of unrelated GUI/backend behavior. Never publish the same run under three labels.

## Quality of the oracle

Seed missing inputs, wrong revisions, invalid denominators, absent tools, malformed native reports and actual failed product behavior. Demonstrate nonzero/blocked final gate results. Independently examine assertions and propagation through wrappers/CI. An LLM judge may supplement suitable qualitative evaluation with calibration and error handling; it cannot return canned success on malformed/missing evidence.

## Evidence security

Record source/artifact/tool/config identity, timestamps, environment, command, selection and exit/result. Protect secrets and private inputs in raw logs and derived indexes. Hashes prove retained bytes; they do not authenticate the producer, authorization or truth. Independent reviewers and trusted native adapters remain required.

## Incremental progress

Useful narrow fixes can land under the actual authorized policy while the product remains below its final acceptance floors. Report the child work as complete and parent target as open. Inherited defects not caused by the current diff can be separate work packages while remaining the parent's responsibility. External blockers require exact owner/action/wakeup, not vague 'out of scope'.

## Cross-consumer acceptance

Use the [ecosystem-first policy](../architecture/ECOSYSTEM-FIRST-EVOLUTION.md). Shared capability tests and affected supported consumer tests are different obligations. Preserve functional, error, state, security, timing/resource, packaging and migration contracts across the actual affected support matrix. Test credible planned consumer contracts only as plans/spikes; do not label future products verified. Do not let faster local tests or a smaller local diff hide downstream failures. Keep acceptance proportional to actual contract impact and independent from the implementing agent's success claim.
