# =============================================================================
# Build Stage
# =============================================================================
FROM --platform=$BUILDPLATFORM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Install dependencies
RUN pip install uv && uv sync --frozen

# =============================================================================
# Runtime Stage
# =============================================================================
FROM --platform=$BUILDPLATFORM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /build/.venv /app/.venv

# Copy source code
COPY --from=builder /build/src /app/src
COPY --from=builder /build/pyproject.toml /app/

# Set environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Set entrypoint
ENTRYPOINT ["python", "-m", "hexapy"]
CMD ["--help"]
