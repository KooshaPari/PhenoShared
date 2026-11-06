# PhenoProc Python - AI/Process Infrastructure

Python packages for AI agent infrastructure and process management.

## Structure

```
PhenoProc/
├── crates/              # Rust crates (existing)
├── python/              # Python packages (new)
│   ├── pheno-clink/     # AI agent integrations
│   └── pheno-llm/       # LLM routing and management
└── Cargo.toml           # Rust workspace
```

## Python Packages

| Package | Description | Extracted From |
|---------|-------------|----------------|
| pheno-clink | Codex, Claude, Gemini agents | phenoSDK |
| pheno-llm | LLM routing, ensemble strategies | phenoSDK |

## Installation

```bash
cd PhenoProc/python
pip install -e pheno-clink -e pheno-llm
```

## Note

Python packages are kept separate from Rust crates but share the same workspace philosophy - independent, minimal dependencies, focused purpose.

*Extraction date: 2026-04-04*
