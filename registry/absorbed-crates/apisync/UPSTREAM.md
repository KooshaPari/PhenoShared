# Upstream — Apisync

This document is the repoint map for anyone who still references
`KooshaPari/Apisync` directly (Cargo git deps, `pheno` submodules, IDE links,
CI caches, or historical prompt records).

## Supersession chain

```
KooshaPari/Apisync                  ← archived, do not push
        │
        │  v0.1.0 extraction → became `apikit`
        ▼
KooshaPari/apikit                   ← archived, do not push
        │
        │  full absorption (governance + src + CI + tooling + docs + ADRs)
        ▼
KooshaPari/phenotype-tooling/
  └─ docs/absorbed-from-apikit/      ← ACTIVE canonical home
```

| Stage | Repo | URL | State | Last meaningful commit |
| ----- | ---- | --- | ----- | ---------------------- |
| 0 (here) | Apisync | https://github.com/KooshaPari/Apisync | archived | 2026-06-08 (per original README) |
| 1 | apikit | https://github.com/KooshaPari/apikit | archived | 2026-06-21 |
| 2 (active) | phenotype-tooling — `docs/absorbed-from-apikit/` | https://github.com/KooshaPari/phenotype-tooling/tree/main/docs/absorbed-from-apikit | active | continuous |

## Repoint instructions by surface

### Cargo dependencies

| Before | After |
| ------ | ----- |
| `apisync = { git = "https://github.com/KooshaPari/Apisync.git" }` | `apikit = { git = "https://github.com/KooshaPari/phenotype-tooling.git" }` (see `phenotype-tooling/docs/absorbed-from-apikit/Cargo.toml`) |
| `git = ".../Apisync.git" rev = "<sha>"` | drop the dep; the absorbed crate surface lives in the workspace member `apikit` inside `phenotype-tooling` |
| Pinning Apisync ADRs (`adr/` in dependent code) | switch to `[`docs/governance/adr/001..005-*.md`](https://github.com/KooshaPari/phenotype-tooling/tree/main/docs/absorbed-from-apikit/docs/governance/adr)` references |

If you specifically need the **original** `Cargo.toml` shape (package name
`apisync`, original repo URL, v0.1.0 version), the verbatim legacy manifest
is preserved at
[`phenotype-tooling/docs/absorbed-from-apikit/Cargo.toml.apisync-legacy`](https://github.com/KooshaPari/phenotype-tooling/blob/main/docs/absorbed-from-apikit/Cargo.toml.apisync-legacy).

### Git submodule — `pheno` workspace

`pheno/.gitmodules` (line 4–6) declares:

```
[submodule "Apisync"]
    path = Apisync
    url = https://github.com/KooshaPari/Apisync.git
```

The `phenotype-core` workspace no longer compiles against the Apisync
submodule as of Wave 14 (task #1, hexa-kit #271: git pin repointed to
`KooshaPari/phenotype-types` main). If you still see a submodule pin in a
fork, remove it:

```bash
git -C "$PHENO_ROOT" submodule deinit -f Apisync
git -C "$PHENO_ROOT" rm -f Apisync
git -C "$PHENO_ROOT" commit -m "chore(submodules): drop Apisync pin (superseded by apikit absorption)"
vim "$PHENO_ROOT/.gitmodules"   # remove [submodule "Apisync"] stanza
git -C "$PHENO_ROOT" add .gitmodules
git -C "$PHENO_ROOT" commit --amend --no-edit
```

If your consumer crate is *not* `phenotype-core` and the Apisync pin is
intentional, replace the URL with the absorbed manifest path:

```ini
[submodule "Apisync"]
    path = vendor/apikit
    url = https://github.com/KooshaPari/phenotype-tooling.git
    # use a path-filter sparse-checkout if you only need Apisync's slice:
    #   git config submodule.vendor/apikit.sparseCheckout true
```

### HexaKit ADR provenance

HexaKit's architecture ADR files at
`pheno/crates/hexa-kit/docs/adr/origin/001..005-apisync-*.md` carry the
"origin" lineage header `<!-- Migrated from KooshaPari/Apisync (archived
2026-06-19) — original commit d981353 -->`. These files continue to point
at the absorbing collection's mirror at
`phenotype-tooling/docs/absorbed-from-apikit/docs/governance/adr/001..005-*.md`
— no change required for downstream readers.

### Phenotype registry bindings

`phenotype-registry/docs/intent/Apisync.md` and
`phenotype-registry/docs/boundary/Apisync.md` remain stable (4 bound
prompts, role: `unknown`, last_verified: 2026-06-17). The pointer README on
the GitHub side does not invalidate the historical intent/boundary records;
these continue to back-route prompt reconstructions that reference
`Apisync` as a working context.

## Operational checklist (operator)

When this pointer `README.md` is pushed (or PR'd) to
`KooshaPari/Apisync`:

- [ ] Push branch with the new `README.md` to a feature branch (e.g.
      `chore/supersede-pointer-2026-09-01`).
- [ ] Open a PR against `KooshaPari/Apisync` `main`; the repo is archived,
      so the PR is a "documentation-only supersession" and will be admin-merged
      or applied via a workflow bypass.
- [ ] On merge, set the GitHub repo **Homepage** field to
      `https://github.com/KooshaPari/phenotype-tooling/tree/main/docs/absorbed-from-apikit`
      (per `GITHUB_ARCHIVE_POLICY` step 5).
- [ ] On merge, set the GitHub repo **Description** to
      `SUPERSEDED 2026-06-19 — migrated into apikit, absorbed into phenotype-tooling/docs/absorbed-from-apikit. Do not push here.`
      (per `GITHUB_ARCHIVE_POLICY` step 4).
- [ ] Append a registry audit row to `registry/audit-absorption-justification/apisync-2026-09-01.md`
      capturing the pointer README push for traceability.
- [ ] Leave a one-line note in the operator session log under
      `~/.forge/audit/<ts>-G2-B.md`.

## Notes

- Org rename to `zz-archive-Apisync` is held until the registry-wide rename
  sweep — current remote is the original name for traceability with the
  in-flight introspections.
- The absorbing collection's `CHANGELOG.md` is the long-form record; this
  `UPSTREAM.md` is the short-form repoint map.
- This document is paired with the sibling `README.md` (the new root of
  the archived remote) and `ABSORPTION.md` (provenance for this registry
  entry).
