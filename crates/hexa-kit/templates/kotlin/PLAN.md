# PLAN.md — template-lang-kotlin

## Phase 1: Scaffold
- Define layer contract manifest and reconcile rules
- Create Kotlin scaffold templates (Gradle project structure)
- Set up `task check` quality gate
- Create docs: `index.md`, `UPGRADE.md`, `BRANCH_PROTECTION.md`

## Phase 2: Validation
- Verify composition on template-commons primitives
- Run `task quality` across manifest, docs, and scaffold output
- Smoke-test generated Kotlin project compiles with `gradle build`
- Validate semver bump workflow end-to-end

## Phase 3: Stabilization
- Freeze public contract surface for downstream domain templates
- Add integration tests: scaffold → build → test → teardown
- Document upgrade path when commons bumps
- Ensure English-only docs align with layer convention

## Phase 4: Release
- Tag initial semver release
- Update template-program-ops layer registry
- Publish availability to downstream domain templates
