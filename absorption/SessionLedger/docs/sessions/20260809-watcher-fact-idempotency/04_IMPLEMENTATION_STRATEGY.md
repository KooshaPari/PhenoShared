# Implementation strategy

Use a deterministic content identity for SQLite memory facts and SQLite primary-key conflict handling. This fixes the durable boundary where duplicates are created and avoids debouncing heuristics that could discard legitimate later edits.
