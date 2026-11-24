# SSOT — Pine

## State
- Default branch: main
- Last verified: 2026-06-08
- CI status: green (docs + lint)
- Open PRs: 0
- Open branches: 1 (main)
- Stashes: 0

## Dependencies
- Rust: stable (2021 edition)
- Node: 20 (for docs tooling)
- Python: N/A

## Architecture
- Hexagonal: yes (scaffolded)
- Ports: Loader, SyscallHandler
- Adapters: ElfLoader, LinuxSyscallHandler, NvmsRuntime
- Domain: ProcessId, SyscallNumber, CompatibilityLayer

## Next Steps (DAG)
1. [x] P0: State unification
2. [x] P1: Tooling + governance
3. [x] P2: Hexagonal refactor
4. [ ] P3: Implement ELF loader in pine-loader
5. [ ] P4: Implement syscall translation table in pine-syscall
6. [ ] P5: Add nvms integration test

## Fleet Links
- Parent: Phenotype
- Related: nanovms (runtime), NetScript (Rust toolchain)
- Consumes: N/A
- Merged into: N/A
