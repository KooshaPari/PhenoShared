# Source Index — Appendix (L01, U01, E01, W01-W24, Liveness Status)

This file is an appendix to [`SOURCE-INDEX.md`](SOURCE-INDEX.md). It carries the library-document, user-instruction, verification-evidence and web-source entries plus the full Liveness Status table. No information from the original source index has been omitted.

<a id="L01"></a>
## L01 — 04-polyrepo-ecosystem-consolidation.md

**kind:** library_document

**file id:** file_00000000002881fdb6918d612d9a3bac

**scope note:** Relevant semantic-search excerpts reviewed; not all historical documents/conversations.

<a id="U01"></a>
## U01 — Canonical tooling/processes request, September 16 2026

**kind:** current_user_instruction

**scope note:** Explicit direction for OXC, native TypeScript, Bun, uv, Python 3.14t, Lefthook, FastMCP, aggressive outcome-driven alternatives and shared consumption.

<a id="E01"></a>
## E01 — verification/typescript-multiple-projects.json

**kind:** local_experiment

**scope note:** Executed isolated two-project fixture with TypeScript 5.8.3; not Tracera or its pinned compiler.

<a id="W01"></a>
## W01 — Native TypeScript command identity

[Open source](https://github.com/microsoft/typescript-go)

**kind:** primary_web_source

**accessed date:** 2026-09-16

**scope note:** Official staging repo says port completed and TypeScript 7 RC+ uses tsc; older feature table also remains, so check exact supported release.

<a id="W02"></a>
## W02 — Oxlint

[Open source](https://oxc.rs/docs/guide/usage/linter)

**kind:** primary_web_source

**accessed date:** 2026-09-16

**scope note:** Official capability documentation, not an ecosystem benchmark.

<a id="W03"></a>
## W03 — Oxfmt

[Open source](https://oxc.rs/docs/guide/usage/formatter.html)

**kind:** primary_web_source

**accessed date:** 2026-09-16

**scope note:** Official supported formatter capabilities; verify version and plugins.

<a id="W04"></a>
## W04 — uv Python versions

[Open source](https://docs.astral.sh/uv/concepts/python-versions/)

**kind:** primary_web_source

**accessed date:** 2026-09-16

**scope note:** Explicit free-threaded interpreter requests; deployment patch/build pin still required.

<a id="W05"></a>
## W05 — CPython free threading

[Open source](https://docs.python.org/3.14/howto/free-threading-python.html)

**kind:** primary_web_source

**accessed date:** 2026-09-16

**scope note:** Build support and actual GIL state differ; extension imports may re-enable GIL.

<a id="W06"></a>
## W06 — FastMCP

[Open source](https://gofastmcp.com/getting-started/welcome)

**kind:** primary_web_source

**accessed date:** 2026-09-16

**scope note:** Docs reflect main and can include unreleased features; qualify a release, not every documented feature.

<a id="W07"></a>
## W07 — Bun compatibility

[Open source](https://bun.sh/docs/runtime/nodejs-compat)

**kind:** primary_web_source

**accessed date:** 2026-09-16

**scope note:** Compatibility is API-specific; package-manager and runtime qualification are separate.

<a id="W08"></a>
## W08 — Lefthook remotes

[Open source](https://lefthook.dev/configuration/remotes/)

**kind:** primary_web_source

**accessed date:** 2026-09-16

**scope note:** Shared hook configuration mechanism; use immutable tested ref and inspect effective config.

<a id="W09"></a>
## W09 — GitHub reusable workflows

[Open source](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows)

**kind:** primary_web_source

**accessed date:** 2026-09-16

**scope note:** Job-level reuse, literal refs, .github/workflows provider location, permission constraints.

<a id="W10"></a>
## W10 — Cargo build profiles

[Open source](https://doc.rust-lang.org/cargo/reference/profiles.html)

**kind:** primary_web_source

**accessed date:** 2026-09-16

**scope note:** Size and speed optimization profiles are distinct; benchmark actual workload.

<a id="W11"></a>
## W11 — Zig

[Open source](https://ziglang.org/learn/overview/)

**kind:** primary_web_source

**accessed date:** 2026-09-16

**scope note:** Explicit allocation, C ABI, comptime and SIMD facilities. No local performance result.

<a id="W12"></a>
## W12 — Odin

[Open source](https://odin-lang.org/docs/overview/)

**kind:** primary_web_source

**accessed date:** 2026-09-16

**scope note:** Language/runtime/allocator and data-layout facilities. No local performance result.

<a id="W13"></a>
## W13 — Nim

[Open source](https://nim-lang.org/docs/manual.html)

**kind:** primary_web_source

**accessed date:** 2026-09-16

**scope note:** Native compilation/metaprogramming/interop features. No local performance result.

<a id="W14"></a>
## W14 — Julia

[Open source](https://docs.julialang.org/en/v1/manual/performance-tips/)

**kind:** primary_web_source

**accessed date:** 2026-09-16

**scope note:** Type stability, allocation and compilation-sensitive optimization. No local performance result.

<a id="W15"></a>
## W15 — Pony

[Open source](https://www.ponylang.io/discover/)

**kind:** primary_web_source

**accessed date:** 2026-09-16

**scope note:** Actor/reference-capability concurrency model. No local scheduler benchmark.

<a id="W16"></a>
## W16 — Mojo

[Open source](https://mojolang.org/docs/manual/)

**kind:** primary_web_source

**accessed date:** 2026-09-16

**scope note:** Official language documentation; exact target and redistribution qualification remain required.

<a id="W17"></a>
## W17 — Triton

[Open source](https://triton-lang.org/main/index.html)

**kind:** primary_web_source

**accessed date:** 2026-09-16

**scope note:** GPU programming/compiler framework, distinct from Trident.

<a id="W18"></a>
## W18 — Trident

[Open source](https://github.com/kakaobrain/trident)

**kind:** primary_web_source

**accessed date:** 2026-09-16

**scope note:** Real Triton-based ML library; repo archived October 16 2023. User intended identity still needs resolution.

<a id="W19"></a>
## W19 — CUTLASS

[Open source](https://docs.nvidia.com/cutlass/latest/overview.html)

**kind:** primary_web_source

**accessed date:** 2026-09-16

**scope note:** CUDA templates and CuTe facilities; kernel architecture eligibility must be tested.

<a id="W20"></a>
## W20 — ISPC

[Open source](https://ispc.github.io/)

**kind:** primary_web_source

**accessed date:** 2026-09-16

**scope note:** SPMD CPU-vectorization compiler. No local performance result.

<a id="W21"></a>
## W21–W24, Liveness Status

See [`SOURCE-INDEX-DETAIL.md`](SOURCE-INDEX-DETAIL.md) for web-source entries W21–W24 (TileLang, Futhark, Halide, Lefthook usage) and the full Liveness Status table.



<a id="W21"></a>
## W21 — TileLang

[Open source](https://tilelang.com/)

**kind:** primary_web_source

**accessed date:** 2026-09-16

**scope note:** GPU kernel DSL; qualify exact target/compiler pair.

<a id="W22"></a>
## W22 — Futhark

[Open source](https://futhark-lang.org/)

**kind:** primary_web_source

**accessed date:** 2026-09-16

**scope note:** Array-oriented data-parallel compiler. Candidate, not adopted.

<a id="W23"></a>
## W23 — Halide

[Open source](https://halide-lang.org/)

**kind:** primary_web_source

**accessed date:** 2026-09-16

**scope note:** Image/array pipeline algorithm and schedule separation. Candidate, not adopted.

<a id="W24"></a>
## W24 — Lefthook usage

[Open source](https://lefthook.dev/usage/)

**kind:** primary_web_source

**accessed date:** 2026-09-16

**scope note:** install, validate and dump commands; local hooks can be bypassed.

## Liveness Status

Presence re-indexed 2026-09-17; per-source network liveness NOT verified in this pass.

The following source records were explicitly checked against this snapshot on 2026-09-17:

| Source ID | Status |
|---|---|
| G01 | `presence-only, network unverified` |
| G02 | `presence-only, network unverified` |
| G03 | `presence-only, network unverified` |
| G04 | `presence-only, network unverified` |
| G05 | `presence-only, network unverified` |
| G06 | `presence-only, network unverified` |
| G07 | `presence-only, network unverified` |
| G08 | `presence-only, network unverified` |
| G09 | `presence-only, network unverified` |
| G10 | `presence-only, network unverified` |
| G11 | `presence-only, network unverified` |
| G12 | `presence-only, network unverified` |
| G13 | `presence-only, network unverified` |
| G14 | `presence-only, network unverified` |
| G15 | `presence-only, network unverified` |
| G16 | `presence-only, network unverified` |
| G17 | `presence-only, network unverified` |
| G18 | `presence-only, network unverified` |
| G19 | `presence-only, network unverified` |
| G20 | `presence-only, network unverified` |
| G21 | `presence-only, network unverified` |
| G22 | `presence-only, network unverified` |
| G23 | `presence-only, network unverified` |
| L01 | `presence-only, network unverified` |
| U01 | `presence-only, network unverified` |
| E01 | `presence-only, network unverified` |
| W01 | `presence-only, network unverified` |
| W02 | `presence-only, network unverified` |
| W03 | `presence-only, network unverified` |
| W04 | `presence-only, network unverified` |
| W05 | `presence-only, network unverified` |
| W06 | `presence-only, network unverified` |
| W07 | `presence-only, network unverified` |
| W08 | `presence-only, network unverified` |
| W09 | `presence-only, network unverified` |
| W10 | `presence-only, network unverified` |
| W11 | `presence-only, network unverified` |
| W12 | `presence-only, network unverified` |
| W13 | `presence-only, network unverified` |
| W14 | `presence-only, network unverified` |
| W15 | `presence-only, network unverified` |
| W16 | `presence-only, network unverified` |
| W17 | `presence-only, network unverified` |
| W18 | `presence-only, network unverified` |
| W19 | `presence-only, network unverified` |
| W20 | `presence-only, network unverified` |
| W21 | `presence-only, network unverified` |
| W22 | `presence-only, network unverified` |
| W23 | `presence-only, network unverified` |
| W24 | `presence-only, network unverified` |

**Candidate rejection status:** No explicit rejections recorded; revisit before canonicalizing future candidates.
