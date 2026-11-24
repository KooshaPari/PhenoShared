# phenotype-vessel Specification

## Architecture
```
┌─────────────────────────────────────────────────────┐
│            phenotype-vessel (Rust)                    │
├─────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────┐ │
│  │         Container orchestration             │ │
│  └───────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

## Components

| Component | Responsibility |
|-----------|----------------|
| runtime | Container runtime |
| scheduler | Task scheduling |
| network | Networking |

## Data Models

```rust
struct VesselSpec {
    image: String,
    env_vars: HashMap<String, String>,
    resources: Resources,
}
```

## Performance Targets

| Metric | Target |
|--------|--------|
| Start container | <5s |
| Scale | <30s |