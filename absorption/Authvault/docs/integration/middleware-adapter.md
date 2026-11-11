---
title: Middleware Adapter Integration
---

# Middleware Adapter Integration

`AuthvaultMiddlewareAdapter` is the Axum/Tower layer that turns an incoming `Authorization: Bearer ...`
header into request-scoped `Claims`.

The adapter:

- extracts the bearer token from `Authorization`
- validates the token with `Authenticator::validate_bearer_token`
- inserts `Claims` into the request extensions on success
- returns a `401` JSON response when validation fails

## Tracera Wiring

Use the layer directly on the router or service stack and extract `Claims` from request extensions.

```rust
use axum::{extract::Extension, routing::get, Router};
use authvault::{AuthvaultMiddlewareAdapter, Authenticator, Claims, UserId};
use std::sync::Arc;

async fn whoami(Extension(claims): Extension<Claims>) -> String {
    claims.user_id().to_string()
}

let authenticator = Arc::new(Authenticator::new("tracera-secret"));
let auth_layer = AuthvaultMiddlewareAdapter::from_shared(Arc::clone(&authenticator));

let app = Router::new()
    .route("/whoami", get(whoami))
    .layer(auth_layer);
```

For a protected route, the handler can trust that `Claims` is present because the middleware returns
`401` before the request reaches the handler.

## AgilePlus Wiring

AgilePlus can use the same adapter in front of internal API routes without duplicating validation code.

```rust
use axum::{extract::Extension, response::IntoResponse, routing::post, Router};
use authvault::{AuthvaultMiddlewareAdapter, Authenticator, Claims};
use std::sync::Arc;

async fn create_task(Extension(claims): Extension<Claims>) -> impl IntoResponse {
    format!("task created for {}", claims.sub)
}

let authenticator = Authenticator::new("agileplus-secret");
let app = Router::new()
    .route("/tasks", post(create_task))
    .layer(AuthvaultMiddlewareAdapter::new(authenticator));
```

If the consumer prefers to build layered stacks, the adapter also works with `tower::ServiceBuilder`.

```rust
use authvault::{AuthvaultMiddlewareAdapter, Authenticator};
use tower::ServiceBuilder;

let auth_layer = AuthvaultMiddlewareAdapter::new(Authenticator::new("shared-secret"));
let stack = ServiceBuilder::new().layer(auth_layer);
```

## Error Shape

Invalid or missing credentials return a `401` JSON body such as:

```json
{
  "error": "unauthorized",
  "message": "invalid bearer token"
}
```

That response shape is intentionally minimal so consumer repos can map it into their own error
handling or observability pipeline.
