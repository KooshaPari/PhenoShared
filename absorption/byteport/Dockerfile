FROM golang:1.27-bookworm AS backend
WORKDIR /app
COPY backend/ ./backend/
WORKDIR /app/backend/byteport
RUN go build -o /byteport-server

FROM rust:1.98-slim AS desktop
WORKDIR /app
COPY . .
RUN cargo build --release --locked -p byteport-cli

FROM debian:bookworm-slim

# Run unprivileged: the server resolves its SQLite database relative to the
# working directory, which this user owns.
RUN useradd --system --uid 10001 --create-home byteport \
    && mkdir -p /data \
    && chown byteport:byteport /data
WORKDIR /data
USER byteport

COPY --from=backend /byteport-server /usr/local/bin/
COPY --from=desktop /app/target/release/byteport-cli /usr/local/bin/
CMD ["byteport-server"]
