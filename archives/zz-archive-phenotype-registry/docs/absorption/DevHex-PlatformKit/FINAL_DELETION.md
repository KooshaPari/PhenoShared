# DevHex and PlatformKit deletion package

Date: 2026-06-20
Decision: DELETE_AFTER_PATCHES now complete; DELETE after this registry PR merges.
Confidence: medium-high

## Executive decision

DevHex and PlatformKit can be deleted after preservation because their surviving Go runtime responsibilities are now owned by phenotype-go-sdk. PlatformKit was not fully covered before this pass because packages/platformkit was README-only; phenotype-go-sdk#24 added the missing Go modules from PlatformKit/go/devenv and PlatformKit/go/devhex. DevHex runtime source was already present in packages/devhex and phenotype-go-sdk#24 added explicit ORIGIN metadata. Local-only/ahead source work is preserved here as patchsets.

## Absorption matrix

| Source Item | Source Evidence | Category | Source State | Target Repo | Target Evidence | Status | Deletion Justification | Risk if Deleted | Required Action |
|-------------|-----------------|----------|--------------|-------------|-----------------|--------|------------------------|-----------------|-----------------|
| DevHex hexagonal environment abstraction | DevHex/pkg/domain/environment.go, DevHex/pkg/domain/registry.go, DevHex/pkg/adapters/* | Public Go package | implemented | phenotype-go-sdk | packages/devhex/pkg/domain, packages/devhex/pkg/adapters, PR #24 ORIGIN.md | DONE | Runtime source and package docs preserved in SDK | low; standalone clone duplication | none |
| DevHex tests | DevHex/pkg/adapters/*/*_test.go, DevHex/tests/smoke_test.go | Tests | implemented | phenotype-go-sdk | packages/devhex/pkg/adapters/*/*_test.go, packages/devhex/tests/smoke_test.go | DONE | Test artifacts preserved with source | low | none |
| DevHex docs/governance | DevHex/README.md, FUNCTIONAL_REQUIREMENTS.md, docs/*, AGENTS.md | Docs/governance | implemented/docs-only | phenotype-go-sdk and phenotype-registry | packages/devhex/* plus this folder source-docs/DevHex | DONE | Runtime docs in SDK; audit/source docs preserved in registry | low | none |
| DevHex local-only commits | DevHex main ahead origin/main: chore intent snapshot, L7 intent snapshot | Historical commits | local-only attempted/docs | phenotype-registry | patches/DevHex/local-ahead.patch | DONE | Patchset preserves unpushed intent work without mutating rebase checkout | medium; loss of local work context | none |
| DevHex mid-rebase state | DevHex/.git/rebase-merge | Local repo state | broken/local | phenotype-registry | patches/DevHex/local-ahead.patch plus source-docs | DONE | Useful content preserved; broken local VCS state has no standalone product merit | low | none |
| PlatformKit Go devenv module | PlatformKit/go/devenv/internal/*, SPEC.md, README.md, tests | Public Go package | implemented | phenotype-go-sdk | packages/platformkit/devenv/* in PR #24 | DONE | Previously missing source now folded into SDK | low | none |
| PlatformKit nested devhex module | PlatformKit/go/devhex/pkg/*, tests | Public Go package | implemented | phenotype-go-sdk | packages/platformkit/devhex/* in PR #24 | DONE | Nested module preserved as source evidence and package code | low | none |
| PlatformKit root product docs | PlatformKit/PRD.md, PLAN.md, CHARTER.md, ADR.md, docs/adr/*, docs/research/* | Docs/spec/ADR | docs-only | phenotype-registry | source-docs/PlatformKit/* | DONE | Source claims preserved in registry; runtime owner is SDK | low-medium; loss of rationale | none |
| PlatformKit local-only commits | PlatformKit chore/tick26-lift-ahead-20260611 ahead origin/main | Historical commits | branch-only/local-only | phenotype-registry | patches/PlatformKit/local-ahead.patch | DONE | Patchset preserves WIP/governance/ahead state before deletion | medium; loss of local work context | none |
| Archived remote repo state | gh repo view KooshaPari/DevHex and KooshaPari/PlatformKit archived true | Governance | deprecated | phenotype-registry | this deletion package | INTENTIONALLY_DEPRECATED | Remote was already archived and is now fully covered by SDK/registry evidence | low | delete remote |

## Gaps and exceptions

No LAST_RESORT_EXCEPTION remains after phenotype-go-sdk#24 and this registry preservation package.

## Merit of broken/scaffold work

DevHex rebase metadata has no product merit, but the commits reachable from HEAD do have documentation/intent merit and are preserved as patches. PlatformKit root docs and research docs have rationale merit and are preserved under source-docs. README-only PlatformKit target state was partial and was corrected by phenotype-go-sdk#24.

## Final deletion recommendation

DELETE after this registry PR merges. Delete KooshaPari/DevHex and KooshaPari/PlatformKit remotes and remove local clones, including duplicate local Settly handling in a later package if needed.
