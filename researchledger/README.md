# researchledger

Shared tooling for the Phenotype research-ledger corpus: one SQLite database that
accumulates conversations, prompts, and extracted entities from every harness
(claude, codex, cursor, jcode, kcode, forge, gemini, chatgpt, imessage).

This package exists because the corpus has twice been damaged in ways nothing
reported:

- **2026-10-15** — a symlink was left on the canonical path, so writes went
  somewhere else.
- **2026-11-10** — every guard constant had drifted off the real corpus. The
  guard "worked" against a path that no longer existed while the live 20.9 GiB
  corpus accepted unrestricted writes, and `SEALED_BACKUP` pointed at a
  directory that had been repurposed for something unrelated. Nothing failed,
  because nothing compared the constants against reality.

## What `corpus_guard` does

`guard_write_target(path, allow_canonical=False)` is called by every writer
before it opens its target. It refuses, as a hard stop:

| Target | Behaviour |
|---|---|
| The sealed archive, or anything inside `SEALED_ARCHIVE_DIR` | Always refused. No flag, no env var. |
| A `RETIRED_CANONICALS` path | Refused by name: writing there splits the corpus in two. |
| The canonical corpus, when it is missing | Refused: never create an empty corpus over a lost one. |
| The canonical corpus, when it is a symlink | Refused: this is the shape of the 2026-10-15 loss. |
| The canonical corpus, without opt-in | Refused unless `--allow-canonical` or `ANALYSIS_ALLOW_CANONICAL=1`. The env path logs to stderr so unattended runs leave a trace. |

`assert_corpus_sane()` is the read-side tripwire: the corpus must exist, be a
regular file (not a symlink), and be non-empty.

## Configuration

Everything resolves to a real path and is overridable, so a checkout or a restore
drill needs no code change.

| Variable | Purpose |
|---|---|
| `ANALYSIS_CANONICAL_DB` | Live corpus location. |
| `ANALYSIS_SEALED_BACKUP` | The sealed read-only archive. |
| `ANALYSIS_SEALED_DIR` | Directory containing it; the whole tree is unwritable. |
| `ANALYSIS_ALLOW_CANONICAL` | `1` lets an unattended pipeline write the corpus. Logged, never silent. |

The sealed archive is scoped as a *directory* rather than one filename on
purpose: protection keyed to a single dated filename drifts out of view as soon
as the next backup is taken, which is exactly the 2026-11-10 failure mode.

## Tests

```bash
python -m pytest researchledger/tests -q
```

The suite never reads or writes the production corpus: every path is a
`tmp_path` fixture or monkeypatched. It includes two host tripwires that fail
loudly if `CANONICAL` or `SEALED_BACKUP` stops being a real, non-symlinked,
non-empty regular file (and for the archive: unwritable, inside the guarded
directory, and the same size as the live corpus).

## History

Extracted from `KooshaPari/analysis-archive`, where it lived beside the ingest
pipeline it protects. That repository was a per-task archive; the operator
directive of 2026-11-11 is that shared code belongs in `PhenoShared` and records
belong in `PhenoRegistry` rather than in new archives.
