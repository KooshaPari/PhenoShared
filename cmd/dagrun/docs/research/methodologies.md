# Methodologies for the traceability + autograder epic

Scope: how eight specification, contract and test-driven development methodologies map onto an epic that freezes
an assignment contract, binds requirement to scenario to check to evidence, and grades student submissions with
an independent read-only grader. Each methodology gets the artifact it produces, what it can prove, what it cannot
prove, how it would appear as an executable check inside the grader, and its known failure modes when grading.

Rules observed: no percentages. `UNKNOWN` marks anything not verified in this session. No citation is asserted
beyond files read or commands run here. Grading weights, nondeterminism repetition and aggregation, mutation
depth, model-based testing applicability and the adversarial submission threat model are `UNKNOWN` in the epic
and remain `UNKNOWN` here. No paper, book, standard or tool version is cited. Tool names appear only where the
tool is standard to the language or where its presence in the grader image is explicitly marked `UNKNOWN`.

Source provenance: the epic direction document `cmd/dagrun/docs/research/epic-traceability-autograder.md` was read
in full at 2026-11-12T11:21Z. By 11:23Z that file and its siblings `traceability-closure.md`,
`assignment-contract-proposal.md`, `agileplus-surface.md` and the `tools/` profile directory had been removed
from disk by a concurrent lane. They were untracked files. Statements attributed to them reflect the 11:21Z read.
Everything under "Verified local artifacts" was re-verified at 11:25Z and 11:26Z and still exists.

## Verified local artifacts

- `cmd/dagrun/internal/plan/plan.go:55-62` : `Artifact` struct with `MinBytes`, `MustContain`, `MustMatch`,
  `MinCount`, `AllowEmpty`.
- `cmd/dagrun/internal/plan/plan.go:252-264` : default expectations, e.g. `INTENT.md` `MinBytes: 300` plus
  `MustContain: ["Acceptance"]`, `SPEC.md` `MinBytes: 400`, `RESEARCH-<slug>.md` `MinBytes: 500` plus
  `MustContain: ["## Sources"]`.
- `cmd/dagrun/internal/verify/antigaming.go` : `PlaceholderFindings(name string, content []byte) []KindResult`;
  markers TODO, TBD, FIXME, XXX, lorem ipsum, placeholder, coming soon, not implemented; code-fence skipping.
- `cmd/dagrun/internal/verify/kinds.go` : `KindCheck`, `PlanKindCheck`, `KindResult`, `whenThenRE`
  (`(?is)\bwhen\b.{0,400}?\bthen\b`), `reqIDPattern` (`(?i)\b(REQ-\d+|R\d+)\b`), per-kind checks including
  `checkSPEC` and `checkTEST`, helpers `hasStatement` and `hasWord`.
- `cmd/dagrun/internal/verify/limits.go` : `checkGlobCap`, `checkMustMatchLen`, `checkMustContainLen`.
- `cmd/dagrun/internal/verify/verify.go` : `ArtifactResult`, `CheckResult`, `Report`, `Node`, `PlanNode`,
  `Satisfied`, `checkArtifact`, `runCheck` (executes a command under a timeout), `isProseArtifact`.
- `cmd/dagrun/internal/verify/fuzz_test.go` : existing fuzz harness, `fuzzDeadline = 2 * time.Second` bounding
  one artifact or kind check.
- `cmd/dagrun/internal/agileplus/agileplus.go` : "an artifact contract is NEVER invented", `Unmapped`,
  `FromJSON`, `ToPlan`, `Conflicts`, `contractDiff` (names the first thing that would change a node's
  verification), `executableCheck`.

## 1. Specification by example (SbE)

**(a) Artifact.** Concrete examples, each a named input plus its expected observable output. In the epic this is
the `scenario` entity (`SC-n`) with `given`, `when`, `then` and `observable_surface`, bound to requirement ids.
Prose plus a binding table, not code.

