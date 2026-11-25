# AgilePlus Self-Hosted Deployment

Docker Compose stack for self-hosting AgilePlus CLI with data persistence and optional Cloudflare Tunnel support.

## Important: AgilePlus is a CLI Tool

**AgilePlus is not a web service.** It is a command-line tool for project management. This stack:

- Provides a **containerized CLI environment** with a persistent SQLite database
- **Does not expose an HTTP API** by default
- Includes **Caddy** as a placeholder reverse proxy (serves a status page only)
- Supports **data volume mounting** for local CLI access
- Optionally integrates with **Cloudflare Tunnel** for external connectivity

If you need HTTP endpoints, build a separate web service wrapper (REST API or GraphQL layer) that mounts the AgilePlus database volume.

## Architecture

```
┌─────────────────────────────────────┐
│ Your CLI / Local Container          │
│ (mounts agileplus-data volume)      │
│ Runs: agileplus --db /data/...      │
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│ AgilePlus CLI Container             │
│ - SQLite database at /data/          │
│ - No HTTP server                     │
└─────────────────────────────────────┘
        │
        ▼
  [agileplus.db]
```

## Quick Start

### 1. Build the AgilePlus Image

```bash
cd /path/to/agileplus
docker build -t agileplus:latest .
```

### 2. Create `.env.selfhost`

```bash
cat > .env.selfhost << 'EOF'
HOSTNAME=agileplus.pheno.studio
CF_TUNNEL_TOKEN=
EOF
```

Add to `.gitignore`:
```
.env.selfhost
.env.*.local
```

### 3. Start the Stack

```bash
docker compose -f deploy/selfhost/docker-compose.selfhost.yml \
  --env-file .env.selfhost up -d
```

### 4. Access the Database

```bash
# Run CLI commands against the container
docker compose -f deploy/selfhost/docker-compose.selfhost.yml \
  exec agileplus-cli agileplus list-projects

# Or mount the volume locally
docker run -it --rm -v agileplus-data:/data \
  agileplus:latest agileplus --db /data/agileplus.db list-projects
```

## Using the CLI

```bash
# List all projects
docker compose exec agileplus-cli agileplus list-projects

# List epics
docker compose exec agileplus-cli agileplus list-epics --project-id 1

# List stories
docker compose exec agileplus-cli agileplus list-stories --epic-id 2

# View full help
docker compose exec agileplus-cli agileplus --help
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `HOSTNAME` | Domain for Caddy status page (no API) |
| `CF_TUNNEL_TOKEN` | Cloudflare Tunnel token (optional) |

## Managing the Stack

```bash
# Stop
docker compose -f deploy/selfhost/docker-compose.selfhost.yml down

# View logs
docker compose -f deploy/selfhost/docker-compose.selfhost.yml logs -f

# Backup database
docker run --rm -v agileplus-data:/data -v $(pwd):/backup \
  ubuntu tar czf /backup/agileplus-backup.tar.gz -C /data .
```

## Building an HTTP Wrapper (Optional)

Create a lightweight REST API service that mounts the `agileplus-data` volume and calls AgilePlus CLI commands or directly queries SQLite.

## Troubleshooting

```bash
# Check container status
docker compose ps

# View detailed logs
docker compose logs agileplus-cli

# Test CLI directly
docker compose exec agileplus-cli agileplus --help

# Verify database exists
docker compose exec agileplus-cli ls -la /data/
```

## Security

- Never commit `.env.selfhost` to version control
- Use strong `GITHUB_PAT` if integrating with GitHub
- Restrict database file permissions (600 or 640)
- Use Tailscale for private access instead of exposing on public internet

## Updates

```bash
# Update AgilePlus image
docker pull agileplus:latest
docker compose -f deploy/selfhost/docker-compose.selfhost.yml up -d agileplus-cli

# Update Caddy
docker compose -f deploy/selfhost/docker-compose.selfhost.yml pull caddy
docker compose -f deploy/selfhost/docker-compose.selfhost.yml up -d caddy
```

## Production Checklist

- [ ] Database backups automated and tested
- [ ] `.env.selfhost` is in `.gitignore`
- [ ] Caddy status page accessible
- [ ] HTTP wrapper service built (if needed)
- [ ] Cloudflare Tunnel configured (if external access needed)
- [ ] Regular Docker image updates scheduled

---

**Version:** 1.0  
**Status:** CLI-only (no HTTP server)
