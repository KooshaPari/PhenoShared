# Go modules excluded from CI

Every Go module in this repository is either listed in `go.modules.txt` (and
therefore gated) or listed here with the reason it is not.

`scripts/ci/check-go-modules.py` enforces this: the build fails if a `go.mod`
appears that is neither in `go.modules.txt` nor covered by an ignore rule, so
a new module must be consciously classified.

## Currently gated

Twelve modules, listed in `go.modules.txt`:

`agileplus/pheno-cli` · `apps/bench-cockpit/server` ·
`cmd/capprobe` · `cmd/checker` · `cmd/promptscrape` · `cmd/trust` ·
`cmd/wire` · `crates/argis-extensions/slm-server` · `crates/nanovms` ·
`go-fabric` · `libs/docslib` · `pheno-cli`

## Absorbed or vendored snapshots

These are copies of code developed elsewhere. They are preserved for
historical reference and are not maintained here.

| Module | Disposition |
|---|---|
| `hfscope` | Absorbed from `github.com/KooshaPari/zz-merge-unk-hfscope` (2026-09-15). Both declared upstreams are deleted (404). Absorption is incomplete: `cmd/` is missing, so `make build` cannot work. Building it also requires `templ generate` plus a gofmt pass. See `docs/absorbed-from/hfscope/README.md`. |
| `_archived/**` | Archived trees. `_archived/nanovms-core/go.mod` declares replace directives pointing at `../.worktrees/l3-52-pheno-go-ctxkit-2026-06-11/pheno-go-ctxkit` and `./third_party/go.uber.org/mock`, neither of which exists. The upstream `github.com/KooshaPari/pheno-go-ctxkit` is also deleted. |
| `absorption/**` | Absorption staging trees, including a second divergent copy of the archived modules above. |

## Duplicates of a gated module

Several copies of the same CLI exist. Only the canonical one is gated.

| Module | Canonical |
|---|---|
| `crates/agile-plus/pheno-cli` | `agileplus/pheno-cli` |
| `crates/hexa-kit/agileplus/pheno-cli` | `agileplus/pheno-cli` |

All three declare the module path `github.com/KooshaPari/pheno-cli`. The two
copies lack the `internal/hooks/scripts/` directory that the canonical copy
has, so they fail `go vet` with a `//go:embed` pattern error.

## Templates and fixtures

Not modules of this repository. They are embedded templates, fixtures, or
scratch workspaces written by test harnesses.

| Path | Why excluded |
|---|---|
| `crates/hexa-kit/templates/go` | **EXCLUDE**, structurally. Template source, not buildable code. The real `go.mod` is nested one level deeper, at `crates/hexa-kit/templates/go/templates/go/go.mod`, and it opens with `module {{ module_path }}`; 17 imports across the tree are `"{{ module_path }}/..."` (for example `"{{ module_path }}/domain/entities"`). The placeholders are substituted per generated project, so no gate can ever resolve it. |
| `crates/hexa-kit/templates/hexagon/go` | Embedded template, not a build target. |
| `crates/policystack/wrappers/go` | Wrapper fixture. |
| `servers/external/mcpforge/integrationtests/workspaces/go` | Integration-test fixture workspace. |
| `servers/external/mcpforge/integrationtests/test-output/**` | Scratch output written by test runs. Gitignored, so the guard skips it automatically. |

## Ungated modules: measured blockers and disposition

These are not gated because gating them today would fail the build for reasons
unrelated to any change under test. The `Disposition` column distinguishes a
fixable defect (`NEEDS_FIX`) from a target that can never be gated as written
(`NOT_GATEABLE`).

| Module | Disposition | Failure |
|---|---|---|
| `crates/argis-extensions` | `NEEDS_FIX` | `go.mod` requires `go >= 1.26.10` and declares no `toolchain` line; the local toolchain is go1.26.5, so `go list .` reports `go: go.mod requires go >= 1.26.10 (running go 1.26.5; GOTOOLCHAIN=local)`. CI resolves that floor automatically via setup-go `go-version-file`, so the floor is not what blocks gating. Two real blockers remain: **133** gofmt-violating files, and generated source containing `<REDACTED>` in place of the org segment — `api/graphql/gen/generated.go` carries `githubᚗcomᚋ<REDACTED>ᚋbifrostᚑextensions`, which resolves to nothing. The `hatchet` dependency is `v0.114.8`. |
| `crates/argis-extensions/bifrost/core` | `NEEDS_FIX` | `undefined: schemas.ChatMessageRole`. An incomplete vendored shim, and the local `replace` target of `crates/argis-extensions`. |
| `servers/external/mcpforge` | `NOT_GATEABLE` | `TestDiagnostics/CleanFile` fails in `integrationtests/tests/go/diagnostics/` — not in `internal/lsp`, which has no `TestDiagnostics` and passes. Measured: subtest fails in 7.6s (7.9s for the package), not 41s. It fails two ways: the harness needs an external `gopls` binary that no workflow installs (`helpers.go` uses `t.Fatalf` on setup error rather than skipping), and the workspace path is rejected because `component "phenoShared" is listed by macOS as "PhenoShared"`, so the file is reported as `WARNING at L1:C9: No active builds contain .../workspace/clean.go (Source: go list)` where the test expects no diagnostics. |
| `servers/external/ops-mcp` | `NEEDS_FIX` | `go vet` did not complete within 300s. The dependency tree pulls in `nanovms/ops` and `google-cloud`. Needs investigation before it can be gated. |
