# zz-pause

Long pause. No active development. Code preserved.

---

# ResearchLedger

Local-first research ledger and LLM knowledge base.

[![AI slop inside](https://sladge.net/badge.svg)](https://sladge.net) [![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/KooshaPari/ResearchLedger/total)](https://github.com/KooshaPari/ResearchLedger/releases)

The desktop app keeps Markdown and SQLite data local, preserves source provenance, and
exposes import/search/RAG/export adapters through a Tauri command boundary.

## Development

```bash
bun install
bun run dev
```

Tests and production build:

```bash
bun run test
bun run build
```

The desktop app supports a native local-vault picker, persisted vault status, GitHub
starred-repository import, manual LinkedIn permalink/content import, and browser-capture imports for Reddit and X
bookmarks, offline FTS5 search, and retrieval context with aligned citations.
Imported documents are written as Markdown under
the selected vault and indexed into a local SQLite database. Markdown export is compatible
with Obsidian and Logseq-style vault workflows.

GitHub uses the authenticated local GitHub CLI. The Rust backend reads the credential and
returns only an import summary to the UI; no GitHub credential crosses the renderer boundary.

For LinkedIn, paste a manually supplied permalink and content. Reddit saved posts and X
bookmarks use authenticated browser connectors:

```bash
bun run reddit:capture -- --profile "$HOME/Library/Application Support/ResearchLedger/reddit-profile" \
  --output "$HOME/.phenotype/researchledger/captures/reddit-capture.json"

bun run x:capture -- --profile "$HOME/Library/Application Support/ResearchLedger/x-profile" \
  --output "$HOME/.phenotype/researchledger/captures/x-capture.json"
```

Each connector opens a persistent local browser profile, waits for the user’s normal login
if needed, scrolls at a bounded rate, deduplicates post URLs, and writes a deterministic
capture file for import into the selected vault. None of them automate posting, messaging,
reactions, follows, votes, or other account actions.

### First-run: Playwright browser install

The capture scripts use Playwright’s Chromium binary. `bun install` runs a
`postinstall` hook (`scripts/postinstall.mjs`) that pre-fetches the browser so
the first capture feels instant — there is no prompt, no spinner, and no
~150 MB download during capture. The hook is platform-aware (Linux also pulls
system deps via `--with-deps`), idempotent (Playwright’s install is a no-op
when the browser is already cached at `~/Library/Caches/ms-playwright/`), and
skipped automatically when `CI=1` or `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`.

If the install-time hook fails (offline, restrictive network, missing sudo on
Linux) the capture scripts still detect a missing browser and run
`npx playwright install chromium` automatically — one time, as a safety net.
Subsequent runs use the cached install under `~/Library/Caches/ms-playwright/`.
You can also re-run manually:

```bash
bunx playwright install chromium
```

See [security](docs/SECURITY.md) and [testing](docs/TESTING.md) for data-handling and
verification rules.

### Optional local cross-encoder

Reranking is loopback-only and opt-in. Download a model explicitly, then run the
included adapter in a separate terminal:

```bash
hf download cross-encoder/ms-marco-MiniLM-L-6-v2 config.json model.safetensors \
  tokenizer.json tokenizer_config.json special_tokens_map.json vocab.txt \
  --local-dir "$HOME/.cache/huggingface/hub/rl-ms-marco-minilm"
RESEARCHLEDGER_RERANK_MODEL_PATH="$HOME/.cache/huggingface/hub/rl-ms-marco-minilm" \
  python3 scripts/local_reranker_server.py
RESEARCHLEDGER_RERANK_ENDPOINT=http://127.0.0.1:8082/v1/rerank \
RESEARCHLEDGER_RERANK_ENGINE=mlx \
RESEARCHLEDGER_RERANK_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2 \
  bun run smoke:rerank
```

The adapter binds only to `127.0.0.1`; no model or source text is uploaded.