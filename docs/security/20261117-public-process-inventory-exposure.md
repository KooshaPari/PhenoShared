# Public exposure: captured credentials in PhenoShared `state/` and absorbed trees

- **Date:** 2026-11-17
- **Repo:** `KooshaPari/PhenoShared` (**public**)
- **Severity:** high. Live-shaped credentials, readable by anyone, in a public repository.
- **Status:** disclosure record for a remediation PR. The repo is still public and the blobs
  are still in history at the time of writing.

## What was exposed

### 1. Process/env inventory dumps (38 files)

`state/full_process_inventory_*.json` at the tip of `main`. Each is a point-in-time capture:
host metadata plus an `env` object holding 123 environment variable names and values.

25 of the 38 carry credential-shaped values. Each of those 25 files carries the same four
values, so this is a small credential set repeated, not 100 unique secrets.

| Family (`env` name) | Shape | Length | Occurrences | Distinct |
|---|---|---|---|---|
| `OMNIROUTE_API_KEY` | `sk-`-prefixed | 35 | 25 | 1 |
| `ENCRYPTION_KEY` | opaque base64 | 44 | 25 | 1 |
| `FIREWORKS_API_KEY` | opaque | 26 | 25 | 1 |
| `SERVICE_KEY` | lowercase hex | 64 | 25 | 1 |

Distinctness was checked by hashing each value per file: all 25 files produced the same digest
per family (25/25 identical). No values are reproduced in this document.

### 2. Resume-state and session-extract dumps (2 files, agent-generated, not source)

- `state/session_resume_2026-07-24_019f6249.json` — GitHub OAuth token (`gho_…`, length 40).
- `state/codex_session_extracts/rollout-2026-07-03T17-52-31-*.md` — Hugging Face token
  (`hf_…`, length 37) and an OpenRouter key (`sk-or-…`, length 73) that gitleaks did not flag.

### 3. Absorbed vendored tree (2 files)

`docs/absorbed-from-PhenoTooling/docs/absorbed-from-QuadSGM/4sgm/backend/{database.py,seed.py}`
each embed a full Postgres DSN including a non-placeholder password for
`db.xerrnwvpdkywwugdtlma.supabase.co`.

## Who measured it

The closure ledger's D38.3 public-tree secret sweep, merged as the evidence artifact
`closure/evidence/public-surface-scan-phenoshared-20261117.md` in the private repo
`KooshaPari/host-ops` (PR #381). Triage there keeps every value masked.

## What this PR does

- Removes 38 `state/full_process_inventory_*.json` files from the tip of `main`.
- Removes 2 state dumps: the resume file and the session-extract transcript.
- Redacts only the password portion of the DSN in the 2 absorbed files to
  `REDACTED-ROTATE-ME`, preserving DSN shape, the files, and their provenance (absorbed files
  are vendored content, not ours to delete).
- Extends `.gitignore` so all three dump families cannot be committed again:
  `state/full_process_inventory_*.json`, `state/full_process_*.json`,
  `state/session_resume_*.json`, `state/codex_session_extracts/`.

## What this PR does NOT do

- **It does not remove the blobs from history.** Every value remains reachable in existing
  commits. Removing it from HEAD reduces casual exposure; it does not undo it.
- **It does not rotate anything.** Every value below must be treated as compromised and
  rotated. Rotation is an operator action; an agent must not rotate production credentials.
- **It does not purge history.** A real purge needs `git filter-repo` (or BFG) followed by a
  force-push of every affected ref, plus re-clone coordination. Policy forbids an agent from
  force-pushing, so this is left to the operator.
- **It does not change workflows or Sonar configuration.**

## Rotation list (operator action, no values below)

1. `ENCRYPTION_KEY` — symmetric encryption key (44-char base64). Data encrypted with the old
   key must be re-encrypted, or the old key retained only for legacy decryption.
2. `OMNIROUTE_API_KEY` — routing gateway key.
3. `FIREWORKS_API_KEY` — inference provider key.
4. `SERVICE_KEY` — 64-hex service credential.
5. GitHub OAuth token (`gho_…`) — revoke, then re-authorize the tool that minted it.
6. Hugging Face token (`hf_…`) — revoke in account settings.
7. OpenRouter key (`sk-or-…`) — revoke.
8. Supabase Postgres password for `db.xerrnwvpdkywwugdtlma.supabase.co` — rotate the database
   password, then update any deploy environment that still uses it.

Because the 25 inventory dumps carry identical values, one rotation per family covers every
copy in those files.

## Follow-ups

1. Rotate the eight families above and record the rotation date next to each.
2. Plan the history purge with `git filter-repo` across all affected refs and coordinate
   re-clones.
3. Audit the rest of `state/` and the absorbed trees for further captured material; treat
   both as untrusted until reviewed.