**(b) Can prove.** That a named example behaves as specified on the recorded build, toolchain and environment.
Regression against a frozen example set. Traceability completeness of the binding graph, if the binding itself
is checked.

**(c) Cannot prove.** That the examples cover the requirement space: examples sample, they do not quantify.
Absence of unhandled input classes. Semantic correctness of the contract, since the examples come from the same
requirement reading as the implementation. Generalization: a submission that special-cases every example passes.

**(d) Executable check in a grader.** Each example is a `check` record with `id`, `tier` (public `PT-n` or
private `HT-n`), `runner` (shell command or test entry), `timeout`, `determinism_class` and `expected_signal`.
The grader runs the private tier, captures exit code, stdout digest, duration and environment digest, and treats
missing evidence as FAIL. Example identity must survive freeze, so the grader compares the packet revision's
scenario set hash.

**(e) Failure modes.** Gaming: a submission hard-codes outputs for the visible public examples, so the private
tier must be withheld from the packet directory entirely, not merely hidden by naming. Spec drift: examples
written before the requirement settled diverge from the requirement text, and grading binds to examples rather
than to the requirement, so a grader can pass a submission that violates the requirement it was written from.
False confidence: example count read as coverage. Flakiness: environment-dependent outputs, so determinism class
must be declared per check and the repetition and aggregation policy for probabilistic and environmental checks
is `UNKNOWN` in the epic. Partial local mitigation: `PlaceholderFindings` catches stubs, not example-specific
hard-coding.

## 2. Design by contract (preconditions, postconditions, invariants)

**(a) Artifact.** A per-operation contract: preconditions on entry, postconditions on exit, and class or module
invariants across operations. This shape exists locally as `plan.Artifact`
(`cmd/dagrun/internal/plan/plan.go:55-62`) and as per-kind contracts in `cmd/dagrun/internal/verify/kinds.go`.

**(b) Can prove.** That a well-formed input satisfies preconditions, that a successful operation establishes its
postconditions, and that invariants hold at check points. Structural properties of the submission's artifacts and
declared interfaces, which is stronger than "the example output matched". A violation is attributable to a named
obligation rather than to an opaque diff.

**(c) Cannot prove.** That the postcondition set is complete or the invariant set captures what matters.
Preconditions that are never checked are decoration. Nothing about code paths that bypass the guarded operation.
Semantic correctness of the contract itself, which the epic's SCTBDD mapping already states.

**(d) Executable check in a grader.** Two layers. Contract checks on the submission workspace: `checkArtifact`
in `cmd/dagrun/internal/verify/verify.go` evaluates the `Artifact` predicates, and `KindCheck` /
`PlanKindCheck` in `kinds.go` evaluate the per-kind contract. Contract checks on the submission's own code: a
check record whose runner is a test entry asserting preconditions and invariants around the operation under
test. Both emit a `CheckResult` through `runCheck`, with the same exit-code and stdout-digest evidence shape.

**(e) Failure modes.** Gaming: predicate-based artifact checks are structurally gameable, because they only ask
whether a file exists and contains a string, so `MinBytes` and `MustContain` are satisfiable by padding. The
local mitigation is `PlaceholderFindings`, but padding with non-placeholder prose still passes. `AllowEmpty` is
the deliberate exception: an artifact declaring it is still placeholder-checked, so empty is honest and a stub is
dishonest, the right split but only for documents. Invariants checked in one place are trivially bypassed. False
confidence from a large set of trivially-true postconditions. Flakiness is lower than for examples, but
`MustMatch` regexes over large inputs can be slow, and `cmd/dagrun/internal/verify/limits.go` exists to bound
that. Spec drift: contracts written by the party that writes the implementation drift toward it, and the freeze
protocol plus human approval is the control.

## 3. BDD (Gherkin, three amigos, living documentation)

**(a) Artifact.** Executable scenarios in Gherkin form: `Feature` containing `Scenario` or `Scenario Outline`,
each with `Given`, `When`, `Then` and optionally `And`, plus step definitions binding prose to code. The "three
amigos" practice is a collaboration model; the artifact it leaves behind is the same executable scenario set.
"Living documentation" claims the scenario suite, run against the real system, is the reference documentation.

