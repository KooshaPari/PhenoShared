<!-- ARCHIVED 2026-07-05:START -->
> **ARCHIVED 2026-07-05.** This repository is archived. The canonical
> successor is [AuthKit](https://github.com/KooshaPari/AuthKit).
>
> New FRs land in AuthKit:
> - FR-AUTHV-018 (PKCE state->session binding) -- SHIPPED
> - AUT-SOTA-001 (OIDC Discovery 1.0 + JWKS) -- SHIPPED
> - AUT-SOTA-003 (WebAuthn L3) -- SHIPPED
> - AUT-SOTA-004 (TOTP RFC 6238) -- SHIPPED
> - AUT-SOTA-002/005/006/007 (key rotation, KMS, DPoP, rate-limit) -- PLANNED
>
> **GAP-008 PKCE middleware** and **gap-010 middleware adapter docs** that
> landed in this repo are pending a port PR to AuthKit (D1 resolution path A).
> See `docs/sessions/2026-07-05-polyrepo-portfolio-strategy/05-decisions/02-D1-blocker-authvault-authkit-state.md`.
>
> For migration: see
> [AuthKit docs/migrations/from-authvault.md](https://github.com/KooshaPari/AuthKit/blob/main/docs/migrations/from-authvault.md).
<!-- ARCHIVED 2026-07-05:END -->

<!-- AI-DD-META:START -->
<!-- This repository is planned, maintained, and managed by AI Agents only. -->
<!-- Slop issues are expected and intentionally present as part of an HITL-less -->
<!-- /minimized AI-DD metaproject of learning, refining, and building brute-force -->
<!-- training for both agents and the human operator. -->
![Downloads](https://img.shields.io/github/downloads/KooshaPari/Authvault/total?style=flat-square&label=downloads&color=blue)
![GitHub release](https://img.shields.io/github/v/release/KooshaPari/Authvault?style=flat-square&label=release)
![License](https://img.shields.io/github/license/KooshaPari/Authvault?style=flat-square)
![AI-Slop](https://img.shields.io/badge/AI--DD-Slop%20Expected-orange?style=flat-square)
![AI-Only-Maintained](https://img.shields.io/badge/Planned%20%26%20Maintained%20by-AI%20Agents%20Only-red?style=flat-square)
![HITL-less](https://img.shields.io/badge/HITL--less%20AI--DD-metaproject-yellow?style=flat-square)

> ⚠️ **AI-Agent-Only Repository**
>
> This repo is **planned, maintained, and managed exclusively by AI Agents**.
> Slop issues, rough edges, and AI artifacts are **expected and intentionally
> present** as part of an **HITL-less / minimized AI-DD** metaproject focused
> on learning, refining, and brute-force training both the agents and the
> human operator. Bug reports and contributions are still welcome, but please
> expect AI-generated code, comments, and documentation throughout.
<!-- AI-DD-META:END -->
> **Work state:** ACTIVE · **Progress:** `███████░░░ 70%`
> Hexagonal auth framework (OAuth2/JWT/RBAC); security+session+token audits complete · updated 2026-06-02

# Authvault

**Authentication and authorization framework with OAuth2, JWT, and RBAC/ABAC support.**

## Consolidated Auth Family

Authvault is now the umbrella repo for the Phenotype auth surface. Imported subtrees live at:

- `authkit/` - Rust staging SDK and security crates
- `typescript/phenotype-auth-ts/` - TypeScript auth library and docs

A hexagonal architecture-based authentication framework supporting:

- **Multiple Auth Methods**: JWT, OAuth2, API Keys, Session tokens
- **Authorization Models**: RBAC, ABAC, PBAC with policy engine
- **User Management**: Registration, login, password reset
- **Session Management**: Token refresh, revocation, rotation
- **Multi-tenancy**: Tenant isolation, domain-based routing
- **Audit Logging**: Complete auth event logging

## Architecture

```
authvault/
├── src/
│   ├── domain/          # Core domain logic (pure)
│   │   ├── identity.rs # User entities
│   │   ├── auth.rs     # Authentication logic
│   │   ├── policy.rs   # Authorization policies
│   │   ├── session.rs  # Session management
│   │   ├── ports.rs    # Interface definitions
│   │   └── errors.rs   # Domain errors
│   ├── application/     # Application services
│   ├── adapters/        # Infrastructure adapters
│   └── infrastructure/  # Cross-cutting concerns
```

## Features

- [x] JWT tokens with RS256/HS256
- [x] OAuth2 client credentials flow
- [x] Password hashing (argon2, bcrypt)
- [x] RBAC with role hierarchy
- [x] ABAC with attribute-based policies
- [x] Session management with refresh tokens
- [x] Rate limiting
- [x] Audit logging
- [ ] Multi-factor authentication
- [ ] Passwordless authentication
- [ ] Delegation and federation

## Installation

```toml
[dependencies]
authvault = "0.1"
```

## Quick Start

```rust
use authvault::{Authenticator, Claims};

let auth = Authenticator::new(secret_key)?;
let token = auth.generate_token(user_id, roles)?;
let claims = auth.verify_token(&token)?;
```

## Development

```bash
cargo build
cargo test
cargo clippy -- -D warnings
cargo fmt
```

## Runtime Configuration

The `serve` example binds to `127.0.0.1:8080` by default. Set `BIND_ADDR` to listen
on a different address:

```bash
BIND_ADDR=0.0.0.0:8080 cargo run --example serve
```

## License

MIT OR Apache-2.0
