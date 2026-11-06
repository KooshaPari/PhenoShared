# quill

Type-safe HTTP client for TypeScript with interceptors, retries, and built-in test utilities.

## Stack

- Language: TypeScript (strict mode)
- Package name: `@kooshapari/quillts`
- Build: `tsc` (TypeScript compiler)
- Testing: vitest
- Linting: eslint
- Type checking: `tsc --noEmit`

## Structure

```
src/    - TypeScript source
dist/   - Compiled JavaScript output (published to npm)
tests/  - Test suite
```

## Development

```bash
npm install
npm run build
npm run test
npm run lint
npm run typecheck
```

## TypeScript Conventions

- Strict mode required; no `any` types.
- Export public API from `src/index.ts`.
- All public functions must have JSDoc comments with param/return types.
- Interceptors must implement the `Interceptor` interface.
- Retry configuration uses exponential backoff; expose via `RetryConfig`.

## Phenotype Org Rules

- UTF-8 encoding only in all text files. No Windows-1252 smart quotes or special characters.
- Worktree discipline: canonical repo stays on `main`; feature work in worktrees.
- CI completeness: fix all CI failures on PRs, including pre-existing ones.
- Never commit agent directories (`.claude/`, `.codex/`, `.gemini/`, `.cursor/`).

## Spec Tracking

Spec work is tracked via AgilePlus: `cd /Users/kooshapari/CodeProjects/Phenotype/repos/AgilePlus && agileplus <command>`
