# Pheno Inference Stack — Ops Runbook

> **Scope**: `pheno-compute-layer` managed inference deployment on the 3090 Ti desktop.
> **Last updated**: 2026-05-24

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  Client Layer (Mac)                                             │
│                                                                  │
│  pheno_client.py       pheno-client.sh      Claude Desktop      │
│  PhenoMultiClient     role_code/reason     + pheno-gpu MCP     │
│  port 8080/8000-8003  HTTP POST            FastMCP tools        │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTP /v1/chat/completions
                             │ SSH desk (Tailscale)
┌────────────────────────────▼─────────────────────────────────────┐
│  pheno-compute-layer /providers/                                  │
│                                                                  │
│  omni_route.py       models.conf        config.env                │
│  ROLE_MAP           DENSE_MODELS      DESKTOP_URL=100.96.135.160 │
│  ROLE_PROVIDER_MAP  MOE_MODELS        OMNI_URL (alias)           │
│  MODELS dict        QUANT_OPTIONS     VLLM_BASE_URL              │
│  route()            ROLE_MAPPING      OLLAMA_BASE_URL            │
│                                                                  │
│  bin/pheno-llm      mcp/pheno_gpu_mcp.py   bin/pheno            │
│  start/stop         gpu_status            gpu / run / shell      │
│  status/logs        run_command           wsl-ssh / SCP         │
│  restart            check_connection      gpu-full / gpu-proc    │
└────────────────────────────┬─────────────────────────────────────┘
                             │ Tailscale SSH → Windows → WSL
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  Desktop (kooshapari-desk / 3090 Ti)                            │
│                                                                  │
│  WSL Ubuntu-22.04                                               │
│   ├── Tailscale IP: 100.96.135.160                             │
│   ├── WSL IP: 172.28.183.80                                    │
│   ├── ~/llm-models/         (model GGUF files)                  │
│   ├── ~/llm-server/         (llama-server + logs)               │
│   └── ~/llama.cpp/llama-b9010/llama-server                      │
│                                                                  │
│  Inference backends: llama-server (llama.cpp) / vLLM / SGLang   │
│  OpenAI-compatible API: http://100.96.135.160:8080/v1           │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Repository Map

| Repo / Path | Purpose |
|---|---|
| `pheno-compute-layer/` | **Primary managed inference layer** — routing, service control, MCP, config |
| `pheno-compute-layer/providers/omni_route.py` | OmniRoute router — `MODELS` dict, `ROLE_MAP`, `ROLE_PROVIDER_MAP`, `route()` |
| `pheno-compute-layer/providers/models.conf` | Bash model registry — `DENSE_MODELS`, `MOE_MODELS`, `ROLE_MAPPING`, `QUANT_OPTIONS` |
| `pheno-compute-layer/providers/config.env` | Environment config — `DESKTOP_URL`, `VLLM_BASE_URL`, `OLLAMA_BASE_URL`, `MODELS_DIR` |
| `pheno-compute-layer/bin/pheno-llm` | llama-server lifecycle — `start`/`stop`/`restart`/`logs`/`status`/`test` |
| `pheno-compute-layer/bin/pheno` | Global CLI — GPU status, remote exec, WSL tooling |
| `pheno-compute-layer/mcp/pheno_gpu_mcp.py` | FastMCP server — GPU/system/execution tools for Claude Desktop |
| `pheno-compute-layer/config/mcp.json` | MCP server config — `uvx mcp-pheno-gpu` invocation |
| `pheno-compute-layer/scripts/download-model.sh` | Model downloader — `uv` + `huggingface_hub`, core model install via `install-core` |
| `pheno-compute-layer/scripts/setup.sh` | One-time setup — SSH config, `pheno` symlink, PATH |
| `pheno-compute-layer/scripts/setup-tailscale-ssh.sh` | Tailscale SSH setup for WSL (run on Windows) |
| `pheno-compute-layer/scripts/check-server.sh` | Endpoint health checker — checks /models + remote process via SSH |
| `pheno-llm/` (standalone) | Parallel standalone — own `bin/pheno-llm` + `config/models.conf` (simple `KEY=REPO:FILE` format) |
| `cursor-reset-tools/scripts/pheno_client.py` | Python SDK — `PhenoClient` + `PhenoMultiClient` (ports 8000–8003) |
| `cursor-reset-tools/scripts/pheno-client.sh` | Bash client — role helpers (`role_code`, `role_reason`, etc.) |
| `cursor-reset-tools/scripts/start-multi-vllm.sh` | Multi-vLLM launcher — 4 servers on ports 8000–8003 |
| `cursor-reset-tools/scripts/deploy-desktop.sh` | Desktop deployment script — installs vLLM, downloads models, starts servers |
| `repos/phenoShared/…/pheno_llm/` | Shared contract library — `LLMRouter` skeleton + dataclass models |

