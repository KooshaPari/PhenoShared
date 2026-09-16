# JWT Authentication Pattern

## Overview

JSON Web Tokens (JWT) provide stateless authentication for distributed systems. This pattern covers secure JWT implementation in the Phenotype ecosystem.

## When to Use

- Stateless authentication needed
- Distributed microservices
- Cross-domain single sign-on (SSO)
- Mobile/API-first applications

## Structure

```
┌─────────────────────────────────────────────┐
│           JWT Authentication Flow           │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────┐      ┌──────────┐             │
│  │  Client │─────▶│   Auth   │             │
│  │         │      │ Service  │             │
│  └─────────┘      └────┬─────┘             │
│       │                │                   │
│       │                ▼                   │
│       │         ┌──────────┐               │
│       │         │  Sign    │               │
│       │         │  JWT     │               │
│       │         └────┬─────┘               │
│       │                │                   │
│       │◀───────────────┘ (Token)         │
│       │                                    │
│       │         ┌──────────┐              │
│       └────────▶│  API     │              │
│    (JWT Header) │  Service │              │
│                 └────┬─────┘              │
│                      │                     │
│                      ▼                     │
│              ┌──────────────┐              │
│              │ Verify JWT   │              │
│              │ (Signature + │              │
│              │  Claims)     │              │
│              └──────────────┘              │
└─────────────────────────────────────────────┘
```

## Phenotype Implementation

### Rust (phenotype-auth-tokens)

```rust
use serde::{Deserialize, Serialize};
use jsonwebtoken::{encode, decode, Header, Algorithm, Validation, EncodingKey, DecodingKey};

#[derive(Debug, Serialize, Deserialize)]
struct Claims {
    sub: String,        // Subject (user ID)
    iss: String,        // Issuer
    aud: String,        // Audience
    exp: usize,         // Expiration time
    iat: usize,         // Issued at
    jti: String,        // JWT ID (for revocation)
    scope: Vec<String>, // Permissions
}

pub struct JwtConfig {
    secret: String,
    issuer: String,
    audience: String,
    expiry_hours: i64,
}

pub fn generate_token(
    user_id: &str,
    scope: Vec<String>,
    config: &JwtConfig,
) -> Result<String, JwtError> {
    let now = chrono::Utc::now().timestamp() as usize;
    let exp = now + (config.expiry_hours * 3600) as usize;
    
    let claims = Claims {
        sub: user_id.to_string(),
        iss: config.issuer.clone(),
        aud: config.audience.clone(),
        exp,
        iat: now,
        jti: generate_jti(),
        scope,
    };
    
    encode(
        &Header::new(Algorithm::HS256),
        &claims,
        &EncodingKey::from_secret(config.secret.as_bytes()),
    )
    .map_err(|e| JwtError::Encoding(e.to_string()))
}

pub fn validate_token(token: &str, config: &JwtConfig) -> Result<Claims, JwtError> {
    let mut validation = Validation::new(Algorithm::HS256);
    validation.set_issuer(&[config.issuer.clone()]);
    validation.set_audience(&[config.audience.clone()]);
    validation.validate_exp = true;
    
    let token_data = decode::<Claims>(
        token,
        &DecodingKey::from_secret(config.secret.as_bytes()),
        &validation,
    )
    .map_err(|e| JwtError::InvalidToken(e.to_string()))?;
    
    // Check revocation (with phenotype-cache-adapter)
    if is_token_revoked(&token_data.claims.jti)? {
        return Err(JwtError::Revoked);
    }
    
    Ok(token_data.claims)
}
```

### Python (phenoSDK)

```python
from datetime import datetime, timedelta
from typing import List, Optional
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import uuid

class JwtConfig:
    def __init__(
        self,
        secret: str,
        issuer: str,
        audience: str,
        expiry_hours: int = 24,
        algorithm: str = "HS256"
    ):
        self.secret = secret
        self.issuer = issuer
        self.audience = audience
        self.expiry_hours = expiry_hours
        self.algorithm = algorithm

class JwtService:
    def __init__(self, config: JwtConfig):
        self._config = config
    
    def generate_token(
        self,
        user_id: str,
        scope: List[str],
        additional_claims: Optional[dict] = None
    ) -> str:
        now = datetime.utcnow()
        exp = now + timedelta(hours=self._config.expiry_hours)
        
        claims = {
            "sub": user_id,
            "iss": self._config.issuer,
            "aud": self._config.audience,
            "exp": exp,
            "iat": now,
            "jti": str(uuid.uuid4()),
            "scope": scope,
        }
        
        if additional_claims:
            claims.update(additional_claims)
        
        return jwt.encode(
            claims,
            self._config.secret,
            algorithm=self._config.algorithm
        )
    
    def validate_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(
                token,
                self._config.secret,
                algorithms=[self._config.algorithm],
                issuer=self._config.issuer,
                audience=self._config.audience
            )
            
            # Check revocation via phenotype-cache-adapter
            if self._is_revoked(payload["jti"]):
                raise jwt.InvalidTokenError("Token revoked")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {e}")
```

