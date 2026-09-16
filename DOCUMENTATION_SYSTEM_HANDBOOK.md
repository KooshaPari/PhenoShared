# Documentation Systems Handbook — Kush Ecosystem

> Agent-facing reference for understanding, creating, and maintaining documentation

---

## Executive Summary

Your workspace has multiple overlapping documentation systems driven by different needs:

1. **VitePress docsite** — human-facing documentation
2. **Docs Engine** — agent-driven doc lifecycle management  
3. **.llms index** — LLM context optimization
4. **CLAUDE.md files** — agent instruction context
5. **Governance framework** — quality standards

---

## Part 1: The Five Documentation Layers

### Layer 0 — Raw/Ephemeral (Not Published)

| Type | Path Pattern | Created By | Retention |
|------|--------------|------------|-----------|
| ConversationDump | `docs/research/CONVERSATION_DUMP_YYYY-MM-DD.md` | session-end hook | 90 days → archive |
| SessionMemory | `.claude/.../memory/MEMORY.md` | agent explicit | permanent |
| ScratchNote | `docs/scratch/YYYYMMDD-*.md` | any agent | 48h → promote or discard |
| AgentWorklog | `docs/reference/WORK_STREAM.md` | claim/complete | permanent |

### Layer 1 — Informal/Working (VitePress /lab/ View)

| Type | Path Pattern | Created By | Promotion |
|------|--------------|------------|-----------|
| IdeaNote | `docs/ideas/YYYY-MM-DD-{slug}.md` | agent / CLI | → ResearchDoc |
| ResearchDoc | `docs/research/{TOPIC}.md` | research agent | → DesignDoc/FR |
| DebugLog | `docs/debug/YYYY-MM-DD-{issue}.md` | any agent | → IncidentRetro |
| ChangeProposal | `docs/changes/{name}/proposal.md` | any agent | → ChangeDesign |

### Layer 2 — Formal/Spec (VitePress /docs/ View)

| Type | Path Pattern | ID System |
|------|--------------|-----------|
| PRD | `PRD.md` (root) | E{n}.{m} epics |
| FunctionalRequirements | `FUNCTIONAL_REQUIREMENTS.md` | FR-{CAT}-{NNN} |
| ADR | `docs/adr/ADR-{NNN}-{slug}.md` | ADR-{NNN} |
| UserJourney | `USER_JOURNEYS.md` | UJ-{N} |
| ArchitectureDoc | `docs/reference/ARCHITECTURE_*.md` | — |
| DesignDoc | `docs/plans/YYYY-MM-DD-{topic}-design.md` | — |

### Layer 3 — Delivery/Audit (VitePress /audit/ View)

| Type | Path Pattern | Trigger |
|------|--------------|---------|
| SprintPlan | `docs/sprints/SPRINT-{NN}.md` | sprint planning |
| ChangeDesign | `docs/changes/{name}/design.md` | proposal approved |
| Changelog | `CHANGELOG.md` | git tag |
| CompletionReport | `docs/reports/YYYY-MM-DD-{feature}-complete.md` | story done |

### Layer 4 — Retrospective/Knowledge (VitePress /kb/ View)

| Type | Path Pattern | Trigger |
|------|--------------|---------|
| SprintRetro | `docs/retros/SPRINT-{NN}-retro.md` | retrospective |
| EpicRetro | `docs/retros/EPIC-{id}-retro.md` | epic complete |
| KnowledgeExtract | `docs/kb/{topic}/{slug}.md` | nightly semantic indexer |

---

## Part 2: The Docs Engine System

### Architecture

