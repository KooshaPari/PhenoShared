---
layout: home
title: Pine
hero:
  name: Pine
  text: Wine-equivalent compatibility for Phenotype
  tagline: Translate Windows, macOS, and Linux applications into Phenotype-native execution environments.
  actions:
    - theme: brand
      text: Getting Started
      link: /getting-started
    - theme: alt
      text: View on GitHub
      link: https://github.com/KooshaPari/Pine
features:
  - icon: 🪟
    title: Windows compatibility
    details: Translate Win32/NT syscalls to Phenotype-native equivalents — files, sockets, threads, memory, IPC, and registry semantics mapped to safe POSIX calls.
  - icon: 🍎
    title: macOS & Linux targets
    details: ELF and Mach-O loaders in pine-loader; POSIX adapter scaffolding for Linux applications and Darling-inspired plans for Cocoa-on-Phenotype.
  - icon: 🔒
    title: Sandboxed by default
    details: Backed by nvms (nanovms) microVMs — Firecracker for untrusted binaries, gVisor for semi-trusted code, WASM for hot-path utilities.
  - icon: 🦀
    title: Rust core
    details: Hexagonal architecture with trait-based ports (Loader, SyscallHandler) and pluggable adapters — built on stable Rust 2021 edition.
  - icon: ⚡
    title: Performance-aware
    details: Designed against the Wine ~5–15% overhead target — native where possible, emulation where needed, no QEMU-grade translation tax.
  - icon: 📚
    title: Open governance
    details: MIT OR Apache-2.0 licensed, OpenSSF Scorecard tracked, weekly drift checks, and signed-release provenance.
---

## What is Pine?

**Pine** is a compatibility layer that enables Windows, macOS, and Linux
applications to run on Phenotype-native infrastructure. Like Wine translates
Windows syscalls to POSIX, Pine translates applications into Phenotype
execution environments.

Pine sits in the same family as Wine, Proton, and Darling — but targets
**Phenotype OS** as the host and is built on the **nvms** microVM runtime
(nanovms) for isolation.

## Status

Pine is in **pre-alpha** (`[###-------] 25%`). The Rust workspace, ELF/PE
loaders, syscall translation tables (Linux + Windows), and nvms integration
scaffolding are in place. The current focus is the Windows syscall translation
layer and macOS/Linux adapter work — see
[ARCHITECTURE.md](https://github.com/KooshaPari/Pine/blob/main/docs/ARCHITECTURE.md)
for the full design.

## Architecture at a glance

```
┌──────────────────────────────────────┐
│  Application Layer                   │  (Windows .exe / macOS .app / Linux)
├──────────────────────────────────────┤
│  Binary Loader  (PE / ELF / Mach-O)  │  → pine-loader
├──────────────────────────────────────┤
│  Syscall Emulation Layer             │  → pine-syscall
│  (Win32 / POSIX → Phenotype ABI)     │
├──────────────────────────────────────┤
│  Compatibility Libraries             │  → pine-compat
├──────────────────────────────────────┤
│  nvms Isolation Layer                │  → pine-nvms
├──────────────────────────────────────┤
│  Phenotype Native Runtime            │  Rust core + Go orchestration
└──────────────────────────────────────┘
```

## Where to next?

- [Getting Started](/getting-started) — build the workspace and run the tests.
- [Architecture (raw)](https://github.com/KooshaPari/Pine/blob/main/docs/ARCHITECTURE.md)
  — full layer design and nvms integration strategy.
- [Repository](https://github.com/KooshaPari/Pine) — source code and issues.
