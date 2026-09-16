# pheno-errors boundary reconciliation — 2026-07-29

## Scope

Reconcile the historical `pheno-errors` absorption record with the current
GitHub estate and the aliases `phenoErrors` and `phenotype-errors`.

## Remote evidence

| Repository | Result |
|---|---|
| `KooshaPari/phenoErrors` | GitHub API 404 |
| `KooshaPari/phenotype-errors` | GitHub API 404 |
| `KooshaPari/pheno-errors` | private, unarchived, default `main`, no license metadata |

Current `pheno-errors` default-branch SHA is
`01b850e4b9f8ba8ed667c34f35fa46d7cef37214` (pushed 2026-07-28).

The tree contains only:

- `README.md` and `Cargo.lock`;
- `.circleci/config.yml`, `.github/workflows/ci.yml`, `.mergify.yml`, and `trunk.yaml`;
- `.gitignore`.

There is no `Cargo.toml`, Rust source, package manifest, or license file.
The README identifies the repository as a scratch/tooling archive and a
"cargo ghost workspace" residue from the 2026-07-15 local gitification pass.

## Boundary decision

Keep the historical absorption into `pheno/crates/phenotype-error-core` under
ADR-ECO-027. Do not infer a second absorption from the re-created private
remote. Record the current remote as `active` only because GitHub reports it
unarchived; its lifecycle is `recovery-only` and its registry disposition is
`ARCHIVE_ONLY`.

No local checkout or unreleased source was found under the Phenotype repos
container. The remote itself is the cloud-preserved residue. No deletion,
force-push, or history rewrite is authorized or performed.

## Reproduction commands

```zsh
gh api repos/KooshaPari/phenoErrors
gh api repos/KooshaPari/phenotype-errors
gh api repos/KooshaPari/pheno-errors
gh api 'repos/KooshaPari/pheno-errors/git/trees/main?recursive=1'
gh api 'repos/KooshaPari/pheno-errors/commits?per_page=10'
```
