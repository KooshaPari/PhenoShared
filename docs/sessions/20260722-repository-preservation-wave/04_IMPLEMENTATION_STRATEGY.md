# Implementation Strategy

## Ref namespaces

- Product recovery: `refs/heads/recovery/<source>/<branch>`
- Retired history: `refs/heads/archive/<source>/<branch>`
- Tags: `refs/tags/archive/<source>/<tag>`

## Rules

- Import Git objects and refs without merging into active branches.
- Preserve source ref names in the manifest.
- Use canonical product parents; never route unrelated history into AgilePlus.
- Store large data-only recovery material as checksummed artifacts rather than active Git branches.
- Keep multi-crate workspaces on hold until crate ownership and consumers are known.
