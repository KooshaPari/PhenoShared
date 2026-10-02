# PhenoShared: preservation findings and proposed SDK direction

Date: 2026-09-18. Status: **review draft; not accepted architecture or migration approval**.

Subject repository ID: `1200273587`.
Observed source: `a0147e562a7fd62a9a5f198567409da3040d01f9`.
Earlier checkpoint: `345c602d789649a008c003fd19d0773c7cd8f846`.

This record is based on Git objects, manifests, selected historical file comparisons and bounded source inspection. It does not rely on the root README as an inventory. No native builds, package installation, full recursive semantic inventory, donor restore drill, or all-consumer parity tests were executed. The documents and metadata below are evidence of their contents, not proof that every described behavior works.

## 1. Immediate preservation verdict

The earlier checkpoint is an ancestor of the observed head. GitHub's comparison returns `ahead`, 62 commits ahead and zero behind, with that checkpoint as merge base. This rules out wholesale replacement of that observed ancestry interval. It does **not** establish preservation of every donor branch, uncommitted file, external object or accepted capability.

[Compare these exact commits](https://github.com/KooshaPari/PhenoShared/compare/345c602d789649a008c003fd19d0773c7cd8f846...a0147e562a7fd62a9a5f198567409da3040d01f9).

The comparison includes removal of `.gitmodules` and numerous root entries. A direct check establishes that the old `BytePort` entry was a submodule pointing to `95f01a842551ec76ff7fa067e8d8d9737d468af9`, not a full nested source directory. Do not classify every removed entry as lost source without inspecting its Git mode and successor.

[Old BytePort entry](https://api.github.com/repos/KooshaPari/PhenoShared/contents/BytePort?ref=345c602d789649a008c003fd19d0773c7cd8f846).

GitHub's compare API returns at most 300 changed-file records. Its returned list is not a complete large-tree diff; full manifests or a read-only local Git diff are still required for exhaustive classification.

## 2. Confirmed archival mutation

The patch `.archive/Repos-phenodocs-2026-07-15/patches/0001-feat-add-L7-001-intent-boundary-snapshot-docs.patch` has different blobs at the two checkpoints:

- Earlier: `f50e84da4edc7b0fe75de63480336287660755e0`.
- Current: `44b147c158c7fe3b5e6a285624f4197e95fc596f`.

Its `KooshaPari/phenotype-registry` provenance string was replaced by `<REDACTED>/phenotype-registry`, including within patch content. The earlier bytes remain reachable. The current copy is not an untouched archival original, even though the patch retains its original index headers.

[Earlier patch](https://github.com/KooshaPari/PhenoShared/blob/345c602d789649a008c003fd19d0773c7cd8f846/.archive/Repos-phenodocs-2026-07-15/patches/0001-feat-add-L7-001-intent-boundary-snapshot-docs.patch) and [current patch](https://github.com/KooshaPari/PhenoShared/blob/a0147e562a7fd62a9a5f198567409da3040d01f9/.archive/Repos-phenodocs-2026-07-15/patches/0001-feat-add-L7-001-intent-boundary-snapshot-docs.patch).

A sanitized derivative can be useful, but it needs its own identity, declared transform and source linkage. Do not re-expose real secrets, blanket-revert privacy work, or rewrite history on the basis of this note. Preserve access-controlled originals and classify the affected outputs. Identify broken source locations, commands, attribution and restore artifacts independently.

## 3. The current root is a mixed inherited control surface

| Actual file | Observed declaration | Consequence |
|---|---|---|
| `AGENTS.md` | Calls itself the `phenotype-omlx` agent contract; points to that clone and `perf-core/` | An agent entering PhenoShared can receive another product's workspace instructions |
| `pyproject.toml` | Packages `pheno-harness-bench`; broad package discovery and historical Harbor/Portage references | This is not a complete declaration of all retained Python capabilities |
| `package.json` | Names `phenodocs`; VitePress commands and `packages/*` workspaces | Root JavaScript checks target the documentation product, not automatically all nested applications |
| `Cargo.toml` | Explicit member list centered on substrate, Fabric and selected shared crates | Root workspace success does not establish every retained subtree's build or behavior |

These are observations, not an instruction to delete donor code. Reconcile the subject identity and actual package/build ownership before broad refactoring. Keep PhenoDocs and AgilePlus reusable tooling rather than turning this workspace into their universal mutable portfolio state.

Pinned files: [AGENTS](https://github.com/KooshaPari/PhenoShared/blob/a0147e562a7fd62a9a5f198567409da3040d01f9/AGENTS.md), [Python manifest](https://github.com/KooshaPari/PhenoShared/blob/a0147e562a7fd62a9a5f198567409da3040d01f9/pyproject.toml), [JavaScript manifest](https://github.com/KooshaPari/PhenoShared/blob/a0147e562a7fd62a9a5f198567409da3040d01f9/package.json), [Cargo manifest](https://github.com/KooshaPari/PhenoShared/blob/a0147e562a7fd62a9a5f198567409da3040d01f9/Cargo.toml).

The Python manifest also contains a CLI pytest option `--cov-fail-under=0` alongside a report configuration of `fail_under=65`. This configuration must not be presented as the required independent 85% assurance envelope. No coverage was measured in this review.

## 4. Structural inventory boundary

The complete non-recursive `crates/` tree is `50fa11c02db82a3eb8324daf5f6797ce5d485ee3` (`truncated:false`). Transcription of its direct child directory names yields **363 directories**. This is not 363 verified Rust packages: the directory includes `.github`, `src`, `tests`, nested donor workspaces and multiple languages.

The root Cargo manifest explicitly names **74 member paths**: 71 beneath `crates/`, two fake-engine test tools and one full-demo example. This is **not** the resolved Cargo membership count: eligible in-tree path dependencies can join implicitly, and nested/excluded workspaces require separate handling.

Observed name families include 23 `agileplus-*`, 43 `focus-*`, 20 `fabric-*`, 12 `sharecli*`, 16 `pheno-compose-*`, nine connector directories, eight eye-tracker directories, ten substrate-prefixed directories, six team-communication directories, five Pine directories and three Tokn directories. Names identify inventory leads, not verified features or correct ownership.

Other source-bearing or custody areas include `packages/`, `python/`, `libs/`, `apps/`, `src/`, `bindings/`, `go-fabric/`, `agileplus*/`, `forge-daemon/`, `forgecode-fork/`, `phenotype-gfx/`, `infrakit/`, `phenotype-infrakit/`, `hfscope/`, `kernels/`, `serving/`, `native/`, `linux-client/`, `windows-client/`, `tools/`, `tooling/`, `absorption/`, `shelf-infra/`, `repos/`, `.archive/`, `_archived/`, `archive/`, `archives/` and `historical/`.

The inspected `packages/` tree has these nine child directories: `auth`, `design-tokens`, `docs`, `github-fetcher`, `pheno-core`, `pheno-llm`, `pheno-resilience`, `site-base`, `ui`.

The root preservation manifests describe particular older recovery captures, especially `crates/agile-plus/` and `crates/hexa-kit/`. They expressly leave parity and parent-boundary decisions open. They are not a blanket certificate for all later absorptions.

[Crates tree](https://api.github.com/repos/KooshaPari/PhenoShared/git/trees/50fa11c02db82a3eb8324daf5f6797ce5d485ee3), [packages tree](https://api.github.com/repos/KooshaPari/PhenoShared/git/trees/8072df71cf99fd30a1ecb17a7ac5f537870f0960), [preservation manifest](https://github.com/KooshaPari/PhenoShared/blob/a0147e562a7fd62a9a5f198567409da3040d01f9/PRESERVATION_MANIFEST.md).

## 5. Proposed SDK direction: progressive control without mandatory layers

The target is a set of independently consumable capabilities with progressively more policy available. A consumer must be able to choose a direct primitive, a safe low-level interface, a domain capability, an adapter, a policy bundle or a complete recipe. It should not have to traverse every layer.

| Level | Responsibility | Must not silently require |
|---|---|---|
| Environment boundary | Native calls, established library integration, FFI | A GUI, network service or portfolio account |
| Safe primitives | Resource ownership, buffers, IDs, clocks, cancellation | Application-specific policy or a global runtime |
| Capability contracts | Explicit operations, errors and invariants | A compulsory implementation/provider |
| Adapters | Specific storage, OS, protocol, harness or renderer | Unrelated providers or platform dependencies |
| Policy/composition | Retry, permissions, budgets, persistence choices | Duplicate policy in every consuming product |
| Recipes/applets | Opinionated useful workflows and host integration | Irreversible lock-in to the recipe's defaults |

This is a graph of contracts and optional composition, not an infinitely deep inheritance hierarchy. A renderer, database, agent harness and process supervisor may have different useful layering depths. Sharing repository custody does not imply lockstep releases, shared databases or a mandatory daemon.

Use maintained external implementations or improve the authoritative owned capability before handrolling a second version. A wrapper is justified by policy, adaptation, containment or replaceability; a one-to-one renaming layer is not automatically useful. Preserve current and credible future consumer requirements without speculative universal frameworks.

For each published capability record: owning package; public contract; current consumers; standalone build/install command; feature/OS profile; optional dependency closure; performance/compatibility constraints; test evidence; source lineage; patch/update policy; migration route; and known limitations.

Compare primitive and high-level usage through the same behavior/performance cases. The high-level route should reduce consumer work without obscuring cancellation, safety, state ownership, allocation or timing guarantees. Keep game-, media-, inference- and app-runtime dependencies optional for consumers that do not need them.

## 6. Required next evidence, in order

1. Capture a complete recursive Git path/blob/mode manifest at the pinned head and old checkpoints, preserving truncation/access warnings. Account for gitlinks, LFS pointers, nested repositories and ignored/dirty local state separately.
2. Enumerate every package manifest and its containing build universe; resolve Cargo members rather than equating the explicit list with the full workspace. Map native, Python, JavaScript, Go, FFI and standalone tools independently.
3. Build a donor-to-current capability ledger: original stable repository ID/ref/blob, current path/blob, declared transforms, included/excluded build status, consumer, test and restoration evidence. Distinguish archive custody from runtime integration.
4. Triage duplicate implementations by public behavior and consumers, not filename. Do not mass-delete or mass-activate every copied directory.
5. Choose a narrow foundation slice needed by an actual application. Qualify it both directly and through its intended higher-level recipe before generalizing the SDK layout.
6. Repair subject-specific root instructions/build discovery through separately reviewed changes. Preserve history and existing local work. Keep proposed decisions distinct from accepted contracts.

## 7. Execution and permission boundaries

The current product-shaping program permits at most five repositories in a state batch and at most two products in active shaping. Games, PhenoFabric, Melosviz and the research trio are deferred as products; their code remains part of preservation and dependency inventory where present here.

This note does not authorize deletion, source moves, donor retirement, force pushes, irreversible migrations, merge bypasses, new repositories, or lifecycle promotion. It is a new document on an isolated review branch. No live AgilePlus state transition was made or inferred.

There is no basis yet for a full-preservation, full-SDK-readiness, or native-product completion percentage. The completed result is a bounded source-backed diagnosis and proposed direction with explicit remaining evidence.

## References

- [Cargo workspace membership](https://doc.rust-lang.org/cargo/reference/workspaces.html): implicit path dependencies and explicit exclusions matter.
- [GitHub comparison limits](https://docs.github.com/en/rest/commits/commits): changed-file lists are bounded; do not certify a large tree solely from them.