**(b) Can prove.** That the specified behaviors are implemented at the level of detail the scenarios describe. That
the prose and the code agree, which SbE alone does not, because step definitions are code that must exist and
resolve. Traceability when scenario ids bind requirement ids, which the epic requires: every scenario binds at
least one requirement, and every requirement is reachable from at least one check or explicitly marked `unverified`
with a reason.

**(c) Cannot prove.** That the Gherkin prose is the right prose. Step definitions can be stubs, so a green suite
can mean the steps assert little. Scenario coverage of the requirement space. Accuracy of documentation beyond the
scenarios, so "living documentation" is literally true only for what the scenarios cover. Semantic correctness of
the contract.

**(d) Executable check in a grader.** Each scenario's step definitions run as one check record whose `runner`
names the test entry, with `timeout`, `determinism_class` and `expected_signal` as the exit code. Because the
scenario binds requirement ids, the grader can emit a requirement-level report by projecting check results up the
binding graph. A local structural equivalent exists: `whenThenRE` in `cmd/dagrun/internal/verify/kinds.go`
recognises a when/then shape in a `SPEC` artifact, and `reqIDPattern` recognises requirement ids of the form
`REQ-n` or `R-n`. Those are static shape checks over prose, not executable scenarios, and the epic records that
limitation.

**(e) Failure modes.** Gaming: step definitions that assert nothing. A scenario whose steps are only
`Given`/`When`/`Then` with no assertion passes, and whether the grader can detect that depends on a
step-quality check that is `UNKNOWN` in this epic. Another gaming surface is step definitions that reimplement the
submission's logic, so the test agrees with the implementation by construction. Spec drift is systemic: prose and
code are bound through steps, so a changed step silently changes the meaning of the prose, and the freeze
protocol's content hash over canonical serialization catches that only if step text is part of the hashed content,
which is `UNKNOWN`. Flakiness is higher than for raw examples because steps often carry setup state. False
confidence: a fully green Gherkin suite reads as a complete specification while covering only the written
scenarios.

## 4. ATDD (acceptance-test-driven development)

**(a) Artifact.** An executable acceptance test written before the implementation and bound to an acceptance
criterion. A test file plus the binding from criterion to test, and the practice is that the test is red before
implementation and green after. In the epic this is the `check` entity with `tier` and `expected_signal`, and
the epic's SCTBDD mapping names `executableCheck` in `cmd/dagrun/internal/agileplus/agileplus.go` as the
existing ATDD-shaped mechanism.

**(b) Can prove.** That a named acceptance criterion holds for the submission. This is the closest of the eight
to the epic's closure definition, which requires the requirement to scenario to check to evidence chain to be
fully traversable with no orphans. That acceptance criteria are executable rather than prose, provided the
grader's own negative controls fire, since NC-001 empty submission and NC-002 no-op submission must FAIL.

**(c) Cannot prove.** That the acceptance criteria are the right ones, that they cover the requirement space, or
that the implementation generalises beyond the criteria. Semantic correctness. That an untestable criterion was
handled correctly: such a criterion either cannot be expressed as a check or is expressed as a weak one, and the
epic records prose criteria as `Unmapped` rather than silently passing them.

**(d) Executable check in a grader.** This is the native shape of the epic's check record. The acceptance test is
the `runner`, `expected_signal` is the asserted exit code or output predicate, and `tier` decides public
visibility. The private tier is the grading tier. Evidence per check is exit code, stdout digest, duration and
environment digest, and a check with no captured evidence is FAIL, never PASS with a warning, which is NC-004.
Determinism is declared per check, and the number of repetitions and the aggregation for probabilistic and
environmental checks is `UNKNOWN`. Two grades of the same submission against the same revision must produce
identical result records under hermetic conditions, which is what makes ATDD gradeable rather than merely
descriptive.

