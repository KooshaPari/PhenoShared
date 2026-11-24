# Architecture Guide

Understanding how PhenoDocs works under the hood.

## System Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│                        PhenoDocs Hub                             │
├─────────────────────────────────────────────────────────────────┤
│  .vitepress/          # VitePress config & theme                │
│  docs/               # Hub-specific docs                         │
│  projects/           # Aggregated project docs (submodules)     │
│  package.json        # Bun / VitePress dependencies               │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     docs_engine (Python)                         │
├─────────────────────────────────────────────────────────────────┤
│  hub/generator.py    # HubGenerator class                        │
│  db/                 # SQLite index                              │
│  cli/commands.py     # docs hub command                          │
│  mcp/tools.py        # MCP tools                                 │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Source Projects                               │
├─────────────────────────────────────────────────────────────────┤
│  thegent/docs/       # Project A docs                            │
│  pheno-sdk/docs/    # Project B docs                             │
│  cliproxy/docs/     # Project C docs                             │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### HubGenerator

The `HubGenerator` class is the main entry point:

```python
from docs_engine.hub.generator import HubGenerator
from pathlib import Path

projects = {
    "thegent": "/path/to/thegent/docs",
    "pheno-sdk": "/path/to/pheno-sdk/docs"
}

gen = HubGenerator(
    hub_dir=Path("phenodocs"),
    projects=projects
)
gen.generate()
```

### What it generates

1. **index.md** — Landing page with project links
2. **.vitepress/config.ts** — Navigation from project map
3. **package.json** — VitePress dependencies

## Data Flow

### 1. Project Documents Created

Agent or human creates docs in source project:

```text
thegent/docs/ideas/2026-02-24-new-feature.md
```

### 2. Git Hook Triggers

- `post-commit` → updates worklog
- `session-end` → dumps conversation
- `post-tag` → generates changelog

### 3. Hub Regeneration

```bash
# Manual
docs hub --hub-dir ../phenodocs

# Or automatic via CI/CD
```

### 4. VitePress Build

```bash
bun run build
# Output: .vitepress/dist
```

## Layer System

Each layer has distinct properties:

| Layer | Path Pattern | Visibility | Auto-promotion |
|-------|--------------|------------|-----------------|
| 0 | scratch/**, memory/** | Internal | 48h → discard |
| 1 | ideas/**, research/** | /lab/ | Manual |
| 2 | prd/**, adr/**, specs/** | /docs/ | Status → published |
| 3 | reports/**, changelogs/** | /audit/ | On delivery |
| 4 | retros/**, kb/** | /kb/ | On close |

## Frontmatter Schema

All aggregated docs must have proper frontmatter:

```yaml
---
type: idea | research | prd | adr | fr | report | retro | kb
status: draft | active | staging | published | archived
date: YYYY-MM-DD
title: "Human-readable title"
layer: 0 | 1 | 2 | 3 | 4
relates_to: ["path/to/other.md"]
traces_to: ["FR-001", "ADR-023"]
author: agent | human
---
```

## Search & Indexing

### Human Search

VitePress built-in search (Algolia or local)

### AI Search

`.llms.txt` generation for each doc:

```bash
python scripts/generate-llms-docs.py
```

Output: `.llms/docs/filename.llms.txt`

## Deployment

### Static Export

```bash
bun run build
# Deploy .vitepress/dist to any static host
```

### Docker

```dockerfile
FROM oven/bun:1-alpine
WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile
COPY . .
RUN bun run build
EXPOSE 4173
CMD ["bun", "run", "preview"]
```

## Performance Considerations

- **Incremental builds** — Only rebuild changed docs
- **Lazy loading** — Images and code blocks
- **Pre-fetching** — Link pre-fetch on hover
- **CDN** — Deploy to edge CDN

## Security

- No server-side execution
- Static only
- Review submodules for malicious content
- Sanitize user-generated links
