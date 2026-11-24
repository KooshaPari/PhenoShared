# Deploying BytePort

This guide covers deploying BytePort to production environments.

## Docker Compose (Recommended)

```bash
git clone https://github.com/KooshaPari/BytePort.git
cd BytePort

# Create environment file
cat > .env << EOF
NVMS_URL=http://nanovms:8443
NVMS_TOKEN=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 32)
PORT=8081
EOF

# Start all services
docker compose up -d

# Verify
curl http://localhost:8081/health
curl -H "Authorization: Bearer <token>" http://localhost:8081/metrics
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | No | `8081` | Backend API listen port |
| `NVMS_URL` | Yes | `http://localhost:8443` | NanoVMS server URL |
| `NVMS_TOKEN` | Yes | — | Bearer token for NanoVMS API |
| `JWT_SECRET` | Yes | (generated) | JWT signing secret |
| `DATABASE_URL` | No | `file:./byteport.db` | SQLite database path |

## Health Check

```bash
curl http://localhost:8081/health
# {"status":"healthy","service":"byteport","uptime":"1h23m45s"}
```

## Metrics (Prometheus)

```bash
curl http://localhost:8081/metrics
# byteport_uptime_seconds 5025.00
# byteport_requests_total 1234
# byteport_errors_total 3
# byteport_deploys_total 42
# byteport_sandboxes_active 5
# byteport_memory_alloc_bytes 12345678
# byteport_memory_sys_bytes 23456789
# byteport_goroutines 15
```

## Production Checklist

- [ ] Set `NVMS_TOKEN` to a secure random value
- [ ] Set `JWT_SECRET` to a secure random value
- [ ] Configure `NVMS_URL` to point to running NanoVMS instance
- [ ] Enable TLS termination (reverse proxy: nginx, Caddy, or cloud LB)
- [ ] Set up log aggregation
- [ ] Configure backup for SQLite database
- [ ] Set up monitoring with `/metrics` endpoint
- [ ] Configure rate limiting at load balancer level

## Reverse Proxy (nginx)

```nginx
server {
    listen 443 ssl http2;
    server_name deploy.example.com;

    ssl_certificate /etc/ssl/certs/byteport.pem;
    ssl_certificate_key /etc/ssl/private/byteport.key;

    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8081/health;
        access_log off;
    }

    location /metrics {
        proxy_pass http://127.0.0.1:8081/metrics;
        # Restrict to internal monitoring
        allow 10.0.0.0/8;
        deny all;
    }
}
```

## Troubleshooting

**Server won't start:**
```bash
# Check port availability
lsof -i :8081

# Check database
ls -la byteport.db

# Check logs
docker compose logs backend
```

**Can't connect to NanoVMS:**
```bash
# Verify NanoVMS is running
curl -H "Authorization: Bearer $NVMS_TOKEN" http://localhost:8443/v1/sandboxes

# Check NVMS_URL configuration
echo $NVMS_URL
```
