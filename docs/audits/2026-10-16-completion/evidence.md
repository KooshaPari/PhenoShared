# Evidence, provenance, inventory and limits

## Identity and method

Frozen GitHub main and local origin/main: `1448514e5692d8de6e40be8c7b67c6b5168f9fe2` (2026-10-15T03:53:41Z). Origin: https://github.com/KooshaPari/PhenoShared.git. Docs branch: `docs/completion-usability-20261016`, isolated worktree `/tmp/phenoshared-completion-20261016`. Original checkout `/Users/kooshapari/CodeProjects/Phenotype/repos/PhenoShared` remains on `tmp-pose-ci` with its untracked recovery/test/build artifacts preserved.

The earlier `/tmp/phenoshared-inventory-20261016.md` described 33,251 files and 85 literal members in the older checkout. This publication recomputes inventory from current main: **33,345 tracked files; 168 top-level tracked directories; 272 root files; 371 first-level crate directories; 333 first-level Cargo manifests; 980 recognized package/build manifests; 249 literal root workspace member paths.** These are different source denominators, not unexplained drift in completion. Literal member count is not `cargo metadata` resolved package count. No Cargo dependency resolution/build was performed.

Recognized declarations: Cargo.toml, package.json, pyproject.toml, go.mod, Package.swift, pubspec.yaml and .csproj. Manifest fields parse via Python TOML/JSON; other formats use text/source classification. Invalid JSON found: `crates/conft/crates/conft/typescript/packages/conft/package.json`. A package row can be a donor snapshot, fixture or template; no total product count is inferred. Every top-level directory/root file and first-level crate directory has a custody row, including components lacking a manifest. Dependencies/generated directories not tracked by Git do not enter denominator. Submodule/ignored/untracked contents are not silently inventoried as accepted source.

All package descriptions are **manifest intent**, not auditor-certified behavior. Structural source classes are deliberately provisional. Deep traces below cover critical representative paths; other rows explicitly need semantic review and real consumer/profile acceptance. This is a complete custody inventory plus bounded deep audit, not a claim of 980 complete code reviews.

## Inspected source witnesses

Paths link to the exact repository source at the frozen revision; line anchors here are plain text because Markdown rendering differs across viewers.

