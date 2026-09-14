# Dockerfile — NanoVMS production image
# Multi-stage: build → minimal runtime
# Usage:
#   docker build -t nanovms .
#   docker run -p 8443:8443 -e NVMS_TOKEN=$(openssl rand -hex 32) nanovms

# ── Stage 1: build ──────────────────────────────────────────
FROM golang:1.26-bookworm AS builder

WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download 2>/dev/null || true

COPY . .
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /nvms ./cmd/nvms

# ── Stage 2: runtime ────────────────────────────────────────
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r nvms && useradd -r -g nvms -s /sbin/nologin nvms

COPY --from=builder /nvms /usr/local/bin/nvms

USER nvms
EXPOSE 8443

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD nvms health || exit 1

ENTRYPOINT ["nvms"]
CMD ["serve"]
