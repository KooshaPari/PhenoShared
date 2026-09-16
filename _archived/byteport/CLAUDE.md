# BytePort — CLAUDE.md

## Project Summary

BytePort is an IaC deployment + portfolio UX generation platform. Developers define their app and AWS infrastructure in a single NVMS manifest; BytePort deploys to AWS and generates portfolio site components showcasing the deployed projects. Optionally uses an LLM (OpenAI or LLaMA) for enhanced template text.

## Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Backend | Go | Deployment engine, AWS SDK, LLM integration |
| Frontend | Web (see frontend/) | Management UI |
| IaC Format | NVMS manifest | Custom .nvms format |
| Cloud | AWS | EC2, ECS, Lambda |
| LLM | OpenAI / LLaMA | Template text generation |

## Structure

```
backend/
  byteport/      # Core deployment engine
  bytebridge/    # Bridge/integration layer
frontend/        # Management UI
start            # Local dev startup script
odin.nvms        # Example NVMS manifest
```

## Key Commands

```bash
./start          # Start local dev stack
go build ./...   # Build all Go packages
go test ./...    # Run tests
```

## Development Rules

- All CLI errors MUST print to stderr and exit non-zero
- AWS credentials read from env vars or ~/.aws/credentials -- never hardcoded
- New CLI commands go in backend/byteport/cmd/
- LLM integration is pluggable via LLMBackend interface
- Manifest parsing is strictly validated -- fail loudly on schema errors

## Quality Gates

- go build ./... -- 0 errors required
- go vet ./... -- 0 warnings required
- go test ./... -- all pass required