---

## 3. Model Registry

### 3a. Python registry (`providers/omni_route.py`)

The `MODELS` dict is the authoritative registry. Each entry:

```python
{
    "repo": "org/repo-name-GGUF",          # HuggingFace repo
    "default_quant": "IQ4_NL",              # Default quantization
    "role": "code" | "reason",              # Routing role
    "size_gb": 4.8,                         # GGUF file size
    "context": 128000,                       # Max context length
    "type": "dense" | "moe",                # Architecture type
    "description": "...",                   # Human description
    "quants_available": ["IQ4_NL", ...],    # Supported quantizations (optional)
    # Optional boolean flags:
    "reap": True,       # REAP variant
    "thinking": True,    # Extended thinking variant
    "distilled": True,   # Reasoning distilled
    "vision": True,     # Vision-language model
    "fine_tuned": True, # Fine-tuned variant
}
```

### 3b. Bash registry (`providers/models.conf`)

Format: `"key"="repo:quant:size"`:

```bash
declare -A DENSE_MODELS=(
    ["granite-4.1-8b"]="unsloth/granite-4.1-8b-GGUF:Q4_K_M:5GB"
    ["qwen3.5-0.5b"]="unsloth/Qwen3.5-0.5B-GGUF:Q4_K_M:512MB"
)
declare -A MOE_MODELS=(
    ["qwen3.6-35b-a3b-iq2"]="unsloth/Qwen3.6-35B-A3B-GGUF:UD-IQ2_M:12GB"
)
declare -A ROLE_MAPPING=(
    ["code"]="granite-4.1-8b"
    ["reason"]="qwen3.6-35b-a3b"
)
declare -A QUANT_OPTIONS=(
    ["granite-4.1-8b"]="IQ4_NL:IQ4_XS:Q4_K_M:Q3_K_M:Q5_K_M:Q6_K"
)
```

### 3c. Simple registry (`pheno-llm/config/models.conf`)

Format: `key=repo:filename.gguf`:

```bash
qwen3.6-moeq4=unsloth/Qwen3.6-35B-A3B-GGUF:Qwen3.6-35B-A3B-Q4_K_M.gguf
granite4.1-8b-q4=unsloth/granite-4.1-8b-GGUF:granite-4.1-8b-Q4_K_M.gguf
```

---

## 4. Role Routing

| Role | Model Key | Description | Size |
|------|-----------|-------------|------|
| `code` | `granite_4_1_8b` | IBM Granite — best coding | 4.8 GB |
| `reason` | `qwen3_6_35b_a3b_iq2` | MoE ultra-low memory | 12 GB |
| `think` | `qwen3_6_35b_distill` | Claude 4.7 distilled reasoning | 22 GB |
| `reap` | `qwen3_6_28b_reap` | REAP specialized (28B/3B) | 18 GB |
| `default` | `granite_4_1_8b` | Falls back to Granite | 4.8 GB |

`ROLE_PROVIDER_MAP` enables role-level endpoint/backend routing (for future multi-host scenarios):

