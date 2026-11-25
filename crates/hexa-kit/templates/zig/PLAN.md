# PLAN.md — template-lang-zig

## Phase 1: Scaffold
- Define layer contract manifest and reconcile rules
- Create Zig scaffold templates (`build.zig`, project structure)
- Set up `task check` quality gate and `scripts/scaffold-smoke.sh`
- Create docs: `index.md`, `UPGRADE.md`, `BRANCH_PROTECTION.md`

## Phase 2: Validation
- Verify composition on template-commons primitives
- Run `task quality` across manifest, docs, and scaffold smoke script
- Smoke-test generated Zig project with `zig build`
- Validate semver bump workflow end-to-end

## Phase 3: Stabilization
- Freeze public contract surface for downstream domain templates
- Add integration tests: scaffold → zig build → test → teardown
- Document upgrade path when commons bumps
- Ensure `zig fmt --check` passes on generated code

## Phase 4: Release
- Tag initial semver release
- Update template-program-ops layer registry
- Publish availability to downstream domain templates
