# ADR — template-lang-zig

## ADR-001: Zig Version
**Status:** Accepted
**Context:** Zig is evolving rapidly; version selection matters.
**Decision:** Target Zig 0.12+ for all generated projects.
**Rationale:** Zig 0.12 has improved comptime and build system.

## ADR-002: Build System
**Status:** Accepted
**Context:** Zig has a built-in build system.
**Decision:** Use `build.zig` exclusively. No CMake or other build systems.
**Rationale:** Native Zig build system is fast and cross-platform.

## ADR-003: Memory Management
**Status:** Accepted
**Context:** Zig requires explicit memory management.
**Decision:** Use arenas for temporary allocations. defer for cleanup. std.heap.ArenaAllocator.
**Rationale:** Zig's no-runtime philosophy; manual memory management is idiomatic.

## ADR-004: Error Handling
**Status:** Accepted
**Context:** Zig has error sets and try/catch.
**Decision:** Use error sets for recoverable errors. error union types. No exceptions.
**Rationale:** Errors are values in Zig; explicit handling prevents silent failures.

## ADR-005: C Interop
**Status:** Accepted
**Context:** Zig can embed C code and link with C libraries.
**Decision:** Use cImport for C interop. link libc for standard library.
**Rationale:** Zig is designed as a C replacement; seamless C interop is a strength.

## ADR-006: Comptime
**Status:** Accepted
**Context:** Zig has powerful compile-time execution.
**Decision:** Use comptime for generic algorithms, validation, code generation.
**Rationale:** Zig comptime eliminates metaprogramming complexity.
