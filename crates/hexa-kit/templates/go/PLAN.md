# PLAN.md — template-lang-go

## Phase 1: Scaffold
- Define layer contract manifest and reconcile rules
- Create Go scaffold templates (module structure, Taskfile)
- Set up `task check` quality gate
- Create docs: `index.md`, `UPGRADE.md`, `BRANCH_PROTECTION.md`

## Phase 2: Validation
- Verify composition on template-commons primitives
- Run `task quality` across manifest, docs, and scaffold output
- Smoke-test generated Go module builds with `go build`
- Validate pinned-version consumption from domain templates

## Phase 3: Stabilization
- Freeze public contract surface for downstream domain templates
- Add integration tests: scaffold → build → test → teardown
- Document upgrade path when commons bumps
- Ensure go vet and staticcheck pass on generated code

## Phase 4: Release
- Tag initial semver release
- Update template-program-ops layer registry
- Publish availability to template-domain-service-api (primary consumer)