**(e) Failure modes.** The dominant gaming surface is the acceptance test being written to the submission rather
than the submission to the criterion, which is why the grader must be independent, read-only, and must not share
a session with the agent that produced the submission. A second surface is a submission that satisfies the
criteria while violating requirements the criteria only partially express, and the epic's answer is that grading
never mixes revisions and that a grader result references exactly one revision hash and one private suite hash.
Spec drift is the criterion-to-requirement mismatch: criteria are prose and can be reworded without changing
behavior. Flakiness is the environmental-dependence problem of SbE again, and the epic's fix is incomplete
because that policy is `UNKNOWN`. False confidence: a red-then-green discipline is invisible to the grader, which
sees a green run and cannot tell whether the test was written before or after the code, so ATDD's ordering
benefit is lost in grading unless the grader also checks modification order, which the epic does not specify.

## 5. Consumer-driven contract testing (Pact-style provider/consumer verification)

**(a) Artifact.** A pact file per consumer-provider pair: a recorded set of interactions, each an example request
with the response the consumer expects. The provider verifies every pact it is a party to. The artifact is the pact
file plus the provider verification run.

**(b) Can prove.** That a provider honours the requests and responses its consumers actually depend on. That the
two sides agree on wire format and on the semantics of the recorded interactions. That a provider change breaking
a consumer is detected without the consumer's own suite being run against it.

**(c) Cannot prove.** That the provider is correct for cases no consumer exercised. The consumer's own behavior is
correct: only that the provider met the recorded expectation. Anything about a consumer that was never onboarded,
and pact files can be written by hand to match a broken provider. Semantic correctness of the contract beyond the
recorded interactions.

**(d) Executable check in a grader.** The grader treats the provider side as the student submission and the
frozen consumer expectation as the private suite. The check record's `runner` invokes the provider's verification
step over the pact expectations, with `expected_signal` as exit code. Two local mechanisms map onto this. The
AgilePlus to dagrun export/import bridge in `cmd/dagrun/internal/agileplus/agileplus.go` carries the rule "an
artifact contract is NEVER invented", with `Unmapped` holding work packages that could not be represented
faithfully, and `contractDiff` naming the first thing that would change a node's verification, the same shape as
a pact mismatch. And `cmd/dagrun/internal/verify/verify.go` provides `Satisfied`, the predicate the grader can
evaluate per node without executing it. Whether pact tooling is available in the grader image is `UNKNOWN`.

**(e) Failure modes.** Gaming is the largest here: a submission can write a pact file that matches its own
broken behavior, and a grader that accepts submission-authored pacts verifies nothing. The pact must come from
the frozen private side, never from the submission. A second surface is a submission that special-cases the
recorded interaction. False confidence: a passing pact suite is a strong signal about a narrow boundary and reads
as broad coverage. Spec drift: pacts pin one direction of one interface, and an interface change not expressed as
a consumer expectation change slips through. Flakiness is low if pacts are replayed, but replay harnesses that
replay live timing can reintroduce it. The rule that a check with no captured evidence is FAIL protects here
too, since a pact run that produced no result must not be read as a pass.

## 6. Model-based testing

**(a) Artifact.** An abstract model of the system under test, expressed as states, transitions, inputs and
invariants, plus a generator producing concrete test sequences from the model and an oracle deciding whether an
observed execution conforms to the model. The artifact is the model plus the generated sequence corpus plus the
conformance checker.

**(b) Can prove.** That every reachable state in the model is reachable in the implementation, that no observed
execution leaves the model's state space, and that invariants hold across generated sequences. Properties over many
executions rather than one example, which makes it the closest of the eight to exhaustive checking over a bounded
space. Sequence-dependent bugs that isolated examples miss.

**(c) Cannot prove.** That the model is the right model: the oracle is only as good as the model, and the model
is written by the same party that may write the implementation. Anything about states outside the modelled space,
and a finite model covers only what was modelled. Semantic correctness of the underlying requirement.

