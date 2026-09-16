# Getting Started

Welcome to PhenoDocs! This guide will help you set up and use the federation hub.

## Prerequisites

- [Bun](https://bun.sh/) 1.x (package manager + runtime for this repo)
- [uv](https://docs.astral.sh/uv/) + **CPython 3.14+** (pre-commit, `uv run` scripts)

See [Toolchains](/guides/tooling).

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourorg/phenodocs.git
cd phenodocs
```

### 2. Install Dependencies

```bash
bun install
uv sync --group dev
```

### 3. Start Development Server

```bash
bun run dev
```

Visit `http://localhost:5173` to see your docs hub.

## Adding Your First Project

### Step 1: Prepare Your Project Docs

Ensure your project documentation follows the doc taxonomy:

```text
your-project/
├── docs/
│   ├── ideas/           # Layer 1
│   ├── research/        # Layer 1
│   ├── prd/            # Layer 2
│   ├── adr/            # Layer 2
│   ├── reports/        # Layer 3
│   └── retros/         # Layer 4
```

### Step 2: Link Your Project

Option A: Git Submodule

```bash
git submodule add https://github.com/yourorg/your-project-docs.git projects/your-project
```

Option B: Update HubGenerator

```python
from docs_engine.hub.generator import HubGenerator

projects = {
    "your-project": "/path/to/your-project/docs"
}
```

### Step 3: Regenerate Hub

```bash
docs hub --hub-dir .
```

## Understanding the Views

### /lab/ — Working Documents

- IdeaNotes
- Research documents
- Debug logs
- Change proposals

Use this view for active experimentation and ideation.

### /docs/ — Formal Specifications

- Product Requirements (PRDs)
- Architecture Decision Records (ADRs)
- Functional Requirements
- Design documents

This is your source of truth for specifications.

### /audit/ — Delivery Tracking

- Sprint plans
- Changelogs
- Completion reports

Track what has been delivered and when.

### /kb/ — Knowledge Base

- Sprint retrospectives
- Epic retrospectives
- Knowledge extracts

Learn from past work.

## Next Steps

- Read the [Architecture Guide](/guide/architecture.md)
- Explore the [API Reference](/reference/api.md)
- Learn about [Governance](/governance/overview.md)
