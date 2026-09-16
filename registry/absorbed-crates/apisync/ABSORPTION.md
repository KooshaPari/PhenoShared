# Absorbed Crate: Apisync (KooshaPari/Apisync)

> Pointer provenance — Apisync was **not** absorbed directly into the registry.
> Its content first migrated downstream into the `apikit` crate
> (`KooshaPari/apikit`), and `apikit` was absorbed (2026-06-21) into
> `phenotype-tooling/docs/absorbed-from-apikit/`. This entry exists in the
> registry only to host the new pointer `README.md` that sits on the
> archived `KooshaPari/Apisync` GitHub remote.

## Source

| Field | Value |
| --- | --- |
| Source repo | `KooshaPari/Apisync` |
| Source state at absorption | Archived (read-only) on GitHub — 2026-06-19 |
| Source description (archived) | "Universal API toolkit — REST, GraphQL, WebSocket adapters (Rust, scaffold, dormant)" |
| Immediate successor | `KooshaPari/apikit` (also archived 2026-06-21) |
| Active canonical home | `KooshaPari/phenotype-tooling/docs/absorbed-from-apikit/` |
| Pointer artifact (this entry) | `README.md` — written for push to `KooshaPari/Apisync` root |
| Registry row | See `registry/chokepoints.json` and `registry/absorbed-crates/README.md` |

## Why a pointer entry

Per
[`phenotype-omlx/docs/guides/GITHUB_ARCHIVE_POLICY.md`](https://github.com/KooshaPari/phenotype-omlx/blob/main/docs/guides/GITHUB_ARCHIVE_POLICY.md),
archived repos on this org MUST NOT be deleted. The required cutover shape is:

1. Mirror needed history/branches into the canonical home.
2. Rename to `zz-archive-<original-name>`.
3. Archive the remote (read-only).
4. Description: `SUPERSEDED YYYY-MM-DD — … mirrored to <canonical>. Do not push here.`
5. Homepage → canonical URL.
6. **Optional root `SUPERSEDED.md`** *(or `README.md` that acts as one).*

Apisync is currently in steps 1–5 (org-wide rename is held until the central
registry sweep closes), and step 6 is being completed with this entry.
The `README.md` in this directory is the new root README that points the
`KooshaPari/Apisync` remote at its upstream.

## Migration trail

```
KooshaPari/Apisync           2026-06-19   archived (this commit, step 1–5)
        │                                  content extracted into
        ▼                                  KooshaPari/apikit (v0.1.0 source of truth)
KooshaPari/apikit            2026-06-21   archived
        │                                  full content absorbed
        ▼                                  (governance + src + CI + tooling + docs)
KooshaPari/phenotype-tooling/
  docs/absorbed-from-apikit/             active canonical home — 107 tracked files
                                          + 9 gitlinks preserved as `.GITLINK`
```

Absorption events, with provenance:

| Date | Source → Target | Documented in |
| ---- | --------------- | ------------- |
| 2026-06-19 | `KooshaPari/Apisync` → archived (this commit) | Wave 14 task #1, `phenotype-registry/docs/operations/wave14-gateway-ssot-2026-06-17.md` |
| 2026-06-20 | `Apisync` governance/docs/CI/tooling → absorbed into `apikit` | `phenotype-tooling/docs/absorbed-from-apikit/CHANGELOG.md` § "2026-06-20 — Absorbed governance, docs, CI, and tooling from archived Apisync repo" |
| 2026-06-20 | Second-pass absorption (root configs, agile-plus specs, legacy manifests) | `phenotype-tooling/docs/absorbed-from-apikit/CHANGELOG.md` § "2026-06-20 — Second-pass absorption" |
| 2026-06-21 | `KooshaPari/apikit` → archived; content absorbed into `phenotype-tooling/docs/absorbed-from-apikit/` | `phenotype-tooling/docs/absorbed-from-apikit/ABSORPTION.md` |
| 2026-09-01 | `KooshaPari/Apisync` root `README.md` replaced with the pointer in `phenotype-registry/registry/absorbed-crates/apisync/README.md` (this entry) | G2.B worklog entry, this `ABSORPTION.md` |

## Contents delivered by this entry

```
phenotype-registry/registry/absorbed-crates/apisync/
├── README.md       # new pointer README → pushed to KooshaPari/Apisync root
├── ABSORPTION.md   # this file — provenance of the pointer
└── UPSTREAM.md     # supersession chain + repoint guidance for submodules/Cargo
```

No source `src/`, `Cargo.toml`, `docs/`, etc. are copied here. Those live in
the absorbing collection at `phenotype-tooling/docs/absorbed-from-apikit/`
with `.apisync.md` suffixes on governance docs to disambiguate from
apikit's own files.

## Verification

- `KooshaPari/Apisync` GitHub remote is archived: `isArchived: true`.
- `KooshaPari/apikit` GitHub remote is archived (deleted 2026-06-18 successor
  `apikit-httpora-final` is gone; archived state of `apikit` itself confirmed
  via the absorption `ABSORPTION.md` referencing `isArchived: true`).
- `phenotype-tooling/docs/absorbed-from-apikit/` is the active canonical home
  with a dated `CHANGELOG.md` entry for the absorption.
- The HexaKit/phenotype-core workspace no longer pins to the Apisync
  submodule as of Wave 14 task #1 (HexaKit #271: validation/string pin
  repointed to `KooshaPari/phenotype-types` main).

## Notes

- This entry is intentionally **pointer-only** (no source clone, no workspace
  member, no federation handoff). The full source sits in the absorbing
  collection; this entry exists solely to capture the GitHub-side README
  replacement required by the archive policy step 6.
- The corresponding registry audit row is `repo-Apisync → superseded`
  (registry status: `active` bindings preserved for historical prompt
  reconstruction, per `docs/intent/Apisync.md` and `docs/boundary/Apisync.md`).
- The `CHANGELOG.apisync.md` (downstream) and this entry together form the
  end-to-end provenance. Either alone is sufficient for audit; both are
  preferred.
