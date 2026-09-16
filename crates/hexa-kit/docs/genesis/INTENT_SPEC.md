# intent.md + docs/intent/

Intent documentation captures **why the project exists**, with **deterministic prompt provenance** from agent sessions. It grounds LLM synthesis in verbatim user language — not paraphrase-from-memory.

**AgilePlus trace:** FR-GENESIS-005 (user intent provenance per repo)

Bootstrap: [`templates/genesis/intent.md`](../../templates/genesis/intent.md), [`templates/genesis/docs/intent/`](../../templates/genesis/docs/intent/)

## Root file: `intent.md`

One-page executive intent. Keep scannable; detail lives in `docs/intent/`.

### Required sections

1. **Problem statement** — user language, not marketing fluff
2. **Success criteria** — measurable checkboxes where possible
3. **Non-goals** — link `charter.md#out-of-scope`; repeat critical exclusions
4. **Originating prompts** — table linking to `docs/intent/prompts/<tool>/`
5. **Synthesized goals** — link `docs/intent/synthesis.md`; split confirmed vs inferred
6. **Agent assumptions log** — table + link `docs/intent/assumptions.md`

### Prompt index table format

| Date | Tool | Session | Summary |
|------|------|---------|---------|
| 2026-06-16 | cursor | `b561a593-…` | [genesis standard ask](docs/intent/prompts/cursor/20260616-….md) |

Refresh command (document in intent.md footer):

```bash
python scripts/extract-intent-prompts.py \
  --out-dir docs/intent/prompts \
  --repo <RepoName> \
  --sources cursor,forge,claude,codex
```

## Folder: `docs/intent/`

```
docs/intent/
  README.md           # how to refresh provenance
  synthesis.md        # LLM synthesis (grounded, cites prompts)
  assumptions.md      # agent belief → action → validation
  prompts/
    README.md         # scrape sources (required even with .gitkeep)
    .gitkeep          # keeps empty tool dirs in git
    cursor/           # scraped from agent-transcripts
    forge/            # forge conversation exports
    claude/           # Claude Code session logs
    codex/            # Codex session logs
```

## Prompt record format

Each file: `docs/intent/prompts/<tool>/YYYYMMDD-<session-id>-t<N>.md`

```markdown
---
source: cursor
session_id: b561a593-1729-44da-b90d-0cfbdf9d72ef
captured_at: 2026-06-16T12:00:00Z
verbatim_hash: sha256:abc123...
repository_context: <REDACTED>/HexaKit
transcript: ~/.cursor/projects/.../b561a593....jsonl
turn: 1
---

## Verbatim user prompt

<paste exact user text — no paraphrase>

## Session reference

- transcript: `~/.cursor/projects/.../agent-transcripts/<id>.jsonl`
- turn: 1
- related_files: [optional list of paths touched in same turn]
```

### Rules

- **Never paraphrase** in the verbatim section — synthesis belongs in `synthesis.md`
- Compute `verbatim_hash` as SHA-256 of the verbatim prompt body (excluding frontmatter)
- One user message per file for turn-level traceability; combine only if user sent a single compound message
- Do not commit secrets from logs — redact tokens; note redaction in frontmatter `redacted: true`

## Scrape sources

| Tool | Log location | Scraper module |
|------|--------------|----------------|
| **Cursor** | `~/.cursor/projects/<project>/agent-transcripts/*.jsonl` | `extract-intent-prompts.py --sources cursor` |
| **forge** | `~/forge/` exports; `forge conversation list` | `--sources forge` |
| **Claude Code** | `~/.claude/projects/` session logs | `--sources claude` |
| **Codex** | `~/.codex/` or tool-specific session store | `--sources codex` |

See [`templates/genesis/docs/intent/prompts/README.md`](../../templates/genesis/docs/intent/prompts/README.md).

## Scraping pipeline

```bash
# From HexaKit or vendored script
python scripts/extract-intent-prompts.py \
  --out-dir docs/intent/prompts \
  --repo HexaKit \
  --sources cursor,forge,claude,codex \
  --since 2026-01-01
```

Post-scrape:

1. Append rows to `intent.md` originating prompts table
2. Run synthesis (human or LLM) into `synthesis.md`
3. Update `assumptions.md` for new agent actions
4. Bump `okf/manifest.okf.yaml` → `provenance.last_scrape`

## synthesis.md structure

Template: [`templates/genesis/docs/intent/synthesis.md`](../../templates/genesis/docs/intent/synthesis.md)

| Section | Purpose |
|---------|---------|
| **Themes** | Cluster prompts by topic; cite prompt files |
| **Confirmed goals** | User-validated (explicit in prompts or follow-up) |
| **Inferred goals** | Agent interpretation — mark `Validate? pending` |
| **Conflicts / tensions** | Opposing prompts → charter/SOTA resolution |
| **Rejected / deferred** | Explicit non-goals with reason |
| **Recommended next actions** | What agents should do without re-asking user |

### Synthesis rules

1. Every inferred goal must cite ≥1 prompt file
2. Paraphrase user language in themes — link to verbatim source
3. Conflicts trigger charter review before merge of conflicting work
4. Do not delete old themes; mark superseded with date

## assumptions.md structure

| Assumption | Evidence | Action taken | Validated? | Date |
|------------|----------|--------------|------------|------|
| User wants genesis-only HexaKit | cursor/20260616-… | Wrote STANDARD.md | pending | 2026-06-16 |

Agents append rows when they act on unconfirmed inference.

## Refresh policy

| Event | Action |
|-------|--------|
| New major feature | Scrape + append prompts; update synthesis |
| Quarterly | Re-synthesize; bump OKF `last_scrape` |
| Charter change | Reconcile intent non-goals and synthesis conflicts |
| User corrects agent | Add prompt capture + mark assumption validated |

## LLM grounding notes for agents

Before large pivots:

1. Read `charter.md` — do not expand scope to "help"
2. Read `synthesis.md` confirmed goals first, inferred second
3. Append new user prompts to `prompts/` before implementing ambiguous asks
4. Update synthesis when user confirms or rejects inferred goals

## Related specs

- [STANDARD.md](STANDARD.md)
- [OKF.md](OKF.md) — `provenance` block
- [CHARTER_SPEC.md](CHARTER_SPEC.md) — non-goals alignment
