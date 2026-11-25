# Configuration

Settly is a configuration management framework.  This document describes how to
configure the **framework itself** (its own behaviour) — not how to use Settly
to manage *your* application's configuration (see the API docs for that).

## Framework Settings (`SettlySettings`)

The `SettlySettings` struct controls runtime behaviour of Settly's built-in
components.  Every field has a sensible default, so you only need to override
what you need.

| Field                   | Type    | Default | Description                              |
|-------------------------|---------|---------|------------------------------------------|
| `idempotency_ttl_secs`  | `u64`   | 86_400  | Idempotency cache TTL (seconds, 24h).    |
| `max_retries`           | `u32`   | 3       | Max retry attempts per submission.       |

### Example — Programmatic

```rust
use settly::domain::settings::SettlySettings;

let settings = SettlySettings {
    idempotency_ttl_secs: 3600,   // 1 hour
    ..Default::default()
};
```

### Example — Config File (TOML)

```toml
[settly]
idempotency_ttl_secs = 3600
max_retries = 5
```

See `config/example.toml`, `config/example.yaml`, and `config/example.json` for
full examples in all three supported formats.

## How It Works

1. The framework defines `SettlySettings` with `serde::Deserialize` + `Default`.
2. Users embed a `[settly]` section in their own config files.
3. When loading config via `FileSource`, the `[settly]` key is parsed into
   runtime settings by the component that needs them (e.g.
   `InMemoryIdempotencyStore` calls `SettlySettings::default()`).

## Adding a New Setting

1. Add the field to `SettlySettings` in `src/domain/settings.rs`.
2. Provide a `#[serde(default = "...")]` helper function and a `DEFAULT_*`
   constant.
3. Use the constant in the component that needs the value.
4. Update `config/example.toml` and this table.
