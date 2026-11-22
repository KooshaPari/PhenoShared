# Deferred: the unified MCP registry

## Also deferred: their agent-driven trace path

`cmd_node_test.go` covers PhenoShared's agent-driven claim/completion writing trace
shards. Its `cmd_node.go` calls `trace.EmitNode` and `store.ClaimOwner`, which exist in
PhenoShared's `internal/trace` and `internal/store` but not in the standalone versions
this absorb takes. Those two packages are where the Windows `LockFileEx` work and the
read-does-not-write guarantee live, so adopting their whole lineage to satisfy one
command is the wrong trade. `cmd_node.go` stays on the standalone implementation and
`cmd_node_test.go` returns with the port.

The reverse happened for `internal/server`: PhenoShared's version is stricter (refuses a
non-loopback address, requires an absolute run directory, exposes `Bind`), and its own
tests enforce that, so the absorb takes theirs. One of those tests asserted a
POSIX-absolute path with `strings.HasPrefix(dir, "/")`; it now uses `filepath.IsAbs`, so
it holds on Windows too.

## The MCP registry

PhenoShared's `cmd/dagrun` had refactored the MCP surface into `internal/mcp/registry.go`
plus an SDK-backed `internal/mcp/http.go`. Both landed on top of the same 19 tools that
the standalone repo ships, so the two catalogues agree on names but not on structure:
the registry is a single source of truth shared by the stdio and HTTP transports, while
the standalone implementation keeps `tool`/`toolList` next to the handlers.

During the absorb (commit "feat(dagrun): absorb standalone repo at v1.3.3") the registry
and HTTP transport were **removed from the tree** rather than half-merged, and the
module went back to its single dependency:

- the registry declares `tool` and `toolList` too, so keeping both is a compile error,
  not a merge conflict a reviewer can resolve by picking a side;
- the standalone MCP implementation is the one covered by the 21-package suite on
  Windows, macOS and Linux, so adopting the registry in the same change would have
  meant shipping an untested rewrite of the agent-facing surface;
- porting it is a real refactor with its own tests, and it belongs in a reviewable PR
  rather than folded into a repository absorb.

Recovering the work is mechanical: the files are intact in PhenoShared history at
`61d6cbda` (`cmd/dagrun/internal/mcp/registry.go` and `http.go`), and the dependency they
need is `github.com/modelcontextprotocol/go-sdk v1.8.0`, which requires Go 1.25.

Port checklist:

1. Bring back `registry.go`, `http.go` and `cmd_serve.go`.
2. Delete `tool`/`toolList` from `internal/mcp/tools.go` and move each handler behind a
   `toolSpec.call`.
3. Re-point `tools_more_test.go` and `tools_run_test.go` at the registry.
4. Raise the module to `go 1.25.0` and re-add the SDK require block.
5. Prove parity: same 19 names, same schemas, both transports answering from one list.
6. Restore the `serve` case in `main.go`; `cmdServe` calls `srv.Bind`, which the
   standalone `internal/server` surface does not expose, so the two travel together.