```
src/docs_engine/
├── schema/              # Pydantic models
│   ├── base.py         # DocFrontmatter
│   └── registry.py     # Type → schema
├── templates/           # Jinja2 per type
│   ├── adr.md.j2
│   ├── idea.md.j2
│   ├── research.md.j2
│   └── ...
├── capture/            # Writer + hooks
│   ├── writer.py      # Validate → write → index
│   ├── session_hook.py
│   └── commit_hook.py
├── db/                 # SQLite
│   ├── schema.sql      # docs, relations, events
│   ├── indexer.py     # Frontmatter → SQLite
│   └── queries.py     # Search APIs
├── mcp/                # FastMCP
│   └── tools.py       # 7 tools
├── semantic/           # KB extraction
│   └── indexer.py    # Nightly extract
├── sidebar/            # VitePress
│   └── generator.py
├── hub/                # Federation hub
│   └── generator.py
└── cli/
    └── commands.py    # docs subcommand
```

### Database Schema (SQLite)

```sql
CREATE TABLE docs (
    path TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    status TEXT NOT NULL,
    title TEXT NOT NULL,
    layer INTEGER NOT NULL,
    date TEXT NOT NULL,
    author TEXT DEFAULT 'agent',
    session_id TEXT DEFAULT '',
    git_commit TEXT DEFAULT '',
    relates_to TEXT DEFAULT '[]',
    traces_to TEXT DEFAULT '[]',
    indexed_at TEXT NOT NULL,
    content_hash TEXT DEFAULT ''
);

CREATE TABLE relations (
    source_path TEXT,
    target_path TEXT,
    relation_type TEXT,
    PRIMARY KEY (source_path, target_path, relation_type)
);

CREATE TABLE events (
    event_type TEXT,
    doc_path TEXT,
    git_ref TEXT,
    timestamp TEXT,
    metadata TEXT
);
```

### MCP Tools (7 Tools)

| Tool | Function |
|------|----------|
| `thegent_doc_new` | Create from template + validation |
| `thegent_doc_search` | Full-text + frontmatter search |
| `thegent_doc_list` | List by type |
| `thegent_doc_export` | JSON for VitePress data loaders |
| `thegent_doc_sidebar` | Regenerate sidebar |
| `thegent_doc_semantic` | Run KB extractor |
| `thegent_doc_changelog` | git-cliff → CHANGELOG |

### CLI Commands (`docs` subcommand)

```bash
docs new idea "title"           # Layer 1
docs new research "topic"       # Layer 1
docs new adr "decision"        # Layer 2 (auto-increment ID)
docs new worklog --commit XYZ  # Layer 3
docs promote <path>             # Layer N → N+1
docs search "query"            # SQLite search
docs index rebuild              # Rebuild from all markdown
docs sidebar regenerate        # → sidebar-auto.ts
docs kb query "topic"          # Query knowledge base
docs hub                       # Generate federation hub
```

---

## Part 3: Git Hooks Integration

### Hooks → Docs Automation

| Hook | Script | Output |
|------|--------|--------|
| session-end | `session-end-write-dump.sh` | `CONVERSATION_DUMP_*.md` |
| post-commit | `post-commit-worklog.sh` | `WORK_STREAM.md` entry |
| post-tag | `post-tag-changelog.sh` | git-cliff → CHANGELOG.md |
| pre-commit | `pre-commit-docs.sh` | Link validation |

### Hook Configuration (`hooks/hook-config.yaml`)

```yaml
hooks:
  - name: session-end-write-dump
    script: hooks/session-end-write-dump.sh
    trigger: SessionEnd

  - name: post-commit-worklog
    script: hooks/post-commit-worklog.sh
    trigger: PostCommit

  - name: post-tag-changelog
    script: hooks/post-tag-changelog.sh
    trigger: PostTag
```

---

## Part 4: VitePress Integration

### Views (5)

| View | URL Path | Content |
|------|----------|---------|
| Lab | `/lab/` | Layer 1 (ideas, research, debug) |
| Docs | `/docs/` | Layer 2 (specs, PRDs, ADRs) |
| Audit | `/audit/` | Layer 3 (changelogs, completion reports) |
| KB | `/kb/` | Layer 4 (retros, knowledge extracts) |
| PM-Prep | `/pm-prep/` | Sprint plans, trackers |

### Auto Sidebar Generation

The `generate-sidebar.py` script reads doc types and frontmatter to auto-generate `docs/.vitepress/sidebar-auto.ts`.

