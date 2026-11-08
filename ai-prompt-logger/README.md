# ai-prompt-logger — Multi-Agent Prompt Logging & Observability

[![AI Slop Inside](https://sladge.net/badge.svg)](https://sladge.net)

Unified logging and observability layer for AI agent prompts and interactions. Captures prompts, responses, latencies, and error traces from multiple AI agent platforms (Claude, Cursor, Forge, Codex, etc.) into a centralized queryable database.

## Overview

**ai-prompt-logger** bridges the gap between agent platforms and observability infrastructure. It scrapes, normalizes, and persists agent activity across heterogeneous AI platforms, enabling analysis, debugging, and compliance tracking of agent-generated outputs.

**Core Mission**: Provide transparent, queryable observability of agent behavior without vendor lock-in, supporting multi-agent orchestration and audit trails.

## Technology Stack

- **Language**: Python (3.9+)
- **Database**: SQLite (default), PostgreSQL (optional)
- **Async Runtime**: AsyncIO, aiohttp
- **Serialization**: JSON, Protocol Buffers
- **Observability**: OpenTelemetry SDK for tracing
- **Testing**: Pytest with fixtures

## Key Features

- **Multi-Agent Support**: Unified interface for Claude, Cursor, Forge, Codex, OpenCode, Factory Droid, Kilo Code
- **Auto-Scraping**: Background agent that continuously polls agent platforms for new interactions
- **Schema Normalization**: Convert heterogeneous agent outputs to canonical schema
- **Queryable Database**: SQLite/PostgreSQL backend with full-text search on prompts
- **Latency Tracking**: Capture response times, token usage, costs per interaction
- **Error Attribution**: Link failed agent runs to root causes for debugging
- **Batch Export**: Export prompt logs in multiple formats (JSON, CSV, Parquet)
- **Redaction**: PII masking and compliance controls for sensitive data
- **Audit Trail**: Immutable log of all logging operations with timestamps

## Quick Start

```bash
# Navigate to sub-crate
cd /Users/<REDACTED>/CodeProjects/Phenotype/repos/PhenoObservability/ai-prompt-logger

# Install dependencies
pip install -e ".[dev]"

# Configure database (SQLite default)
export PROMPT_DB_URL="sqlite:///prompts.db"

# Run logger daemon
python -m prompt_logger serve --port 9091

# Log a prompt programmatically
python -c "
from prompt_logger import PromptLogger
logger = PromptLogger()
logger.log_prompt(
    agent='claude',
    prompt='What is the capital of France?',
    response='The capital of France is Paris.',
    metadata={'conversation_id': '123', 'user': 'alice'}
)
"

# Query logged prompts
python -m prompt_logger query --agent claude --limit 10
```

## Project Structure

```
ai-prompt-logger/
├── README.md                     # This file
├── CLAUDE.md                     # Development guidelines
├── pyproject.toml                # Python project config
├── setup.py                      # Installation script
├── src/
│   └── prompt_logger/
│       ├── __init__.py          # Package exports
│       ├── logger.py            # Core PromptLogger class
│       ├── adapters/            # Agent-specific adapters
│       │   ├── claude.py
│       │   ├── cursor.py
│       │   ├── forge.py
│       │   └── codex.py
│       ├── storage/             # Database layer
│       │   ├── sqlite.py
│       │   ├── postgres.py
│       │   └── schema.py
│       ├── normalization/       # Output normalization
│       │   ├── normalize.py
│       │   └── redact.py
│       ├── observability/       # Tracing & metrics
│       │   ├── tracer.py
│       │   └── metrics.py
│       └── cli/                 # CLI commands
│           ├── serve.py         # Daemon mode
│           └── query.py         # Query interface
├── tests/
│   ├── test_logger.py           # Unit tests
│   ├── test_adapters.py         # Adapter tests
│   └── fixtures/                # Test data
├── examples/
│   ├── basic_logging.py         # Simple usage
│   └── multi_agent_analysis.py  # Advanced analysis
├── docs/
│   ├── ADAPTER_DEVELOPMENT.md   # How to add agent support
│   └── QUERYING.md              # Query language reference
└── LICENSE                       # Apache 2.0
```

## Supported Agents

| Agent Platform | Adapter | Status | Notes |
|---|---|---|---|
| Claude (claude.ai) | `claude.py` | ✓ Stable | Web scraping via Selenium |
| Claude Code | `claude_code.py` | ✓ Stable | IDE integration |
| Cursor Agent | `cursor.py` | ✓ Stable | LSP-based |
| Forge Code | `forge.py` | ✓ Stable | CLI introspection |
| Codex (OpenAI) | `codex.py` | ✓ Stable | API-based (requires key) |
| Factory Droid | `factory_droid.py` | ✓ Stable | Webhook-based |
| OpenCode | `opencode.py` | ✓ Beta | Document parsing |
| Kilo Code | `kilo.py` | ⚠ Alpha | Reverse engineering |

## Database Schema

```sql
CREATE TABLE prompts (
    id INTEGER PRIMARY KEY,
    agent VARCHAR NOT NULL,
    prompt TEXT NOT NULL,
    response TEXT,
    latency_ms FLOAT,
    tokens_used INTEGER,
    cost_cents FLOAT,
    conversation_id VARCHAR,
    user VARCHAR,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    redacted_at TIMESTAMP
);

CREATE INDEX idx_agent_created ON prompts(agent, created_at DESC);
CREATE INDEX idx_user_created ON prompts(user, created_at DESC);
CREATE FULLTEXT INDEX idx_prompt_text ON prompts(prompt);
```

## Related Phenotype Projects

- **PhenoObservability** — Parent project; main observability hub
- **Tracera** — Distributed tracing platform; consumes prompt logs
- **AgilePlus** — Work tracking; integrates agent activity logging
- **PhenoKits** — Framework components; uses prompt logger for instrumentation

## Configuration

Create `~/.phenotype-ops/prompt-logger.toml`:

```toml
[database]
type = "sqlite"
url = "sqlite:///~/.local/share/phenotype/prompts.db"

[agents]
claude.enabled = true
cursor.enabled = true
codex.enabled = true
codex.api_key = "${OPENAI_API_KEY}"

[redaction]
pii_masking = true
patterns = ["email", "ssn", "api_key"]

[observability]
tracing_enabled = true
otlp_endpoint = "http://localhost:4317"
```

## License & Governance

Licensed under Apache 2.0. See `LICENSE`. Governance in `CLAUDE.md` (parent). Functional requirements and FR-to-test mapping in `FUNCTIONAL_REQUIREMENTS.md` (if present). Adapter development guide in `docs/ADAPTER_DEVELOPMENT.md`.
