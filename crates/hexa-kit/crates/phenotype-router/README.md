# `phenotype-router` — H11 absorption

OpenAI-compatible HTTP router plane. `ComboVariant` for the six
auto-combo variants; HTTP delegate to `cliproxy++` (Go plane) for
`/v1/chat/completions`.

## Origin

Absorbed from `<REDACTED>/phenotype-gateway::spikes/rust/router` (H10 spike).
The gateway repo is now archived and re-created as a deprecated mirror;
the live router lives here.

## Scope

- `ComboVariant` enum (5 variants — `Coding` / `Fast` / `Cheap` / `Offline` / `Smart`)
- `Router` trait + `ComboRouter` resolver
- `delegate::build_delegate_request` — composes the cliproxy upstream URL
- `delegate::scoring_profile` — maps cliproxy profile tag → scoring profile

## H12 follow-up

Live HTTP server (axum) listening on `/v1/chat/completions` + `/v1/models`,
forwarding to cliproxy.

## Tests

```
cargo test -p phenotype-router
```