```python
ROLE_PROVIDER_MAP = {
    "code":     {"endpoint": "http://100.96.135.160:8080/v1", "backend": "vllm"},
    "reason":   {"endpoint": "http://100.96.135.160:8080/v1", "backend": "vllm"},
    "think":    {"endpoint": "http://100.96.135.160:8080/v1", "backend": "vllm"},
    "reap":     {"endpoint": "http://100.96.135.160:8080/v1", "backend": "vllm"},
}
```

---

## 5. Environment Configuration

### Source these before using the stack:

```bash
# Primary config source
source providers/config.env

# Or set individually
export OMNI_URL="${DESKTOP_URL}"           # http://100.96.135.160:8080/v1
export OMNI_BACKEND="vllm"
export OMNI_MODELS="/home/kooshapari/llm-models"
export DESKTOP_HOST="desk"
export COMPUTE_IP="100.96.135.160"
```

`config.env` also defines:
```bash
VLLM_BASE_URL="${DESKTOP_URL}"   # vLLM colocated endpoint
OLLAMA_BASE_URL="${DESKTOP_URL}"  # Ollama endpoint (future)
SERVICE_MODEL="granite_4_1_8b"
SERVICE_CONTEXT="8192"
LLAMA_SERVER="/home/kooshapari/llama.cpp/llama-b9010/llama-server"
```

---

## 6. Deployment Procedure

### 6a. Initial Setup (one-time)

```bash
# 1. Clone / ensure compute-layer is accessible
cd /Users/kooshapari/CodeProjects/Phenotype/pheno-compute-layer

# 2. Run the setup script (Mac side)
./scripts/setup.sh

# 3. Verify SSH to desktop
pheno status

# 4. On Windows desktop: enable Tailscale SSH in WSL
# Run once on Windows:
# .\scripts\setup-tailscale-ssh.sh
```

### 6b. Download Models

```bash
# Show available models
./scripts/download-model.sh list

# Install core recommended models (within 1 hour)
./scripts/download-model.sh install-core

# Install individual models
./scripts/download-model.sh install granite_4_1_8b
./scripts/download-model.sh install qwen3_6_35b_a3b_iq2
./scripts/download-model.sh install qwen3_6_28b_reap

# Verify downloads
./scripts/download-model.sh verify granite_4_1_8b
```

Core recommended models:
| Model | Size | Purpose |
|-------|------|---------|
| `granite_4_1_8b` | 4.8 GB | Coding (IQ4_NL) ⭐⭐⭐ |
| `qwen3_6_35b_a3b_iq2` | 12 GB | Reasoning MoE (UD-IQ2_M) ⭐⭐ |
| `qwen3_6_28b_reap` | 18 GB | REAP specialized ⭐⭐ |
| `qwen3_6_35b_distill` | 22 GB | Claude distilled reasoning ⭐⭐ |

### 6c. Start / Stop Inference Service

```bash
# Start the managed inference server (current runtime path)
./scripts/start-llm-server.sh

# Start a specific model
./scripts/start-llm-server.sh --model qwen3_6_35b_a3b_iq2

# Dry run to inspect the exact remote command
./scripts/start-llm-server.sh --dry-run --backend vllm --model granite_4_1_8b

# Check status
bin/pheno-llm status

# Test inference
bin/pheno-llm test

# View logs (live tail)
bin/pheno-llm logs

# Restart
bin/pheno-llm restart

# Stop
bin/pheno-llm stop
```

### 6d. Verify End-to-End

```bash
# Quick connectivity check
pheno status
pheno gpu

# Check endpoint health (current runtime checker)
./scripts/check-server.sh

# List available models on server
curl -s http://100.96.135.160:8080/v1/models | python3 -m json.tool

# Test chat completion
curl -s -X POST http://100.96.135.160:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "granite_4_1_8b",
    "messages": [{"role": "user", "content": "Write a Python function to reverse a string."}],
    "max_tokens": 256,
    "temperature": 0.2
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'])"

# Run role-based test via client
../cursor-reset-tools/scripts/pheno-client.sh role_code "Write a sorting algorithm in Python"
```

