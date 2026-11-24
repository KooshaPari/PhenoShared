# Installing BytePort

BytePort is a self-hosted deployment platform for GitHub repositories. Install via Docker Compose (recommended), from source, or as a Tauri desktop app.

## Quick Start (Docker Compose) — Recommended

```bash
git clone https://github.com/KooshaPari/BytePort.git
cd BytePort
cp .env.example .env        # optional — defaults work for local dev
docker compose up --build
```

This builds two containers:

| Service | Port | What it runs |
|---|---|---|
| `backend` | **8081** | Go API (Gin + SQLite) |
| `web` | **3000** | SvelteKit frontend |

Open <http://localhost:3000> and follow the on-screen signup flow.

```bash
# Stop
docker compose down

# View logs
docker compose logs -f backend
```

## Install from Source

### Prerequisites

- Go 1.26+
- Rust 1.75+ (for Tauri shell and CLI)
- Node.js 20+ (for SvelteKit frontend)
- SQLite (bundled via CGO)

### Backend

```bash
cd backend/byteport
go build -o byteport-server
./byteport-server
# API available at http://localhost:8081
```

### Frontend

```bash
cd frontend/web
npm install
npm run dev
# Web UI available at http://localhost:5173
```

### Tauri Desktop App

```bash
# Install system dependencies: https://v2.tauri.app/start/prerequisites/
cargo install tauri-cli
cargo tauri dev        # Development mode
cargo tauri build      # Build installer
```

### CLI

```bash
cd backend/byteport
go build -o byteport-cli
# Or install directly
go install ./backend/byteport
byteport-cli --help
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8081` | Backend API port |
| `NVMS_URL` | `http://localhost:8443` | NanoVMS server URL |
| `NVMS_TOKEN` | (none) | Bearer token for NanoVMS API |
| `JWT_SECRET` | (generated) | JWT signing secret |
| `DATABASE_URL` | `file:./byteport.db` | SQLite database path |

> **The port is not arbitrary.** The desktop app connects to a fixed
> `http://localhost:8081` (`API_PORT` in `frontend/web/src/lib/api.ts`), and
> the Tauri shell probes the same port for `/health`. Serving the API on any
> other port leaves the app unable to reach its backend. Override with `PORT`
> or `BYTEPORT_API_PORT` only if you also change that constant.

## Integration with NanoVMS

BytePort deploys sandboxes to NanoVMS. To connect:

```bash
# Start NanoVMS first
export NVMS_TOKEN=$(openssl rand -hex 32)
docker run -d --name nanovms -p 8443:8443 -e NVMS_TOKEN=$NVMS_TOKEN ghcr.io/kooshapari/nanovms:latest

# Start BytePort with NanoVMS connection
export NVMS_URL=http://localhost:8443
export NVMS_TOKEN=$NVMS_TOKEN
docker compose up -d
```

## Troubleshooting

**Backend won't start (port in use):**
```bash
lsof -i :8081
# Kill existing or change port
PORT=9090 ./byteport-server
```

**Frontend can't reach backend:**
```bash
# Check backend is running
curl http://localhost:8081/health
```

**Tauri build fails:**
```bash
# Check prerequisites
rustup update
cargo install tauri-cli
```
