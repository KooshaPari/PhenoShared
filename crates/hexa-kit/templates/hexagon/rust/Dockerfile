# =============================================================================
# Build Stage
# =============================================================================
FROM --platform=$BUILDPLATFORM docker.io/library/rust:1.77-bookworm AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy manifests
COPY Cargo.toml Cargo.lock ./

# Create dummy source for dependency caching
RUN mkdir -p src && echo "fn main() {}" > src/main.rs

# Build dependencies only
RUN cargo build --release && rm -rf src

# Copy source code
COPY src/ ./src/
COPY */src/ ./src/

# Build arguments
ARG TARGETOS
ARG TARGETARCH

# Build the workspace
RUN touch src/main.rs && \
    cargo build --release --target ${TARGETOS}-${TARGETARCH} --workspace

# =============================================================================
# Runtime Stage
# =============================================================================
FROM --platform=$BUILDPLATFORM docker.io/library/debian:bookworm-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -s /bin/sh -D appuser

WORKDIR /app

# Copy binaries from builder
COPY --from=builder /build/target/${TARGETOS}-${TARGETARCH}/release/clikit /app/clikit
COPY --from=builder /build/target/${TARGETOS}-${TARGETARCH}/release/agentkit /app/agentkit
COPY --from=builder /build/target/${TARGETOS}-${TARGETARCH}/release/authkit /app/authkit
COPY --from=builder /build/target/${TARGETOS}-${TARGETARCH}/release/configkit /app/configkit
COPY --from=builder /build/target/${TARGETOS}-${TARGETARCH}/release/cachekit /app/cachekit

# Change ownership
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Set entrypoint
ENTRYPOINT ["/app/clikit"]
CMD ["--help"]