### 6e. MCP Server Setup (Claude Desktop)

```bash
# 1. Install FastMCP
pip install fastmcp
# or
uv pip install fastmcp

# 2. Run standalone to verify
python mcp/pheno_gpu_mcp.py

# 3. Add to Claude Desktop MCP settings (~/.config/claude-desktop/mcp_settings.json):
# {
#   "mcpServers": {
#     "pheno-gpu": {
#       "command": "uvx",
#       "args": ["mcp-pheno-gpu"],
#       "env": {
#         "COMPUTE_HOST": "desk",
#         "COMPUTE_IP": "100.96.135.160"
#       }
#     }
#   }
# }

# Available MCP tools: gpu_status, gpu_full, gpu_processes, system_info,
#                      check_connection, run_command, run_wsl,
#                      tailscale_status, python_versions, check_package
```

---

## 7. Scaling & Operations

### 7a. Multi-Instance Scaling (parallel role workloads)

For concurrent requests to different model sizes:

```bash
# Start four vLLM servers on dedicated ports (from cursor-reset-tools)
../cursor-reset-tools/scripts/start-multi-vllm.sh start

# Port mapping:
# 8000: Qwen 0.5B  (fast/format roles)
# 8001: Qwen 1.5B  (retrieve role)
# 8002: Qwen 3B    (plan/code/debug roles)
# 8003: Qwen 7B   (reason role)

# Check status
../cursor-reset-tools/scripts/start-multi-vllm.sh status

# View logs
../cursor-reset-tools/scripts/start-multi-vllm.sh logs

# Stop all
../cursor-reset-tools/scripts/start-multi-vllm.sh stop
```

### 7b. Python SDK Usage

```python
from pheno_client import PhenoClient, PhenoMultiClient

# Simple chat
client = PhenoClient(host="kooshapari-desk", port=8000)
print(client.chat("What is 2+2?"))

# Role-based multi-model
multi = PhenoMultiClient(host="kooshapari-desk")
print(multi.code("function to parse JSON"))     # → port 8002
print(multi.reason("solve this problem"))       # → port 8003
print(multi.plan("implement authentication"))   # → port 8002
```

### 7c. GPU Monitoring

```bash
# Quick GPU check
pheno gpu

# Full nvidia-smi output
pheno gpu-full

# GPU compute processes
pheno gpu-proc

# Remote command
pheno run nvidia-smi -L
```

### 7d. Failure Recovery

| Problem | Diagnosis | Fix |
|---------|-----------|-----|
| `pheno status` fails | Tailscale/DNS issue | `tailscale up --ssh` on desktop WSL; check SSH key |
| `check-server.sh` fails | Endpoint not reachable | Start server: `./scripts/start-llm-server.sh` |
| Server not responding | llama-server crashed | `bin/pheno-llm restart` or re-run `./scripts/start-llm-server.sh` |
| Model missing | Wrong `MODELS_DIR` or filename mismatch | `bin/pheno-llm list`; re-run `download-model.sh install <model>` |
| GPU OOM | Wrong quantization loaded | Switch to lower quant: `qwen3_6_35b_a3b_iq2` (12GB) instead of `qwen3_6_35b_a3b` (21GB) |
| MCP tools unavailable | FastMCP not running | `python mcp/pheno_gpu_mcp.py` or restart Claude Desktop |

### 7e. Backend Swap (llama.cpp → vLLM → SGLang)

The runtime helper supports backend selection directly. Use the current startup script and inspect with `--dry-run` before launching:

```bash
# Stop current service first if needed
bin/pheno-llm stop

# Start llama.cpp backend
./scripts/start-llm-server.sh --backend llama.cpp --model granite_4_1_8b

# Start vLLM backend
./scripts/start-llm-server.sh --backend vllm --model granite_4_1_8b

# Start SGLang backend
./scripts/start-llm-server.sh --backend sglang --model granite_4_1_8b

# Preview the exact remote command without executing it
./scripts/start-llm-server.sh --backend vllm --model granite_4_1_8b --dry-run

# Verify
curl -s http://100.96.135.160:8080/v1/models
```

