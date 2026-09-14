# Installing NanoVMS

NanoVMS is a multi-tier sandbox orchestration engine. You can install it from source, pre-built binaries, or Docker.

## Quick Start (Docker)

```bash
# Generate a token
export NVMS_TOKEN=$(openssl rand -hex 32)

# Run NanoVMS
docker run -d --name nanovms -p 8443:8443 -e NVMS_TOKEN=$NVMS_TOKEN ghcr.io/kooshapari/nanovms:latest

# Verify
curl -H "Authorization: Bearer $NVMS_TOKEN" http://localhost:8443/v1/sandboxes
```

## Docker Compose

```bash
git clone https://github.com/KooshaPari/nanovms.git
cd nanovms

# Create .env
echo "NVMS_TOKEN=$(openssl rand -hex 32)" > .env

# Start
docker compose up -d

# Check health
curl -H "Authorization: Bearer $NVMS_TOKEN" http://localhost:8443/v1/sandboxes
```

## Install from Source

### Prerequisites

- Go 1.26+
- Linux (primary), macOS (limited adapters), Windows (limited)

```bash
# Clone
git clone https://github.com/Kooshapari/nanovms.git
cd nanovms

# Build
go build -o nvms ./cmd/nvms

# Install (optional)
sudo mv nvms /usr/local/bin/

# Verify
nvms probe
```

## Install via `go install`

```bash
go install github.com/kooshapari/nanovms/cmd/nvms@latest
```

## API Server

```bash
# Start the API server
nvms serve --port 8443 --token $NVMS_TOKEN

# Deploy a sandbox
curl -X POST http://localhost:8443/v1/deploy \
  -H "Authorization: Bearer $NVMS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"my-sandbox","image":"alpine:latest","sandbox_type":"native"}'

# List sandboxes
curl -H "Authorization: Bearer $NVMS_TOKEN" http://localhost:8443/v1/sandboxes

# Stop a sandbox
curl -X POST "http://localhost:8443/v1/stop?id=<sandbox-id>" \
  -H "Authorization: Bearer $NVMS_TOKEN"
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `NVMS_TOKEN` | (required) | Bearer token for API authentication |
| `NVMS_LOG_LEVEL` | `info` | Log level: debug, info, warn, error |
| `NVMS_PORT` | `8443` | API server listen port |

## CLI Commands

| Command | Description |
|---------|-------------|
| `nvms serve` | Start the API server |
| `nvms probe` | Check available isolation tiers |
| `nvms run` | Run a sandbox from CLI |
| `nvms list` | List running sandboxes |
| `nvms stop` | Stop a sandbox by name |

## Troubleshooting

**Port already in use:**
```bash
lsof -i :8443
# Kill existing process or change port
nvms serve --port 9443
```

**Permission denied on adapters:**
```bash
# Some adapters (Firecracker, LXC) require root
sudo nvms serve --port 8443
```
