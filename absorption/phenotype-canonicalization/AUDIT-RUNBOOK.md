# Read-only audit and qualification runbook

## 1. Preserve and identify

Use an authorized existing checkout or isolated analysis clone. Never reset the user's worktree. Preserve dirty/untracked state; distinguish it from the remote source snapshot. Record repository numeric ID, full name, current default branch, worktree, resolved commit, shallow-history status, tool identity, acquisition date and visibility boundary. Names, descriptions and archive flags do not establish current lifecycle authority.

Safe local observations include:

```sh
git status --porcelain=v1
git rev-parse --verify HEAD
git rev-parse --is-shallow-repository
git ls-tree -r --name-only HEAD
```

Do not publish remote URLs containing credentials. Do not put credentials or personal paths in evidence. Preserve source identity without using a broad text replacement that damages package selectors, repository URLs or machine-readable data.

## 2. Inventory components rather than repository labels

Identify root and nested manifests, source entry points, published packages, executable services, docs/landing surfaces, workflow exports, generated outputs, vendored code, fixtures and historical material. Resolve one writer for each capability. Record whether a duplicate-looking path is a source, generated mirror, vendored upstream, migration copy, deliberately different implementation or unresolved lineage.

Run the included collector against a pinned commit:

```sh
python -I /absolute/path/to/packet/tools/audit.py \
  --repo /absolute/path/to/checkout --ref HEAD \
  --output /absolute/path/to/evidence/manifest-observations.json
```

It inspects selected manifests and workflow references. It does not parse full shell graphs, evaluate imports, install packages, examine every branch or prove runtime use. Its path exclusions are defaults requiring reconciliation with the actual component inventory. An excluded template can still be important if it generates future consumer code.

## 3. Trace history and migration claims

For relevant paths inspect introduction, rename/copy history, merge lineage, changes after the claimed migration and upstream provenance. Record whether history is complete before using negative conclusions.

```sh
git log --all --date=iso-strict --format='%H %ad %s' -- package.json pyproject.toml Cargo.toml .github
# --follow is meaningful for a single path; it is not whole-ecosystem lineage proof.
git log --follow --date=iso-strict --format='%H %ad %s' -- path/to/one/file
```

For suspected copies, compare complete content and relevant symbol/API structure, not just names or a matching import. Use patch identity and merge-base analysis when repositories share history. Preserve license notices and focused upstream patches. Review default branch, deployment/release refs and active work branches separately. A merged PR title does not establish the installed version.

## 4. Resolve dependencies and consumers

Build separate edges for runtime, build, test, generation, docs, assets, configuration and workflows. Start from actual manifests and lockfiles, then confirm entry-point reachability with the language's dependency/import tooling and controlled runtime evidence. Account for plugin registries, dynamic imports, generated bindings and feature flags.

After dependency/tool execution is authorized in an isolated environment, use the qualified package manager's frozen/locked resolution mode. For Cargo metadata, avoid a casual command that rewrites a lock or resolves a new dependency graph; use a pinned offline/locked workflow when the required dependencies are already present. Missing cached dependencies are blocked acquisition, not proof that the project has no dependency.

A declared shared dependency is not enough. Build/package its exact provider version, install it in a consumer without sibling checkouts or local shadows, and exercise a useful contract. Retain provider source, artifact, consumer lock, resolved binary/library and test identities.

## 5. Qualify each toolchain transition independently

**OXC lint:** map semantic obligations and rule selectors, not tool counts. Seed one representative violation for each required class. Confirm security/framework/custom/type-aware rules remain covered. Keep a residual runner only for exact unmatched obligations.

**Oxfmt:** compare representative files and parser validity; verify idempotence and intentional style changes. Account for embedded languages and plugins. Never run overlapping formatters without an explicit partition.

**Native TypeScript:** resolve package/version/binary. Verify each project's source set, cross-project references and emitted declarations where applicable. Vue/SFC/compiler-API obligations need their own adapters. Reproduce the multi-project counterexample with the selected compiler, then a real negative canary in every required project.

