# Absorption routing plan, 2026-11-17

Answering Q11-D and Q12-D ("absorb all, route by full app vs library vs private
data"). Full table in `ROUTING-2026-11-17.txt`; regenerate with
`python scripts/route_repos.py <repo> ...`.

## The rule as applied

| Content | Destination |
|---|---|
| Data or documentation only | `PhenoRegistry/repos/<name>/tree/` |
| Full application | `PhenoShared/apps/<name>/` |
| Library | `PhenoShared/libs/<name>/` |
| **Private repository whose content is code** | `PhenoRegistry/repos/<name>/tree/` pending a publish decision |

That last row is not the rule as stated. It is a refusal to apply the rule
blindly: publishing is irreversible and 27 of the 35 repositories in scope are
private.

## 35 repositories, 23 app / 9 lib / 3 data

### Public, ready to absorb into PhenoShared (5)

| Repository | Files | Kind | Destination |
|---|---:|---|---|
| `slipstream` | 2,061 | app | `PhenoShared/apps/slipstream/` |
| `zz-ref-HeliosCLI` | 6,387 | app | `PhenoShared/apps/zz-ref-HeliosCLI/` |
| `zz-ref-HeliosLite` | 1,560 | app | `PhenoShared/apps/zz-ref-HeliosLite/` |
| `claude-plugins-official` | 765 | lib | `PhenoShared/libs/claude-plugins-official/` |
| `clap-ext` | 29 | lib | `PhenoShared/libs/clap-ext/` |

### Data only, ready for the registry (3)

`rule30-research` (6 files), `browser-infra` (6), `phenotype-cvp-audit-2026-09-14` (6).

### Private code, blocked on a publish decision (27)

`audit-snapshot-*` ×9 (36,300 files), `BytePort` (680), `Personal` (258),
`PhenoVCS` (133), `audit-system` (454), `cvp-fixture` (17), `dagrun` (192),
`harness-ops` (69), `phenotype-landing` (550), `zz-aa-dep-AirLock` (775),
`argis-extensions-preserved-20261114` (1,628), `cliproxyapi-plusplus` (3,129),
`HarnessDesk` (249), `StealthStartup` (34), `chatta` (4,521),
`phenoreg-browser-audit` (367), `phenoDesign-visual-production-v2` (179),
`zz-HexaKit` (358), `zz-argis-extensions` (304).

Their content is code, so the rule says PhenoShared. They are private, so doing
that publishes them to a public repository. That is a one-way door and it needs
an explicit decision, not an inferred one.

## Two classifier corrections worth recording

Both were found by reading the output rather than trusting it:

1. **`audit-snapshot-OmniRoute` was filed as a library.** It is a 13,989-file
   Next.js app. The cause was `lib_hits` counting every `index.ts`, and shadcn
   ships hundreds of them, which swamped the app score. Next.js and SvelteKit
   route directories are now decisive rather than scored, and the library-path
   count is capped.
2. **Every repository reported as public.** The router read `isPrivate`, which is
   a `gh repo list --json` field name; the raw API says `private`. The
   visibility column was silently wrong for all 35 rows, and it is the column
   that decides whether code gets published.

Both are the same failure mode as the earlier BytePort and `host-ops` mistakes: a
convenient signal standing in for the thing that actually matters.

## Method, and its limits

Classification uses file-path signals only: framework route directories, root
entry points, manifests, and whether any source file exists at all. It never reads
file contents.

Known weaknesses, left visible rather than papered over:

- `phenotype-landing` is a landing *site* and is filed as a library.
- `zz-aa-dep-AirLock` is a dependency fork filed as an app because it has a Go
  main package.
- `StealthStartup` (34 files) is too small for any signal to be reliable.

Routing decides a directory, not a deletion, so a wrong call is a `git mv` to fix.
It was still worth correcting the two signal bugs, because the same code now
decides whether private code is published.