**(d) Executable check in a grader.** The model and its generator become a private check runner whose `runner` is
the model-based driver and whose `expected_signal` is a conformance verdict rather than a plain exit code. The
grade evidence would then need the generated sequence count and the conformance result, which the epic's evidence
schema does not currently have a field for. `determinism_class` must be `deterministic` and a fixed seed must be
recorded, since a generator with a random seed makes the run irreproducible and breaks the requirement that two
grades of the same submission against the same revision produce identical result records. Which model-checking or
model-based-testing tooling would be available in the grader image is `UNKNOWN`. The epic's open question 12,
model-based testing applicability, is `UNKNOWN` and this document does not resolve it.

**(e) Failure modes.** Gaming: a submission that ships a model trivially satisfied by its own behavior, or a
grader that trusts a submission-supplied model. The model must be part of the frozen private side. A second
surface is a state space the submission drives out of early, so the generator reaches few states and reports
success. Spec drift is severe: the model is a second specification that can disagree with the requirement, and
because the epic requires every requirement to be reachable from a check, a model-only check must still bind
requirement ids or it becomes an orphan. Flakiness enters through generator randomness and through any model step
depending on wall-clock or concurrency. False confidence: a bounded model that is exhaustively searched can still
miss every property not written into it, and "all states covered" invites reading that as proof of correctness,
which the epic explicitly refuses.

## 7. Mutation testing as suite qualification

**(a) Artifact.** A mutation score over the test suite: mutants are injected into the code under test, the suite is
re-run, and a surviving mutant is a behaviour the suite does not detect. The artifact is the mutant set, the
survivor list, and a per-mutant kill decision.

**(b) Can prove.** That the test suite has discriminating power over the mutations actually applied. It qualifies
the suite rather than the submission, which is what a grader needs: a suite that kills no mutants cannot
distinguish a correct submission from a broken one. That specific classes of defect are caught, including inverted
conditions, deleted branches and boundary-value changes.

**(c) Cannot prove.** That the suite is adequate for defects outside the mutation operators chosen. Semantic
correctness of the submission: a high mutation score says nothing about whether the tested behaviors are the right
ones. Anything about requirements that no check covers.

**(d) Executable check in a grader.** Mutation testing runs against the grader's own private suite and harness
code, not against the student's test suite, because the student's suite is not the instrument of grading. The
epic already has a minimal form of this as negative control NC-003, the inverted-logic sentinel, which must FAIL,
plus NC-006, suite integrity, where a hash mismatch aborts grading. A fuller form would run mutants over the
private suite and fail grading if surviving mutants reach the checks that carry score weight. Which
mutation-testing tool would be present in the grader image is `UNKNOWN`, and the epic's open question 13, mutation
testing depth and score, is `UNKNOWN` and this document does not resolve it.

**(e) Failure modes.** Gaming: a submission cannot game a mutation run over the grader's private suite directly,
but it can game the grader's harness code if the harness is inside the graded surface, so the harness must be
excluded from the submission's allowed scope. False confidence is the principal risk: a good mutation score can be
reported as though it certified the submission, when it certifies only the suite. Spec drift: mutants test the
code against the suite, not against the requirement, so a suite and its implementation can drift together. Flakiness:
mutation runs multiply suite executions, so any flaky check produces spurious survivors and the score becomes
noise, which is why determinism class per check must precede mutation analysis. Cost: the runs are multiplicative
and the epic specifies no budget. Equivalence caveat: some mutants are equivalent, meaning no test can
distinguish them, so a low score is not automatically a weak suite. The epic records NC-003 as covering only the
inverted-logic case, so full mutation coverage is explicitly out of scope today.

## 8. Property-based testing and its relation to contract invariants

**(a) Artifact.** A property statement, a generator of inputs, and a shrinking mechanism that reduces a failing
input to a minimal counterexample. The artifact is the property plus the generator plus any recorded
counterexample.

