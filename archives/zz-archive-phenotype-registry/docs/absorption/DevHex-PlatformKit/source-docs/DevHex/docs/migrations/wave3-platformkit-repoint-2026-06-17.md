# Wave 3 — PlatformKit consumer alignment

**Date:** 2026-06-17  
**Chokepoint:** DevHex blocks PlatformKit archive delete eligibility

## Canonical library

| Surface | Owner | Module |
|---------|-------|--------|
| devenv abstraction library | [phenotype-go-sdk](https://github.com/KooshaPari/phenotype-go-sdk) | `github.com/KooshaPari/devenv-abstraction` (`packages/devhex/`) |
| DevHex CLI / adapters | This repo | `github.com/kooshapari/DevHex` |

DevHex ships product-specific adapters (docker, nix, native) on top of the hexagonal port pattern. The **canonical reusable library** for new consumers is `phenotype-go-sdk/packages/devhex`, not archived PlatformKit paths.

## Consumer guidance

```go
import (
    "github.com/KooshaPari/devenv-abstraction/pkg/domain"
    "github.com/KooshaPari/devenv-abstraction/pkg/adapters/docker"
)
```

Do not add dependencies on `KooshaPari/PlatformKit` — archived.

## Follow-up

- Optional: extract shared `pkg/domain` from DevHex into go-sdk if API parity is required.
- Repoint any external manifests still pinning PlatformKit module paths.