| Witness | Source | Observation / impact |
|---|---|---|
| Phinbox submission | [InboxManager.swift](../../../apps/phinbox-app/Sources/inbox-helper/InboxManager.swift), lines 101-109 | URL query with no request body |
| HTTP form parsing | [http/mod.rs](../../../crates/phinbox/src/inbox/daemon/http/mod.rs), lines 182-201; [form/mod.rs](../../../crates/phinbox/src/inbox/daemon/form/mod.rs), 119-125 | Body-only parsing, explicit confirm/cancel required |
| Native schema | [Models.swift](../../../apps/phinbox-app/Sources/inbox-helper/Models.swift), 32-64; [types.rs](../../../crates/phinbox/src/spec/types.rs), 93-149 | bool/boolean and default_value/default disagree |
| Application state roots | [bin_app/mod.rs](../../../crates/phinbox/src/bin_app/mod.rs), 22-24,105-109; [inbox/mod.rs](../../../crates/phinbox/src/inbox/mod.rs), 254-281 | Native application default differs from shared CLI/library root |
| Split source build | [app build.sh](../../../apps/phinbox-app/build.sh), 35-38; [helper build.sh](../../../apps/phinbox-app/Sources/inbox-helper/build.sh), 21-27 | Compile source lists omit required files |
| Approval shape | [approval.rs](../../../crates/phinbox/src/approval.rs), 26-48,143-200 | Rich material context and conservative boolean default |
| Substrate composition | [driver-cli main](../../../crates/driver-cli/src/main.rs), imports and command dispatch | Real Forge/Codex adapters and stores are wired; fake mode is separately named |
| AgilePlus adapter | [agent_runtime.rs](../../../crates/agileplus-cli/src/agent_runtime.rs), 22-32 | Default Substrate; explicit AGILEPLUS_AGENT_BACKEND=stub |
| AgilePlus dashboard | [router.rs](../../../crates/agileplus-api/src/router.rs), 97-105 | Empty dashboard Router, with source explanation |
| Focus connectors | [focus-cli main](../../../crates/focus-cli/src/main.rs), 1550-1574 | List prints not built; sync fails requiring SyncOrchestrator |
| Focus UI | [focus-ui lib](../../../crates/focus-ui/src/lib.rs) | Color constants plus tests; not a user app |
| Linear connector | [connector-linear lib](../../../crates/connector-linear/src/lib.rs), builder/default_manifest | Concrete HTTP client + default in-memory token storage; Verified enum is source metadata, not audit verification |
| PhenoCompose supported profiles | [CLI lib](../../../crates/pheno-compose-phenocompose-cli/src/lib.rs), ensure_apply_capabilities around 1047-1110 | Errors before apply for NVMS persistence, unavailable/placeholder provider, health checks, artifact publication and volume removal |
| Eye detector | [onnx_detector.rs](../../../crates/eyetracker-inference/src/onnx_detector.rs), 54-84,149 onward | Runtime-agnostic stub; availability initially based on model file existence |
| Eye fallback | [pipeline.rs](../../../crates/eyetracker-inference/src/pipeline.rs), create_fallback_face around 265-310 | Synthetic face box/landmarks, not observed actual eye geometry |
| HexaKit exported crypto | [lib.rs](../../../crates/hexa-kit/src/lib.rs), 7-16; [encryption.rs](../../../crates/hexa-kit/src/encryption.rs), 21-54; [keys.rs](../../../crates/hexa-kit/src/keys.rs), 20-39 | Exported encryption/decryption return empty successful outputs; KDF empty, salts zero; this is production namespace source, not test fixture |
| Router Bifrost | [bifrost_adapter.rs](../../../crates/phenotype-router/src/bifrost_adapter.rs), 1-13,34-47 | Hello-world ID-prefix allow/deny, no real Go bridge |
| PlayCua composition | [playcua-app lib](../../../crates/playcua-app/src/lib.rs), 1-38 | Explicit port scaffolding with injected in-tree mocks |
| Pine NanoVMS | [pine-nvms lib](../../../crates/pine-nvms/src/lib.rs) | Unit struct with new/default; no actual runtime operation exposed |
| Eidolon unsupported targets | [desktop lib](../../../crates/eidolon-desktop/src/lib.rs); platform stub.rs files | Explicit fail-loud unsupported feature/target paths; not false success |
| Tasken real storage | [main.rs](../../../crates/tasken/src/main.rs) | File storage/queue/service wiring and CLI execution |
| Settly/Stashly | [Settly lib](../../../crates/settly/src/lib.rs), [Stashly lib](../../../crates/stashly/src/lib.rs) | Concrete exported builder/cache layers; consumer/runtime proof separate |
| Sidekick | [messaging lib](../../../crates/sidekick-messaging/src/lib.rs) | Messaging trait/data/errors; tests with stub-sent do not establish provider delivery |
| Registry quality score | [project-registry lib](../../../crates/phenotype-project-registry/src/lib.rs), documentation_score/compliance_score | Counts file-presence booleans, not semantic/product assurance |
| Known identity debt | [README](../../../README.md), 358-384; [AGENTS](../../../AGENTS.md) | Inherited wrong-project documents explicitly acknowledged; root AGENTS says phenotype-omlx |

## Hosted and historical evidence

Read-only GitHub queries in this investigation observed 63 open PRs, four open issues and 30 open Dependabot alerts. Counts are transient; not proof that a named product is complete/incomplete, and no repository-wide CI success was claimed. Relevant issues include #417 manifest repair and #418 ProcessPort child environment support; review existing PRs before implementation to avoid duplication. No workflow runs were triggered, no known-green suite rerun and no upstream project modified.

Native files entered visible local history at 33673213; no deletion appeared under all-ref native-path history. Source defects are inherited/contract drift; older standalone source history, hidden refs and uninspected external repos remain unknown. Current-main comparison shows no changes to central Phinbox defect files relative to earlier inspection, while inventory and some Rust/test infrastructure differ.

Memory routing was used only to locate legacy `phenoAI` identity and existing gateway history, then current source/remote identity was rechecked. Historical key-pool PR #411 was not treated as current main integration, proactive quota management or runtime proof.

## Provenance and decisions

[Absorption index](../../../docs/ABSORPTION_INDEX.md) and per-copy PROVENANCE/ABSORPTION files identify some donor snapshots. `absorption/PhenoInfra`, `PhenoMLX-temp`, pheno-forge and historical router/herdr/design copies do not automatically transfer whole-product ownership. Stashly explicitly documents thegent-cache adoption. `forgecode-fork` is a named fork holding; PhenoShared itself is a pooled repository, not assumed to be a fork. Manifest repository URLs can be stale and are not sufficient provenance. Every unknown fork/donor/release owner is retained as an ownership-review obligation.

Current docs-5 PhenoShared packet requires package-specific real consumers, preserved source authority, independent negative controls and 85%+ accepted suite floors. It explicitly warns that excluded code and source counts do not establish disposition or completeness. This docs-only audit respects that boundary and makes no numeric product grade.

## Validation of this documentation delivery

Required before publication: inventory denominator uniqueness/completeness against frozen Git tree; local Markdown links resolve; no generated doc over 500 lines; `git diff --check`; staged files only under this audit directory; parent dirty checkout unchanged. Results are recorded in validation.md. These checks validate the audit package structure, not product code, links in external untouched documentation or claimed runtime behavior.