**(b) Can prove.** That a stated property holds over a generated input space, a quantified claim rather than an
enumeration of examples. This is the natural executable counterpart of a contract invariant, because an invariant
is a universally quantified statement over all reachable states while an example is an existential statement over
one. Algebraic and metamorphic relations that no hand-written example would find.

**(c) Cannot prove.** That the generated space covers the relevant space. A generator that produces only
well-formed inputs proves nothing about malformed input. That the property is the right property, since properties
are usually derived from the same requirement reading as the implementation. Semantic correctness beyond the
property as stated.

**(d) Executable check in a grader.** A property test becomes a check record whose `runner` is the property test
entry, whose `expected_signal` is the exit code, and whose `determinism_class` is `deterministic` with a recorded
seed. The seed must be pinned in the grade record alongside the environment digest, because the epic requires two
grades of the same submission against the same revision to produce identical result records, and an unpinned seed
breaks that. A property test that reduces to a counterexample produces evidence richer than an exit code, while
the epic's evidence schema records only exit code, stdout digest, duration and environment digest, so the
counterexample survives only inside the stdout digest unless the schema is extended, which is `UNKNOWN`. The Go
standard library provides fuzzing through `go test -fuzz`, and this repository already uses that shape in
`cmd/dagrun/internal/verify/fuzz_test.go`, where `fuzzDeadline = 2 * time.Second` bounds one artifact or kind
check so a pathological regex or a runaway loop fails the iteration instead of stalling the fuzzer. That harness
is a property-style check over artifact predicates and kind checks, not over student behavior, but it is the local
precedent for the pattern.

**(e) Failure modes.** Gaming: a submission that ships a property test asserting nothing, or one whose generator
is empty. A generator that yields zero inputs makes the property vacuously true, the sharpest gaming surface in the
whole set because vacuous truth is a pass. Detecting it requires a minimum generated-case count, which the epic's
evidence schema does not carry, so that check is `UNKNOWN`. Spec drift: a property can be trivially true of a
broken implementation, for example when stated over the implementation's own outputs rather than over an
independently derived relation. Flakiness is low for a deterministic generator with a pinned seed and high for an
unpinned seed or with time and concurrency in the property. False confidence: a property test explores broadly and
is often read as stronger than many examples, which is true of the property and not of the coverage of the
requirement space. Runtime cost is real: property tests with many cases can exceed a check timeout, so the
timeout must be set per check and the failure reported as FAIL with the recorded evidence, not as a missing
result.

## Cross-cutting conclusions

1. The epic's native check record is an ATDD-shaped artifact, and that shape supports every one of the eight
   methodologies as a different kind of `runner` plus a different kind of `expected_signal`. The methodologies are
   not competing designs for the grader; they are competing sources of `runner` content and of what the grader
   can conclude.
2. What the grader can prove is bounded by the frozen revision hash and the private suite hash. Every methodology
   here strengthens what the suite discriminates, and none strengthens the correctness of the contract itself,
   which the epic already states.
3. Vacuous-truth gaming is the shared failure mode across SbE, BDD, ATDD, property-based testing and model-based
   testing, and it is the case negative controls NC-001, NC-002 and NC-003 exist to catch. The controls must
   themselves be able to fail on a correct grader, so their quality is a prerequisite for trusting the suite they
   qualify.
4. Three policy gaps in the epic materially limit what any of these methodologies can deliver at grading time: the
   repetition and aggregation policy for probabilistic and environmental checks, the mutation depth and score, and
   model-based testing applicability. All three are `UNKNOWN` and appear as open questions 7, 12 and 13.

## What remains UNKNOWN after this review

- Grading weights between requirement-bound checks and the rest.
- Nondeterminism repetition count and aggregation, and who arbitrates variance being a test defect versus a
  submission defect.
- Whether the frozen content hash covers step definitions and generators, not only prose and scenario text.
- Whether pact tooling, mutation-testing tooling, or model-based testing tooling is present in the grader image.
- The adversarial submission threat model.
- Whether the grade evidence schema will be extended to carry generated-case counts and reduced counterexamples.