`srcExclude` patterns (not built into VitePress):
- `docset/**`, `plans/**`, `research/**` (existing)
- `scratch/**` (Layer 0)
- `ideas/**`, `debug/**` (Layer 1 raw, included in /lab/ separately)

---

## Part 5: .llms Full-Text Index

### Purpose

Optimized for LLM context window — full-text search across all markdown.

### Location

- `.llms/docs/` — mirror of main docs with `.llms.txt` suffix

### Scripts

- `generate-llms-docs.py` — generates `.llms.txt` versions
- Runs on: pre-build, pre-commit

---

## Part 6: Context Documentation Process

### When Required (P0/P1)

1. Starting new technology integration
2. Implementing new protocol/SDK
3. Technology referenced in 3+ code locations
4. Research spike results in adoption decision

### Phases

1. **Preparation** — Check existence, assign owner, gather sources
2. **Extraction** — API specs, auth, concepts, edge cases
3. **Writing** — Use governance template, test examples
4. **Integration** — Create file, update INDEX.md, cross-reference
5. **Verification** — Peer review, commit, link from PR

### Required Sections

- Header (title, sources, fetch date)
- What is {Technology}
- Key Concepts (if applicable)
- API/Interfaces
- Authentication
- Code Examples (tested)
- Sources & References
- Quick Reference

---

## Part 7: Governance Framework

### Quality Standards

| Metric | Target | Measurement |
|--------|--------|-------------|
| Technical Accuracy | 100% | Automated + Manual |
| Broken Links | 0% | Link checker |
| Code Example Success | 100% | Test execution |
| Freshness | < 6 months | Last-updated timestamp |
| Completeness | 100% public APIs | Audit checklist |

### Review Workflow

```
Draft → Self-Review → Technical Review → Editorial Review → Approval → Release
```

### Versioning

- **Semantic**: MAJOR.MINOR.PATCH-METADATA
- **Required frontmatter**: version, last_updated, status, maintained_by

### Roles

| Role | Responsibility |
|------|----------------|
| Documentation Lead | Strategy, governance, release coordination |
| Maintainers | Domain quality, accuracy, updates |
| Contributors | Content creation, follow guidelines |
| Reviewers | Accuracy verification, feedback |

---

## Part 8: Key File Relationships

### Lifecycle Flow

```
IDEATION
  IdeaNote (draft) ──promote──► ResearchDoc (active) ──► DesignDoc
                                                  │
                                                  ▼
SPECIFICATION                              PRD + FR + ADR
      │                                         │
      ▼                                         ▼
EXECUTION ──► WorklogEntry ──► CompletionReport
      │                           │
      ▼                           ▼
RELEASE ───► git tag ──► Changelog (git-cliff)
      │
      ▼
LEARNING ──► Retro ──► KnowledgeExtract (semantic indexer)
                  │
                  ▼
          Bidirectional links (relates_to)
```

### Frontmatter for Traceability

```yaml
---
type: idea | research | prd | fr | adr | ...
status: draft | active | staging | published | archived
date: YYYY-MM-DD
title: "Human-readable"

# Traceability
relates_to: []      # bidirectional doc links
traces_to: []       # FR-XXX, ADR-NNN, E{n}.{m}
author: agent
session_id: ""
git_commit: ""

# Layer
layer: 0 | 1 | 2 | 3 | 4
tags: []
---
```

---

## Part 9: Validation Stages

### 2.1 Pre-Write Validation (docs_engine.capture.writer)

- **Pydantic Schema Enforcement**: `src/docs_engine/schema/base.py`
- **Type → Schema Mapping**: `src/docs_engine/schema/registry.py`

### 2.2 Post-Write Validation Scripts

| Script | Checks | Location |
|--------|--------|----------|
| `validate-docs.sh` | Markdown structure, titles, orphans, links | `scripts/validate-docs.sh` |
| `check-docs-links.py` | Internal/external link validity | `scripts/check-docs-links.py` |
| `audit-md-structure.sh` | Frontmatter completeness | `scripts/audit-md-structure.sh` |

