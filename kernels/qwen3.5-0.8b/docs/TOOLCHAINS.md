# Toolchain Status — Qwen3.5 0.8B Polyglot Suite

> Snapshot of polyglot toolchain availability on the host that ran
> `scripts/install_mojo.sh` and `scripts/install_nim.sh` for this branch
> (`feat/qwen-polyglot-toolchains`). Captured: 2026-07-14.
>
> The scripts are idempotent and self-correcting. This document records
> the **honest** state of each toolchain on a fresh run, not an aspirational
> one. Re-run either script and the TOOLCHAINS.md may need updating only
> if a toolchain appears, disappears, or upstream stops serving binaries.

## 1. Summary table

| Toolchain | Status      | Path                                | Source        |
|-----------|-------------|-------------------------------------|---------------|
| Mojo      | NOT INSTALLED — upstream 404 | n/a                       | n/a           |
| Nim       | INSTALLED (Homebrew)         | `/opt/homebrew/bin/nim`  | Homebrew 2.2.10 |
| Pony      | NOT INSTALLED — no source    | n/a                       | n/a           |
| Vale      | NOT INSTALLED — no source    | n/a                       | n/a           |

Notes:
- "Vale" here refers to the **Vale programming language**
  (`https://vale.dev/`, formerly `https://github.com/ValeLang/Vale`),
  **not** the `/opt/homebrew/bin/vale` prose linter that happens to share
  the name (the linter is installed; the language compiler is not, and
  no `.vale` sources exist in this kernel tree).
- "Pony" refers to the **Pony language** (`https://ponylang.io/`),
  installable via `brew install ponyc`. No `.pony` sources exist in this
  kernel tree.

## 2. What was attempted

### 2.1 `scripts/install_mojo.sh`

```
[install_mojo] downloading modular CLI installer (https://get.modular.com)...
==> Tapping modularml/packages
==> Would install 1 formula: modular
✘ Formula modular (0.9.3)
Error: Failed to download resource "modular (0.9.3)"
Download failed: https://dl.modular.com/public/installer/raw/names/modular-mac-arm64/versions/latest/modular-v0.9.3-macos-arm64.tar.gz
curl: (56) The requested URL returned error: 404
[install_mojo] ERROR: modular binary not found after installer run
```

**Diagnosis.** The Modular installer's homebrew formula
(`modularml/packages/modular` 0.9.3) hard-codes a download URL on
`dl.modular.com` that currently returns **HTTP 404**. This was confirmed
both via `curl ... | sh` (the canonical installer flow) **and** via
`brew install modularml/packages/modular` directly — same URL, same 404.
The CDN root (`https://dl.modular.com/`) is alive (302 → cloudsmith.com)
but the specific tarball path is gone. The installer still prints its
"Welcome to the Modular CLI!" banner before exiting, which is misleading.

Probed alternate versions; **all** of `0.8.0`, `0.8.5`, `0.9.0` through
`0.9.5`, and `0.10.0` return 404 on the same path scheme. This is an
upstream Modular infrastructure issue, not a script bug.

**Script behaviour.** `install_mojo.sh` is correct and idempotent. On a
fixed host it would:
1. Skip with a one-liner if `modular` is already on `PATH` or in
   `~/.local/bin/`.
2. Otherwise run `curl -fsSL https://get.modular.com | sh -`.
3. Resolve the binary in either `~/.local/bin/modular` or `$(command -v modular)`.
4. Run `modular install mojo`.
5. Print `modular --version | head -3`.

Re-running the script on a host where Modular's CDN is repaired will
work without modification.

### 2.2 `scripts/install_nim.sh`

```
[install_nim] nim already installed at: /opt/homebrew/bin/nim
Nim Compiler Version 2.2.10 [MacOSX: arm64]
Compiled at 2026-04-24
Copyright (c) 2006-2026 by Andreas Rumpf
nimble v0.22.2 compiled at 2026-04-24 03:34:24
```

**Outcome.** The script correctly entered its idempotent skip branch
(`find_nim` matched `/opt/homebrew/bin/nim`). No download was attempted.
Nim was installed earlier via `brew install nim`.

