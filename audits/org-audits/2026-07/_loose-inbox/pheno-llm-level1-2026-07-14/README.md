# pheno-llm

LLM Inference Service for Pheno stack.

## Quick Start

```bash
# Link to ~/bin
ln -s ~/CodeProjects/Phenotype/pheno-llm/bin/pheno-llm ~/bin/pheno-llm

# Start default model (Qwen3.6 MoE Q4)
pheno-llm start

# Test
pheno-llm test "Hello!"

# List models
pheno-llm list
```

## Available Models

| Key | Model | Size | Type | Best For |
|-----|-------|------|------|----------|
| `qwen3.6-moeq4` | Qwen3.6-35B-A3B | ~19GB | MoE (3B active) | General purpose |
| `qwen3.6-reapq4` | Qwen3.6-28B-REAP | ~16GB | MoE + REAP | Optimized routing |
| `granite4.1-8b-q4` | Granite 4.1 8B | ~5GB | Dense | Fast, IBM optimized |
| `granite4.1-30b-q4` | Granite 4.1 30B | ~18GB | Dense | High quality |
| `granite3.1-8b-q4` | Granite 3.1 8B | ~5GB | Dense | Stable, proven |
| `qwen3.5-1.5b-q4` | Qwen3.5 1.5B | ~1GB | Dense | Very fast |

## Commands

```bash
pheno-llm start [model] [port]  # Start server
pheno-llm stop [port]           # Stop server
pheno-llm status                # Check status
pheno-llm gpu                   # GPU info
pheno-llm list                  # List models
pheno-llm download <model>      # Download model
pheno-llm test [prompt]         # Test chat
pheno-llm logs                  # View logs
```

## API Endpoints

Once running on `http://100.96.135.160:8080`:

```bash
# Chat completion
curl -X POST http://100.96.135.160:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello!"}]}'

# List models
curl http://100.96.135.160:8080/v1/models
```

## Architecture

```
pheno-llm/
├── bin/pheno-llm       # CLI tool
├── config/models.conf  # Model registry
├── scripts/
│   └── start-server.sh # WSL startup script
└── models/             # Downloaded models (on desktop)
```

## Connection

- **Desktop**: 100.96.135.160 (via Tailscale)
- **WSL2**: Ubuntu-22.04 with CUDA
- **GPU**: RTX 3090 Ti 24GB

## Notes

- Models stored in `~/llm-models/` on WSL
- llama.cpp server with GPU offloading
- MoE models use tensor offloading for experts