---

## 8. Key File Paths

| What | Where |
|------|-------|
| CLI binaries | `pheno-compute-layer/bin/` |
| Router + config | `pheno-compute-layer/providers/` |
| MCP server | `pheno-compute-layer/mcp/` |
| Health checker | `pheno-compute-layer/scripts/check-server.sh` |
| Model downloads | `~/llm-models/` (WSL) |
| Server logs | `~/llm-server/granite.log` (WSL) |
| vLLM logs | `~/vllm-logs/` (WSL) |
| Download scripts | `pheno-compute-layer/scripts/` |
| Python SDK | `cursor-reset-tools/scripts/pheno_client.py` |

---

## 9. `bin/pheno` command reference

| Command | Description |
|---------|-------------|
| `pheno status` / `pheno s` | Check SSH connection + GPU status + LLM endpoint URL |
| `pheno gpu` / `pheno g` | Quick GPU status (nvidia-smi CSV) |
| `pheno gpu-full` / `pheno gf` | Full nvidia-smi output |
| `pheno gpu-proc` / `pheno gp` | GPU compute processes |
| `pheno llm` | Run `check-server.sh` to verify endpoint health |
| `pheno ts` / `pheno tailscale` | Tailscale status |
| `pheno wsl` / `pheno w` | WSL status via Windows |
| `pheno wsl-ssh` / `pheno ws` | Direct SSH to WSL (port 2222) |
| `pheno wsl-gpu` / `pheno wg` | GPU info via WSL SSH |
| `pheno run <cmd>` | Run command on desktop |
| `pheno shell` / `pheno sh` | Interactive shell |
| `pheno scp-to <src> [dest]` | Copy files to desktop |
| `pheno scp-from <src> [dest]` | Copy files from desktop |

### Most-used startup commands

```bash
# Current runtime launcher
./scripts/start-llm-server.sh --backend vllm --model granite_4_1_8b

# Fast health check
./scripts/check-server.sh

# Legacy service manager actions still available for status/logs/test/stop
bin/pheno-llm status
bin/pheno-llm logs
bin/pheno-llm test
bin/pheno-llm stop
```

---

## 10. Operations Quick Reference

### One-liner full health check

```bash
# From Mac — single command to verify everything is up
pheno status && echo "---" && pheno gpu && echo "---" && ./scripts/check-server.sh
```

### Most-used startup commands

```bash
# Current runtime launcher (preferred)
./scripts/start-llm-server.sh --backend vllm --model granite_4_1_8b

# Fast health check
./scripts/check-server.sh

# Legacy service manager actions still available for status/logs/test/stop
bin/pheno-llm status
bin/pheno-llm logs
bin/pheno-llm test
bin/pheno-llm stop
```

### First-time setup (copy-paste block)

```bash
# 1. Enter the compute layer repo
cd /Users/kooshapari/CodeProjects/Phenotype/pheno-compute-layer

# 2. Run the installer (symlinks pheno → ~/bin, configures SSH)
./scripts/setup.sh

# 3. Verify SSH and GPU are reachable
pheno status

# 4. Download core models (takes ~20–60 min)
./scripts/download-model.sh install-core

# 5. Start the inference server
bin/pheno-llm start

# 6. Wait for model to load, then verify end-to-end
sleep 15 && bin/pheno-llm test
```

### Daily start-up (copy-paste block)

```bash
cd /Users/kooshapari/CodeProjects/Phenotype/pheno-compute-layer

# Verify connectivity
pheno status

# Start server (if not already running)
bin/pheno-llm start

# Confirm endpoint is responding
./scripts/check-server.sh
```

### Role-based inference from terminal

