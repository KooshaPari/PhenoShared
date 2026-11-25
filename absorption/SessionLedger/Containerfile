FROM rust:1.87-slim AS builder
WORKDIR /app
COPY . .
RUN cargo build --release --locked
FROM debian:bookworm-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends libssl3 ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/sl-daemon /usr/local/bin/sl-daemon
ENV SL_DATA_DIR=/data SL_PORT=8080
EXPOSE 8080
VOLUME ["/data"]
ENTRYPOINT ["sl-daemon", "serve"]
CMD ["--watch", "/data/sessions", "--out", "/data/out"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8080/healthz | grep -q '^ok$' || exit 1