**Script behaviour.** `install_nim.sh` is correct and idempotent. On a
clean host it would:
1. Skip if `nim` is on `PATH`, in `~/.nimble/bin/nim`, in
   `~/.choosenim/toolchains/nim/bin/nim`, or in `/opt/homebrew/bin/nim`.
2. Otherwise download `https://nim-lang.org/choosenim/init.sh` and run
   `sh init.sh -y`.
3. Source `~/.nimble/bin/choosenim-env` (with a `PATH` fallback).
4. Print `nim --version | head -3` and run a best-effort
   `nimble install --accept`.

## 3. Compile attempts

### 3.1 Mojo: `mojo build kernels/qwen3.5-0.8b/mojo/rmsnorm.mojo -o /tmp/rmsnorm`

**Skipped.** No `mojo` binary on the host (see §2.1). The seven Mojo
sources (`__init__.mojo`, `argmax_sample.mojo`, `attn_decode.mojo`,
`qwen3_5_types.mojo`, `rmsnorm.mojo`, `rope.mojo`, `swiglu.mojo`) are
present and intact; only the toolchain is missing. No compile could be
attempted or verified.

### 3.2 Nim: `nim c -c --skipParentCfg:on -d:release nim/qwen3_5.nim`

```
kernels/qwen3.5-0.8b/nim/qwen3_5.nim(86, 5) Error: 'out' is a keyword and cannot be used as a parameter name
```

**Diagnosis.** `kernels/qwen3.5-0.8b/nim/qwen3_5.nim:86` declares a
`proc` whose parameter list uses `out` as an identifier:

```nim
proc pheno_engine_scratch_sizes*(
    engine: pheno_engine_t;
    batch: uint32; seq: uint32;
    out: pointer): pheno_status_t    # line 86 — "out" is a Nim 2.x keyword
```

In Nim 2.0+, `out` became a contextual keyword for ARC/ORC out-parameter
syntax. The same identifier is reused as a parameter on lines 97, 113,
210, and as a local on line 235. All three downstream files (`bench.nim`,
`decode.nim`, `qwen3_5.nim`) fail to compile because they all `import
qwen3_5`.

This is a **pre-existing source bug** introduced before this branch. It
is **out of scope** for the toolchain-install commit; the fix would be a
single follow-up patch renaming the parameter (e.g. `outPtr`,
`outBuf`) or back-ticking each occurrence as `` `out` ``. Tracking that
is a separate work item.

### 3.3 Nim: `nimble c -c --skipParentCfg:on -d:release nim/qwen3_5.nim`

```
Error: Could not read package info file in .../qwen3_5.nimble;
    Reading as ini file failed with:
      Invalid section: .
    Evaluating as NimScript file failed with:
      `bin` entry should not be a source file: nim/bench.nim.
```

**Diagnosis.** `kernels/qwen3.5-0.8b/qwen3_5.nimble` has two issues:
1. `skipDirs = @["nim/../cpp", "nim/../rust", ...]` produces paths
   containing `.` segments that nimble's INI parser rejects as invalid
   section names.
2. `bin = @["nim/bench.nim", "nim/decode.nim"]` uses path-qualified
   basenames; nimble requires plain basenames.

Also out of scope; same source-tree issue class as §3.2. None of the
install scripts need to change.

## 4. What needs follow-up

| Item                                                    | Owner | Type        |
|---------------------------------------------------------|-------|-------------|
| Modular CDN 404 — fix upstream tarball URL              | Modular | upstream bug |
| Rename / back-tick `out` parameter in `qwen3_5.nim`    | TBD   | source fix   |
| Fix `qwen3_5.nimble` `skipDirs` paths and `bin` names   | TBD   | source fix   |

Until the first is resolved, `install_mojo.sh` will fail at the network
step every time. Until the second and third are resolved, `nim c` of
the Nim bindings will not produce a binary on Nim 2.x.

## 5. Files added in this branch

- `kernels/qwen3.5-0.8b/scripts/install_mojo.sh` — macOS-only, idempotent.
- `kernels/qwen3.5-0.8b/scripts/install_nim.sh` — macOS-first, idempotent.
- `kernels/qwen3.5-0.8b/docs/TOOLCHAINS.md` — this document.