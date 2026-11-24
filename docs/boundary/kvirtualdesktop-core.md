# Boundary — kvirtualdesktop-core

> Federated `kvirtualdesktop-core` crate. Boundary file created
> 2026-07-17 during registry batch4 refresh.

## In Scope

- **Federated core crate** — Rust library providing the canonical
  virtual-desktop primitives (window manager bindings, virtual
  filesystem, process sandbox).
- **Bindings** — C-ABI via `pheno-cdylib-bridge`, plus native macOS
  Cocoa / Linux X11 / Windows Win32 adapters.
- **CLI** — `kvirtualdesktop` binary for headless desktop instances.

## Out of Scope

| Not here | Lives in | Reason |
| -------- | -------- | ------ |
| Full desktop app | `KDesktopVirt` | Desktop app is a consumer; core is the library |
| Display server | OS | kvirtualdesktop wraps, doesn't replace X11/Wayland |
| Window manager | Compositor (Mosaic, etc.) | WM is a separate concern |

## Boundary Crossings

| Crossing | Direction | Surface | Status |
| -------- | --------- | ------- | ------ |
| KDesktopVirt → kvirtualdesktop-core | consumer | library | green |
| kvirtualdesktop-core → pheno-cdylib-bridge | peer | FFI surface | green |

## Last Boundary Review

**Date:** 2026-07-17
**Reviewer:** registry batch4 audit (queue-refresh-batch4)
**Disposition-index row:** DSPI-NEW (`repo-kvirtualdesktop-core`, fsm=queued)
**Decisions:**
- ABSORB target: `pheno` monorepo `crates/kvirtualdesktop/`.
- No standalone GitHub repo — federated only via portage.git
  refs (registry metadata).

**Next review:** on absorption completion
