# Ask Register Location

## Absolute path (primary register store)

```
/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-registry/asks-ledger/register.json
```

## Format

**JSON** (git-tracked, non-derived, canonical source of truth).

Top-level keys observed:

| key | type | value |
|---|---|---|
| `generated_at` | str | `2026-11-05T21:24:22` |
| `count` | int | `2259` |
| `records` | list | **2259** items (one per ask, with verbatim `quote`) |

## Table names

JSON has no tables. The derived **sqlite** projection of the same register is:

```
/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-registry/asks-ledger/ledger.db
```

Table list (read-only, `mode=ro`):

```
reg_answers  reg_ask_messages  reg_ask_tags  reg_asks  reg_categories
reg_provenance  reg_sessions  reg_tags  reg_tasks  reg_transactions  reg_utterances
```

Sibling stores in the same directory (not canonical):

- `asks.db` — older sqlite copy, **unprefixed** table names (`asks`, `provenance`, `answers`,
  `ask_messages`, `ask_tags`, `categories`, `sessions`, `tags`, `tasks`, `transactions`,
  `utterances`); `asks` = 2259.
- `reg_asks.db` — **0 bytes**, empty placeholder (build script docstring names it, but
  `build-asks-db.py` actually writes `ledger.db`).
- `asks.json` — intermediate build output (gitignored).

## Ask count (observed)

| store | table / key | count |
|---|---|---|
| `register.json` | `records` array length | **2259** |
| `register.json` | `count` field | **2259** |
| `ledger.db` | `reg_asks` | **2259** |
| `ledger.db` | `reg_provenance` | **2259** |
| `asks.db` | `asks` | **2259** |
| `asks.db` | `provenance` | **2259** |

Corroborating doc: `asks-ledger/REGISTER.md` line 3 — "Total distinct asks: **2259**".

## Repo branch

Repository containing the register:
`/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-registry`

```
git rev-parse --abbrev-ref HEAD  ->  docs/corpus-record-final-state
```

(For reference, the other scanned root `PhenoShared` is on `feat/researchledger-refresh-tool`;
it holds `researchledger/ingest/ask_research_ledger*.py` tooling, not the 2,259-ask register.)

## Notes

- `*.db` is gitignored in `asks-ledger/.gitignore`; `register.json` is deliberately tracked
  ("build-asks.py reads them as read-only sources and nothing in this repo generates them").
- `~/CodeProjects/docs/reports/imessage-asks-20261104/` holds a parallel copy of the build
  scripts (`build-asks-db.py`, `schema.sql`, `reload-d1.py`, `d1-sync-state.json`), not the
  register store itself.