## Security Best Practices

### 1. Token Structure
- Use RS256 (RSA) for production, HS256 (HMAC) for internal
- Keep payload minimal (don't include sensitive data)
- Use short expiration (15 min - 24 hours)
- Include JWT ID (jti) for revocation support

### 2. Storage
```rust
// ❌ Never store in localStorage (XSS vulnerable)
localStorage.setItem("token", token);

// ✅ Store in httpOnly cookie (backend only)
Set-Cookie: auth_token=<jwt>; HttpOnly; Secure; SameSite=Strict; Max-Age=3600

// ✅ Or use memory-only for SPAs
// Store in app state, refresh on page reload
```

### 3. Revocation Strategy
```rust
// phenotype-cache-adapter integration
pub async fn revoke_token(jti: &str, expiry: usize) -> Result<(), CacheError> {
    let ttl = expiry - chrono::Utc::now().timestamp() as usize;
    phenotype_cache_adapter::set_with_ttl(
        format!("jwt_revoke:{}", jti),
        "revoked",
        ttl,
    ).await
}

pub async fn is_revoked(jti: &str) -> Result<bool, CacheError> {
    phenotype_cache_adapter::exists(format!("jwt_revoke:{}", jti)).await
}
```

### 4. Refresh Token Pattern
```
┌──────────────────────────────────────────────┐
│           Refresh Token Flow                 │
├──────────────────────────────────────────────┤
│                                              │
│  1. Client has:                              │
│     - Access JWT (short-lived, 15 min)       │
│     - Refresh Token (long-lived, 7 days)     │
│                                              │
│  2. When access JWT expires:                 │
│     POST /refresh { refresh_token }          │
│                                              │
│  3. Server validates refresh token:          │
│     - Check database (not JWT!)              │
│     - Verify not revoked                     │
│     - Check rotation hash                    │
│                                              │
│  4. Response:                                  │
│     - New access JWT                         │
│     - New refresh token (token rotation)     │
│                                              │
└──────────────────────────────────────────────┘
```

## Testing Strategies

### Unit Tests
```rust
#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_token_lifecycle() {
        let config = test_config();
        let token = generate_token("user123", vec!["read".to_string()], &config)
            .expect("Token generation failed");
        
        let claims = validate_token(&token, &config)
            .expect("Token validation failed");
        
        assert_eq!(claims.sub, "user123");
        assert!(claims.scope.contains(&"read".to_string()));
    }
    
    #[test]
    fn test_expired_token_rejected() {
        let mut config = test_config();
        config.expiry_hours = -1; // Already expired
        
        let token = generate_token("user123", vec![], &config).unwrap();
        let result = validate_token(&token, &config);
        
        assert!(matches!(result, Err(JwtError::Expired)));
    }
    
    #[test]
    fn test_revoked_token_rejected() {
        let config = test_config();
        let token = generate_token("user123", vec![], &config).unwrap();
        let jti = decode_token(&token).unwrap().claims.jti;
        
        // Revoke token
        revoke_token(&jti, usize::MAX).await.unwrap();
        
        // Should be rejected
        let result = validate_token(&token, &config);
        assert!(matches!(result, Err(JwtError::Revoked)));
    }
}
```

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Long-lived tokens | Use 15 min access + refresh tokens |
| Storing secrets in JWT | Never put passwords/API keys in payload |
| No revocation | Implement jti + cache for blacklist |
| Algorithm confusion | Explicitly specify allowed algorithms |
| Weak secrets | Use 256+ bit secrets or RSA 2048+ |

## Integration with Phenotype

```rust
// Middleware for Axum/FastAPI
pub async fn jwt_auth_middleware<B>(
    config: State<JwtConfig>,
    headers: HeaderMap,
    request: Request<B>,
    next: Next<B>,
) -> Result<Response, AuthError> {
    let token = extract_bearer_token(&headers)?;
    let claims = validate_token(&token, &config)?;
    
    // Add claims to request extensions
    let mut request = request;
    request.extensions_mut().insert(claims);
    
    Ok(next.run(request).await)
}
```

## References
- [RFC 7519 - JWT Standard](https://tools.ietf.org/html/rfc7519)
- [OWASP JWT Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_Cheat_Sheet_for_Java.html)