**Bun:** qualify installation, runtime and test-runner separately. Exercise native addons, lifecycle scripts, process shutdown, streams/TLS/subprocess behavior, snapshots/mocking, package packing and framework production builds as relevant. An upstream Node support contract is not erased by using Bun to install dependencies.

**uv/3.14t:** lock environment and interpreter build. Import the real production dependency set, then check both `sysconfig.get_config_var("Py_GIL_DISABLED")` and `sys._is_gil_enabled()`. Test races, concurrency and actual memory/time behavior. Do not force GIL-off on an unsupported extension to satisfy policy. Package minimum metadata can legitimately be older than the deployment interpreter.

**Lefthook:** inspect `lefthook validate` and the effective `lefthook dump` output, then installed hooks and configured `core.hooksPath`. Test staged/nested file selection. Shared configuration resolution must be pinned and reproducible. Mandatory CI checks cannot rely on users being unable to bypass hooks.

**MCP:** prove exact FastMCP/fork package identity. Exercise tool listing, schemas, invalid arguments, output validation, transport, authentication/authorization, cancellation, timeouts, concurrency, resource limits, shutdown and a real client. Do not equate a decorator/import/no-op stub with an operational server.

## 6. Qualify the verifier

Run negative controls against the final result path: a missing report, wrong source/evaluator revision, unavailable tool, malformed measurement, zero denominator, a skipped family, a real failed behavior, swallowed nonzero exit, changed evaluator, unauthorized/stale producer and consumer artifact mismatch.

Separate structural checks from trust. The included synthetic validator checks a limited record shape and independent floors; it does not fetch evidence, authenticate producers, prove freshness or protect itself from an authorized caller modifying its expected values. Integrate real evidence validation with the existing trusted assessment infrastructure.

Do not average coverage families together. Define the reviewed eligible inventory for each profile. A legitimate not-applicable decision requires evidence and authority; an empty suite is not a convenient substitute.

## 7. Qualify workflows where they actually run

Resolve provider by stable ID and current accessible name. Verify a real reusable workflow file exists under the provider's `.github/workflows`, exposes the intended inputs/secrets and has least-required permissions. Generate literal pinned consumer references. Check action/workflow version and dependency policy independently.

Use an authorized hosted consumer run to verify GitHub can call the provider, resolve required actions, access intended artifacts, and propagate real failure. A local YAML parser, a README link or an API 404 cannot substitute for that test. Record workflow source SHA, caller source SHA, run/job identity, selected permissions and retained result.

## 8. Measure duplication and actual savings

Separate authored domain code, common implementation, adapters, generated code, tests, documentation, vendored upstream and historical material. Use content/syntax/symbol comparison plus provenance and semantic review. Do not delete a suspected duplicate until its actual consumers, differences, licensing and ownership are understood.

Report product-local code removed, shared/adapter code added, whole-ecosystem ownership reduction, dependency closure, build/test cost and delivered capability. An extraction that shrinks one repository but increases total burden may be a loss. A distinct implementation can be valuable if its measured outcome justifies the cost.

## 9. Run bounded comparative experiments

Freeze inputs, constraints, target environment and evaluator before implementing alternatives. Include the baseline, current-language improvement and serious external/shared alternatives. Retain cold and warm measurements, repeated samples, failure cases and full boundary overhead. Compare at the actual concurrency/request distribution and hardware budgets.

Promote only a candidate that satisfies the required semantics, target support, packaging and consumer conformance. Keep failed or inconclusive experiments as evidence without automatically keeping their dependencies in the production tree.

## 10. Return and continue

Update the existing product/capability records and exact work package. Include observed source, authority, selected solution/exception, qualification state, evidence identity, changed source, actual consumer state and remaining unknowns. Preserve aliases for migrated IDs. Leave a restart packet with the next concrete action.

The full remaining audit includes actual branch/lineage analysis, installed consumer verification, current workflow execution, exhaustive applicable profile coverage and target-specific benchmarks. Do not label those complete from this packet's selected source review.
