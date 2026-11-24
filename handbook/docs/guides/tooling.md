---
title: Toolchains (Bun, uv, VoidZero)
---

# Toolchains

| Area                             | Choice                                                                 | Notes                                                                                        |
| -------------------------------- | ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| **JS runtime & package manager** | [Bun](https://bun.sh/)                                                 | `bun install`, `bun run build`. Lockfile: `bun.lock`.                                        |
| **Python**                       | [uv](https://docs.astral.sh/uv/) + **CPython ≥ 3.14**                  | `uv sync --group dev`, `uv run …`. Version pin: `.python-version`.                           |
| **TypeScript**                   | **TypeScript ^6** (strict)                                             | `vue-tsc --noEmit`; upgrade to **TypeScript 7** when published and VitePress/Vue support it. |
| **Lint (JS/TS)**                 | [oxlint](https://oxc.rs/docs/guide/usage/linter.html) (VoidZero / Oxc) | Config: `oxlint.json`; run `bun run lint:ts`.                                                |

## Commands

```bash
bun install
bun run build
bun run check        # oxlint + vue-tsc + link stub (uv)
bun run lint         # markdownlint (optional / broad)
uv sync --group dev
uv run pre-commit run --all-files
```

See also [Full-turn delivery](./full-turn-delivery.md).
