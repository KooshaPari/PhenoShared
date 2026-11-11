# Getting Started

## Installation

```bash
npm install
npm run build
```

## Usage

```typescript
import { MemoryTokenStore } from './adapters/MemoryTokenStore'
import { PlaceholderJwtVerifier } from './adapters/PlaceholderJwtVerifier'

const store = new MemoryTokenStore()
const verifier = new PlaceholderJwtVerifier()

// Store a token
await store.save({ accessToken: 'my-token', expiresAt: Date.now() + 3600_000 })

// Verify a token
const claims = await verifier.verify('my-token')
```

## Architecture

```mermaid
graph TD
    A[Application] --> B[TokenProvider Port]
    A --> C[TokenStore Port]
    A --> D[TokenVerifier Port]
    B --> E[JWT Provider Adapter]
    C --> F[MemoryTokenStore Adapter]
    C --> G[RedisTokenStore Adapter]
    D --> H[PlaceholderJwtVerifier]
    D --> I[JWKS Verifier Adapter]
```

## Layout

| Path | Role |
|------|------|
| `src/domain/` | Token types, claims, errors |
| `src/ports/` | `TokenProvider`, `TokenStore`, `TokenVerifier` |
| `src/adapters/` | `MemoryTokenStore`, `PlaceholderJwtVerifier` |

## Testing

```bash
npm test
npm run typecheck
```
