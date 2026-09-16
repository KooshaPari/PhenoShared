# Research

- `package.json` shows a Bun-managed TypeScript package.
- Existing scripts:
  - `build`: `tsc && cp -r css dist/css`
  - `test`: `vitest run`
  - `lint`: `oxlint`
- Generated artifacts to clear:
  - `dist/`
  - `coverage/`
  - `docs/.vitepress/`
- The repository already had a broader `Taskfile.yml`; the requested change is a simplification to the core task surface.

