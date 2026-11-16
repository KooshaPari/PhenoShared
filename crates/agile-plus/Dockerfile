# AgilePlus CLI — multi-stage Docker image (audit K-Ops remediation)
#
# Produces a minimal runtime image with the `agileplus` binary.
# Prerequisite: `agileplus-cli` and its dependency crates must be listed in
# the root [workspace].members (see docs/remediation/OPS.md).
#
# Build:
# docker build -f Dockerfile -t agileplus-cli:local .
# Run:
# docker run --rm agileplus-cli:local agileplus --version

# syntax=docker/dockerfile:1

FROM rust:slim-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    protobuf-compiler \
    build-essential \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Layer cache: manifests first
COPY Cargo.toml Cargo.lock* rust-toolchain.toml ./
COPY rust/ rust/
COPY proto/ proto/
COPY crates/ crates/
COPY libs/ libs/

# Build CLI only (faster than full workspace when members are wired)
RUN cargo build --release -p agileplus-cli --locked \
    && cp /build/target/release/agileplus /tmp/agileplus

# ── Runtime ─────────────────────────────────────────────────────────────────
FROM debian:bookworm-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libssl3 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /tmp/agileplus /usr/local/bin/agileplus

# Default data directory (mount a volume at /data for persistence)
ENV AGILEPLUS_DB=/data/agileplus.db
VOLUME ["/data"]
WORKDIR /data

ENTRYPOINT ["agileplus"]
CMD ["--help"]
