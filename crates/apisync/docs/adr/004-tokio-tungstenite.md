# ADR-004: Choice of tokio-tungstenite for WebSocket

## Status

Accepted

## Context

Apisync’s WebSocket adapter must provide both server and client capabilities, integrate with the tokio runtime, and support standard WebSocket messaging (text, binary, ping/pong, close). The chosen library should expose a stream/sink interface compatible with futures and should not bring in a conflicting runtime or heavy HTTP framework.

Alternatives considered:
- **warp**: Bundles WebSocket support, but it is a full web framework with its own routing and filter system. That would couple the WebSocket transport to warp’s abstractions.
- **actix-web-actors**: Tightly coupled to actix-web and actix-rt, which conflicts with our tokio-first runtime choice.
- **fastwebsockets**: Lightweight and fast, but newer and with a smaller ecosystem. It lacks the maturity and battle-testing we want for a foundational toolkit.
- **websocket crate (rust-websocket)**: Older, blocking-first, and effectively unmaintained. Not suitable for async-first services.

## Decision

Use **tokio-tungstenite 0.24** as the WebSocket implementation.

- It is a thin, async-native wrapper around the tungstenite core, which is widely used and well-tested.
- Exposes `Stream` and `Sink` interfaces from `futures`, allowing composable backpressure and integration with tokio channels.
- Server-side `accept_async` and client-side `connect_async` both work on standard tokio TCP streams, keeping the adapter free of framework-specific types.
- The `Message` enum maps cleanly to our domain message types, so the adapter can translate without leaking tungstenite details outward.

## Consequences

- **Positive**: Proven in production across the Rust ecosystem. Low risk of bugs or unexpected behavior.
- **Positive**: The stream/sink model aligns naturally with async Rust idioms and enables integration with `tokio::select!` and channel-based architectures.
- **Positive**: Because we wrap tungstenite in the adapter layer, we can replace it with a lighter alternative (e.g., fastwebsockets) in the future without changing public APIs.
- **Negative**: `tokio-tungstenite` is a stream-level library, not a room/broadcast abstraction. We must implement higher-level patterns (pub/sub, broadcast) ourselves in `application/` or `infrastructure/`.
- **Negative**: TLS is not built-in; `tokio-native-tls` or `tokio-rustls` must be composed manually for wss:// support.
