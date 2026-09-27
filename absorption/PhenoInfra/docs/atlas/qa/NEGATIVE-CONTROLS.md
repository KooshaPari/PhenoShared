# Qualify the instruments before trusting the numbers

Each verifier must demonstrate known-good, known-bad, unavailable and malformed cases. Preserve the fixture, command, output and gate propagation. A green job named 'coverage' or 'links' is insufficient.

## Required adversarial vectors

- Missing required measurement family and a strong unrelated family.
- Coverage exactly below, exactly at and above the accepted threshold; no rounding up.
- Denominator derived only from touched files or observed successes.
- Duplicate eligible/covered IDs, unknown covered IDs, and missing critical coverage.
- Wrong subject, source revision or build profile; stale artifact/result identity.
- A single mixed accumulator presented as independent unit/integration/E2E.
- Missing native tool, failed report parser, empty test selection and skipped checks.
- Backend/evaluator HTTP or parse failure producing a plausible canned result.
- Interrupted run that wrote partial output before failing.
- A healthy local check wrapped by a script that returns success on failure.
- Correct checksum for a false claim: demonstrate that integrity is not truth.
- Private evidence leaking into public generated output or retained source maps.

## Domain examples

Docs: a nonexistent link/anchor and missing required asset must fail. Agent frameworks: replay after an uncertain tool outcome must not duplicate side effects. Storage: failed persistence must not replace the valid checkpoint. Runtime: missing credentials or unsupported GPU must not be labelled healthy. Creative/game: a blank screenshot or mock renderer cannot count as real visual acceptance.

Where broad qualitative judgments are required, use explicit rubrics, independent review and calibration. Do not disguise subjective preference as deterministic conformance, and do not claim automation proves aspects it cannot observe.
