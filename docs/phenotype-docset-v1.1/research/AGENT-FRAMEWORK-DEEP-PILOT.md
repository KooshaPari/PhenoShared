# Agentora capability: framework ergonomics and behavior study

First locate the actual surviving public framework API and build path. Historical Agentora staging, Cmdra's similarly named CLI framework and templates saying agentkit are not interchangeable. Bind implementation lineage and consumers before writing the benchmark.

## Candidate set

Direct model SDK plus ordinary code; OpenAI Agents SDK; LangGraph; CrewAI; Mastra (provisional interpretation of the user's Mastro); PydanticAI; Rig as a Rust-native baseline. Verify current versions, license terms, supported providers and published semantics. None is predeclared the winner.

## Shared application

Implement a bounded coding agent: inspect a repository, propose a plan, invoke typed tools, edit allowed files, run tests, handle tool/provider failures, respect a budget and sensitive-action approval, and emit a source-backed result. It must use a real fixture repository and meaningful tests, not print a prepared answer. Control the accessible files and side-effect sink.

## Change requests after version one

1. Add a typed tool, validation and a negative case.
2. Require explicit approval for a particular write.
3. Delegate to a specialist with separate budget and scope.
4. Persist and resume after a partially completed tool call.
5. Swap provider without changing the declared tool semantics.
6. Cancel during a long operation, preserving exactly the intended ownership.
7. Upgrade the framework and migrate state/configuration.
8. Embed the same agent inside a CLI and an existing application.

Record implementation time, concepts, docs lookups, wrong turns, glue and framework-specific coupling for each request. Keep raw work logs private when needed. Independent implementers or crossover assignments reduce home-framework familiarity bias.

## Adversarial behavior

Simulate failure just before a side effect, after the side effect but before its receipt, during persistence, after the budget is exhausted and after permission revocation. Capture whether the system retries, asks for reconciliation, duplicates the operation or fabricates completion. Durable execution does not imply universal exactly-once external effects. External model output is untrusted input, including tool-call schemas and instructions embedded in files.

## Three modes

Recorded/deterministic responses isolate framework overhead. Matched live runs assess user-task behavior using fixed provider/model/tool budgets. Idiomatic implementations assess whole-stack practical value. Do not blame a Python-vs-Rust result solely on framework architecture. Track cold start, first response, complete task latency, p95/p99 at accepted concurrency, peak/residual memory and task quality together.

## Decision products

Produce a capabilities-by-version table, measured results with uncertainty, change-request ergonomics matrix, failure-semantics matrix, retained custom-delta list and adoption recommendation. A framework wrapper or a small set of reusable policies can be a better result than preserving a full custom framework. Do not invent novel value merely to keep Agentora code alive.