### 2.3 Runtime Validation (Python Classes)

| Class | Purpose |
|-------|---------|
| `DocLinkChecker` | Async link validation (internal + external) |
| `CodeExampleValidator` | AST parsing for Python snippets |
| `SchemaValidator` | Pydantic model validation |

### 2.4 Quality Gates (hooks/pre-commit-docs.sh)

- validate frontmatter
- check link validity
- verify code examples syntax
- ensure proper file naming

---

## Part 10: Optimization Stages

### 3.1 Build-Time Optimization

| Tool | Purpose |
|------|---------|
| `generate-sidebar.py` | Auto-generate sidebar from doc structure |
| `generate-llms-docs.py` | Generate `.llms.txt` for LLM context |
| `incremental_generation.py` | Only rebuild changed docs |
| `parallel_generation.py` | Multi-thread doc generation |

### 3.2 Performance Optimizer (docgen/performance.py)

| Method | Function |
|--------|----------|
| `optimize_code_splitting()` | Webpack chunk config |
| `optimize_images()` | WebP/AVIF conversion, lazy loading |
| `generate_image_html()` | Optimized img tags with srcset |

### 3.3 Content Optimization

| Feature | Implementation |
|---------|---------------|
| Sticky navigation | `sticky_nav.py` |
| Edit links | `edit_links.py` |
| Content tabs | `content_tabs.py` |
| Math support | `math_support.py` (KaTeX) |
| Code annotation | `code_annotation.py` |

### 3.4 Fragment Expansion (scripts/expand-fragments.sh)

Processes fragmented/incomplete docs for expansion:

```bash
FRAGMENTS=(
    "research/scratchpad/session_review.md:P1"
    "research/GOVERNANCE_WP_GAPS.md:P1"
)
```

---

## Part 11: PhenoDocs - Federation Hub

### Overview

PhenoDocs is the VitePress federation hub that aggregates documentation from multiple projects in the Kush ecosystem.

### Usage

```bash
# Generate hub
docs hub --hub-dir ../phenodocs

# Or via Python
from docs_engine.hub.generator import HubGenerator

projects = {
    "thegent": "/path/to/thegent/docs",
    "pheno-sdk": "/path/to/pheno-sdk/docs"
}
gen = HubGenerator(hub_dir="phenodocs", projects=projects)
gen.generate()
```

### Configuration

Projects are configured in the hub generator with name → path mappings.

---

## Key Files for Reference

| Category | File |
|----------|------|
| **Design** | `docs/plans/2026-02-21-doc-system-design.md` |
| **Taxonomy** | `DOCUMENTATION_TAXONOMY.md` |
| **Governance** | `docs/governance/DOCUMENTATION_GOVERNANCE.md` |
| **Context Process** | `docs/governance/CONTEXT_DOCS_PROCESS.md` |
| **Schema** | `src/docs_engine/schema/base.py` |
| **Templates** | `src/docs_engine/templates/*.j2` |
| **Link Checker** | `src/thegent/docgen/link_checker.py` |
| **Code Validator** | `src/thegent/docgen/code_validator.py` |
| **Validation Script** | `scripts/validate-docs.sh` |
| **Hook Config** | `hooks/hook-config.yaml` |
| **Hub Generator** | `src/docs_engine/hub/generator.py` |

---

## Opinionated Design Decisions

| Decision | Rationale |
|----------|-----------|
| **VitePress** over Fumadocs | Existing 6K-line sidebar, 8 plugins, full enhancement plan |
| **SQLite** for index | Zero ops, stdlib, upgrade path to Postgres |
| **Pydantic** validation | Type safety, frontmatter enforcement |
| **Hybrid promotion** | Auto-promote by age + agent-triggered rewrite + status field |
| **Layer exclusion** | Raw Layer 0 excluded from build, extends existing srcExclude |
| **Jinja2 templates** | Per-type templates in `docs_engine/templates/` |

---

*This handbook is maintained by the Documentation Lead and updated as the system evolves.*
