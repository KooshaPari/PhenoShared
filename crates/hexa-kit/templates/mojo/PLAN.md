# PLAN.md — template-lang-mojo

## Phase 1: Scaffold
- Define layer contract manifest and reconcile rules
- Create Mojo scaffold templates (`main.mojo`, project structure)
- Set up `task check` quality gate and `scripts/scaffold-smoke.sh`
- Create docs: `index.md`, `UPGRADE.md`, `BRANCH_PROTECTION.md`

## Phase 2: Validation
- Verify composition on template-commons primitives
- Run `task quality` across manifest, docs, and scaffold smoke script
- Smoke-test generated Mojo file with `mojo --version` and well-formedness checks
- Validate semver bump workflow end-to-end

## Phase 3: Stabilization
- Freeze public contract surface for downstream domain templates
- Add integration tests: scaffold → mojo run → teardown
- Document upgrade path when commons bumps
- Keep localization English-only per layer convention

## Phase 4: Release
- Tag initial semver release
- Update template-program-ops layer registry
- Publish availability to downstream domain templates
