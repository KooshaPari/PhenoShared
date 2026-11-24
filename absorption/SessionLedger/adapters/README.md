# Cross-language OKF adapters (C08 L75)

Thin **language-agnostic** consumer surface for OKF fixtures. This is **not** a
shipped multi-language SDK and **not** Harbor / agent-eval.

Canonical SSOT: [`docs/ops/cross-language-parity.md`](../docs/ops/cross-language-parity.md).

## Interface (language-agnostic)

Any host-language adapter SHOULD expose these operations over a single OKF
document path (`.okf.json`):

| Operation       | Contract                                                                                                            |
| --------------- | ------------------------------------------------------------------------------------------------------------------- |
| `load(path)`    | Read UTF-8 JSON; return a document object                                                                           |
| `validate(doc)` | Enforce OKF v1.0 structural rules used by the parity harness (dialect, ids, shared entity core, relation endpoints) |
| `emit(doc)`     | Serialize to pretty JSON with a trailing newline (round-trip-friendly)                                              |

CLI shape (reference):

```text
validate <path-to.okf.json>   # exit 0 on pass; non-zero + message on fail
emit <path-to.okf.json>       # print validated OKF JSON to stdout
```

## Reference implementations

| Language   | Path                                                     | Fixture path exercised by SelfCheck                                 |
| ---------- | -------------------------------------------------------- | ------------------------------------------------------------------- |
| Python     | [`python/okf_adapter.py`](python/okf_adapter.py)         | `docs/reference/conformance/fixtures/cursor-python-029.okf.json`    |
| TypeScript | [`typescript/okf_adapter.ts`](typescript/okf_adapter.ts) | `docs/reference/conformance/fixtures/codex-typescript-023.okf.json` |
| Go         | [`go/main.go`](go/main.go) (+ [`go/go.mod`](go/go.mod))  | `docs/reference/conformance/fixtures/forge-go-module-026.okf.json`  |

```powershell
python adapters/python/okf_adapter.py validate docs/reference/conformance/fixtures/cursor-python-029.okf.json
python adapters/python/okf_adapter.py emit docs/reference/conformance/fixtures/cursor-python-029.okf.json

node --experimental-strip-types adapters/typescript/okf_adapter.ts validate docs/reference/conformance/fixtures/codex-typescript-023.okf.json
node --experimental-strip-types adapters/typescript/okf_adapter.ts emit docs/reference/conformance/fixtures/codex-typescript-023.okf.json

go -C adapters/go run . validate ../../docs/reference/conformance/fixtures/forge-go-module-026.okf.json
go -C adapters/go run . emit ../../docs/reference/conformance/fixtures/forge-go-module-026.okf.json
```

Python: stdlib only (`json` / `sys` / `pathlib`). No pip packages.
TypeScript: Node stdlib only (`node:fs` / `node:path`). No npm packages.
Go: stdlib only (`encoding/json` / `os` / `fmt`). No external modules.

SelfCheck always verifies Python, TypeScript, and Go adapter sources exist.
Runtime `go run` runs when `go` is on PATH; Node ≥22 `--experimental-strip-types`
runs when available; otherwise those execute steps are explicit skips (doc +
source anchors still pass).

## Explicit non-goals

- Native SessionLedger ports / full SDKs for Py/TS/Go
- Harbor, Portage, Terminal-Bench, or multi-env agent scoring
- Replacing the Rust `OkfExporter` / ingest pipeline
