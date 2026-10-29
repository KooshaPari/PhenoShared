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
| `crates/hexa-kit/templates/go/templates/go` | Template. Its `go.mod` contains the literal placeholder `{{ module_path }}`, not a module path. |
| `crates/hexa-kit/templates/hexagon/go` | Embedded template, not a build target. |
| `crates/policystack/wrappers/go` | Wrapper fixture. |
| `servers/external/mcpforge/integrationtests/workspaces/go` | Integration-test fixture workspace. |
| `servers/external/mcpforge/integrationtests/test-output/**` | Scratch output written by test runs. Gitignored, so the guard skips it automatically. |

## Broken modules needing a real fix

These are live code with real defects. They are not gated because gating them
today would fail the build for reasons unrelated to any change under test.
Each needs a fix before it can be added to `go.modules.txt`.

| Module | Failure |
|---|---|
| `agents/phenoagent/pheno-cli-go` | `bootstrap_test.go`: `unknown command "bootstrap"`; `templates_test.go`: expects 5 templates, finds 39. Same two defects fixed in `pheno-cli`, but this copy has not received the fix. |
| `crates/argis-extensions` | Requires Go >= 1.26.7, which the local toolchain does not provide. CI would resolve this via `go-version-file`, but the module also has 152 gofmt violations and a dependency (`hatchet@v0.112.12`) with the same floor. |
| `crates/argis-extensions/bifrost/core` | `undefined: schemas.ChatMessageRole`. An incomplete vendored shim, and the local `replace` target of `crates/argis-extensions`. |
| `crates/hexa-kit/templates/go` | See the templates table above. |
| `servers/external/mcpforge` | `TestDiagnostics/CleanFile` fails after 41s in `internal/lsp`. |
| `servers/external/ops-mcp` | `go vet` did not complete within 300s. The dependency tree pulls in `nanovms/ops` and `google-cloud`. Needs investigation before it can be gated. |
