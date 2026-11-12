# Tessl CLI (tesslio/cli)

## What it is

Tessl is an "Agent Enablement Platform": a registry and package manager for agent skills and
plugins, plus governance, evals, observability, and a conversational Tessl Agent. It started in
September 2025 as a spec-driven-development product set (the Tessl Framework plus the Tessl Spec
Registry) and has since repositioned toward skills.

- Repo: https://github.com/tesslio/cli ("Tessl - your Agent Enablement Platform")
- Docs: https://docs.tessl.io (machine index: https://docs.tessl.io/llms.txt)
- Registry: https://tessl.io/registry
- Measured 2026-11-11 via GitHub API: 71 stars, last push 2026-03-05T16:57:28Z. License: GitHub
  reports NOASSERTION (no SPDX identifier detected). GitHub releases: none (404).
- Install: `curl -fsSL https://get.tessl.io | sh`, then run `tessl` in the project directory.

Six documented components (https://docs.tessl.io): Registry & package manager, Governance, Evals,
Observability, Context and Findings, Tessl Agent (open beta).

## Artifact model (exact paths/filenames it writes)

Exact on-disk paths are UNKNOWN - the CLI README is 33 lines and the docs pages read did not list
file names.

What is documented:

- Tessl Framework (closed beta as of 2025-09-16) makes agents create three resource types:
  "Plans: Tessl makes agents create a written plan of action before embarking on a big change ...
  it will get updated as it executes, serving as an audit trail"; "Specs: Agents will capture what
  they intend to build in a clear spec before coding"; "Tests: ... Tessl lets you enrich specs with
  tests, which verify the code matches the intent."
- Tessl Spec Registry: spec packs are added "as project dependencies, and install them locally as you
  would a software library"; the registry "contains over 10,000 Usage Specs ... Each is versioned to
  match the library it's describing".
- Skills and plugins are versioned artifacts in the registry, rolled out like dependencies.
- Related repos: https://github.com/tesslio/code-review-action (GitHub Action publishing a native PR
  review), https://github.com/tesslio/pr-review-guardrails ("Evidence-first pull request review with
  independent critique, selective challenger review, and human handoff").
- CLI surface seen in the README: `tessl` (project init), `tessl feedback` (report issues).

## Traceability enforcement (does it bind requirement -> test -> code; enforced or advisory; what breaks the chain)

For the shipped CLI: NONE documented. The current public docs describe skills, governance and
evals - not requirement traceability.

For the (closed-beta) Framework, the declared mechanism is the strongest in this set: "Tessl lets
you enrich specs with tests, which verify the code matches the intent. Tests serve as powerful
regression tests, ensuring you don't break existing functionality." That is spec -> test -> code
with the test attached to the spec as its guardrail.

What breaks the chain: the Framework is closed beta, so the enforcement details (how tests are
bound to a spec, how failures are surfaced) are not public. The Spec Registry is explicitly about
external knowledge ("The Spec Registry tackles the challenge of giving agents the information they
need, and is not in the codebase"), so it does not contribute to in-repo traceability.

## Interface surface (CLI / MCP / SDK / IDE plugin / slash commands)

- CLI: `tessl`, `tessl feedback`; installed via the `get.tessl.io` shell script.
- MCP server: "We combine agent steering with deterministic logic within our MCP tools to ensure
  it's your agent that works harder - not you." The MCP tool list is UNKNOWN.
- Conversational agent: "Tessl Agent - A conversational agent that drives the platform and
  autonomously monitors and improves your agentic setup. Runs alongside your existing agents (open
  beta)."
- CI integration: the `code-review-action` GitHub Action and `pr-review-guardrails`.
- Skills/plugins are consumed by any agent: "Agent-agnostic. Skills and plugins work across every
  popular coding agent."

## Interactivity (multi-turn refine+freeze conversation, or one-shot generate)

Both, at different layers. At the framework layer, the agent works interactively under MCP
steering: plans are "review and edit"-able before execution and updated during execution. At the
platform layer, Tessl Agent is a conversational agent (open beta) that monitors and improves the
setup. The registry is a plain package install - no conversation.

## External verification (executes/verifies real artifacts, or only checks presence)

Externally computed evidence, but for skills rather than for student code.

- Evals: "Measure a skill or plugin's actual impact by running your agent on real-world tasks with
  and without the context. Every change ships with evidence instead of a guess."
- Governance: "Scan and score every skill against best practices and your own company standards,
  with Snyk security scoring built in ... backed by a full audit trail"; install and publish
  policies "enforce your standards across every workspace".
- Observability: "See where skills actually activate across agent sessions" by mining agent logs.
- Code review: the GitHub Action publishes a native pull-request review; `pr-review-guardrails`
  offers "Evidence-first pull request review with independent critique".
- For the spec layer: the Framework's tests "verify the code matches the intent", but the mechanism
  is closed beta and therefore not verifiable from public docs.

## Autograder fit (could it grade a school-assignment submission: prompt + test + stub + base scope? yes/no + why)

No, as shipped. The pieces that would matter (a spec that owns its tests; evals that run an agent
against a task with and without context; evidence-first PR review with independent critique) are
platform features aimed at engineering teams, not a course grader. A team could build a grader on
top of Tessl's plan/spec/test model, but the public product does not provide rubric scoring, a
submission envelope, or a pass/fail signal for coursework.

## Gaps for our use case

- The Framework - the part with the spec->test->code model - is a closed beta with public docs
  limited to launch posts; the tool surface and file layout are UNKNOWN.
- Product drift: the launch was a spec registry and framework; the 2026 docs describe a skills
  registry and governance platform. Any design that depends on Tessl's spec model depends on a
  closed beta.
- The public CLI repo is small (71 stars), has no releases, and reports no SPDX license identifier.
- Commercial service with account, RBAC, and policy infrastructure - heavier than a course harness
  needs, and it needs network access to the registry.
- Nothing produces a machine-checkable requirement-coverage report over a learner's repository.

## Non-goals (what it deliberately does not do)

- It does not replace the coding agent: the framework "integrates with your agent of choice"; Tessl
  Agent "runs alongside your existing agents".
- The registry is not in-codebase knowledge by design: "The Spec Registry tackles the challenge of
  giving agents the information they need, and is not in the codebase."
- It does not grade assignments or produce course rubrics.
- It does not claim the open-source tools are inferior: it is positioned as "Open, no lock-in ...
  writes your skills, rules, and config as plain artifacts in your repo".