```bash
# Route a code task → Granite 4.1 8B
python3 providers/omni_route.py --role code
# Expected output: granite_4_1_8b → http://100.96.135.160:8080/v1

# Route a reasoning task → Qwen3.6 MoE IQ2
python3 providers/omni_route.py --role reason
# Expected output: qwen3_6_35b_a3b_iq2 → http://100.96.135.160:8080/v1

# Show all role mappings with endpoints
python3 providers/omni_route.py --roles
```

### Interactive inference via curl

```bash
# Simple completion
curl -s -X POST http://100.96.135.160:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "granite_4_1_8b",
    "messages": [{"role": "user", "content": "Write a Python function to reverse a string."}],
    "max_tokens": 256,
    "temperature": 0.2
  }'

# List models served
curl -s http://100.96.135.160:8080/v1/models | python3 -m json.tool
```

### Server lifecycle

```bash
bin/pheno-llm start [granite_4_1_8b]   # Start llama-server on desktop
bin/pheno-llm status                     # Check running state
bin/pheno-llm logs                       # Tail granite.log live
bin/pheno-llm restart                    # Stop + start
bin/pheno-llm stop                       # Stop server
```

### GPU monitoring

```bash
pheno gpu        # Quick: name, VRAM used/total, temp, util, power
pheno gpu-full  # Full nvidia-smi table
pheno gpu-proc  # Running compute processes only
```

### Model management

```bash
./scripts/download-model.sh list                   # Show all available models
./scripts/download-model.sh install-core          # Download recommended set
./scripts/download-model.sh install granite_4_1_8b  # Download specific model
./scripts/download-model.sh verify granite_4_1_8b   # Confirm GGUF on disk
```

### Multi-vLLM (parallel role workloads, cursor-reset-tools)

```bash
../cursor-reset-tools/scripts/start-multi-vllm.sh start   # 4 servers on 8000–8003
../cursor-reset-tools/scripts/start-multi-vllm.sh status  # Check all ports
../cursor-reset-tools/scripts/start-multi-vllm.sh stop   # Stop all
```

### Python SDK usage

```python
from pheno_client import PhenoClient, PhenoMultiClient

client = PhenoClient(host="kooshapari-desk", port=8000)
print(client.chat("What is 2+2?"))

multi = PhenoMultiClient(host="kooshapari-desk")
print(multi.code("function to parse JSON"))      # → port 8002
print(multi.reason("solve this problem"))        # → port 8003
print(multi.plan("implement authentication"))   # → port 8002
```

### Failure diagnosis and recovery

```bash
# Tailscale / SSH unreachable
pheno status
# Fix: ssh desk "wsl -e sudo tailscale up --ssh"

# Endpoint not responding (server down)
bin/pheno-llm status
# Fix: bin/pheno-llm start

# Model missing on desktop
bin/pheno-llm list
# Fix: ./scripts/download-model.sh install <model_key>

# GPU OOM — switch to lower quant
bin/pheno-llm stop
bin/pheno-llm start qwen3_6_35b_a3b_iq2   # 12GB instead of 21GB

# MCP tools gone — restart FastMCP
python mcp/pheno_gpu_mcp.py
```

### Backend swap (vLLM ↔ llama.cpp ↔ SGLang)

```bash
# Stop current
bin/pheno-llm stop

# Switch to llama.cpp server
ssh desk "wsl -d Ubuntu-22.04 -e bash -c 'cd ~/llm-server && \
  nohup ~/llama.cpp/llama-b9010/llama-server \
    -m ~/llm-models/granite_4_1_8b/granite-4.1-8b-IQ4_NL.gguf \
    --host 0.0.0.0 -p 8080 -c 8192 > granite.log 2>&1 &'"

# Switch to vLLM
ssh desk "wsl -d Ubuntu-22.04 -e bash -c 'cd ~/llm-server && \
  nohup python -m vllm.entrypoints.openai.api_server \
    --model ~/llm-models/granite_4_1_8b/granite-4.1-8b-IQ4_NL.gguf \
    --port 8080 --gpu-memory-utilization 0.9 > vllm.log 2>&1 &'"

# Verify
curl -s http://100.96.135.160:8080/v1/models
```

