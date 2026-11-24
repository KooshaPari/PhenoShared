# API Key Authentication Pattern

## Overview

API keys provide simple, stateless authentication for machine-to-machine communication. This pattern covers secure API key implementation for the Phenotype ecosystem.

## When to Use

- Service-to-service authentication
- Third-party integrations
- Rate limiting by client
- Simple stateless auth (not for user sessions)

## Structure

```
┌─────────────────────────────────────────────┐
│           API Key Authentication            │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────┐          ┌──────────┐        │
│  │  Client  │─────────▶│   API    │        │
│  │          │ X-API-Key│ Gateway  │        │
│  │  abc123  │ Header   │          │        │
│  └──────────┘          └────┬─────┘        │
│                             │               │
│                             ▼               │
│                    ┌─────────────────┐      │
│                    │  Key Validation │      │
│                    │  - Hash match   │      │
│                    │  - Not revoked  │      │
│                    │  - Rate limit   │      │
│                    └────────┬────────┘      │
│                             │               │
│                             ▼               │
│                    ┌─────────────────┐      │
│                    │  Resolve Scope   │      │
│                    │  (permissions)   │      │
│                    └────────┬────────┘      │
│                             │               │
│                             ▼               │
│                    ┌─────────────────┐      │
│                    │  Forward to App  │      │
│                    └─────────────────┘      │
└─────────────────────────────────────────────┘
```

## Key Format

### Standard Format (Phenotype)
```
pheno_live_abc123def456ghi789
└──┬──┘ └──┬─┘ └──────┬──────┘
   │       │          └── Random (24 chars)
   │       └─────────── Environment
   └─────────────────── Prefix

Examples:
- pheno_live_...      Production
- pheno_test_...      Test/Staging
- pheno_dev_...       Development
```

## Phenotype Implementation

### Rust

```rust
use sha2::{Sha256, Digest};
use hex;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApiKey {
    pub id: String,           // Key identifier (hashed)
    pub prefix: String,       // First 8 chars (for display)
    pub hash: String,         // SHA-256 hash
    pub scope: Vec<String>,   // Permissions
    pub environment: String,    // live/test/dev
    pub created_at: DateTime<Utc>,
    pub expires_at: Option<DateTime<Utc>>,
    pub last_used: Option<DateTime<Utc>>,
    pub revoked: bool,
    pub metadata: ApiKeyMetadata,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApiKeyMetadata {
    pub name: String,
    pub owner: String,
    pub service: String,
    pub rate_limit: u32,      // requests per minute
}

pub struct ApiKeyService {
    db: ApiKeyRepository,     // phenotype-sqlite or phenotype-redis
    cache: phenotype_cache_adapter::Cache,
}

impl ApiKeyService {
    /// Generate a new API key
    pub async fn generate_key(
        &self,
        metadata: ApiKeyMetadata,
        environment: &str,
        scope: Vec<String>,
    ) -> Result<(String, ApiKey), ApiKeyError> {
        // Generate cryptographically secure random key
        let random_part: String = (0..24)
            .map(|_| rand::random::<u8>() % 62)
            .map(|i| match i {
                0..=25 => (b'a' + i) as char,
                26..=51 => (b'A' + i - 26) as char,
                _ => (b'0' + i - 52) as char,
            })
            .collect();
        
        let key = format!("pheno_{}_{}", environment, random_part);
        let prefix = key[..16].to_string();
        let hash = self.hash_key(&key);
        let id = format!("{}_{}", prefix, &hash[..8]);
        
        let api_key = ApiKey {
            id: id.clone(),
            prefix,
            hash,
            scope,
            environment: environment.to_string(),
            created_at: Utc::now(),
            expires_at: None,
            last_used: None,
            revoked: false,
            metadata,
        };
        
        // Store hash only, never the plaintext
        self.db.store(&api_key).await?;
        
        // Cache for fast validation
        self.cache_key(&api_key).await?;
        
        // Return plaintext key (shown only once)
        Ok((key, api_key))
    }
    
    /// Validate incoming API key
    pub async fn validate_key(&self, key: &str) -> Result<ApiKey, ApiKeyError> {
        // Extract components
        let parts: Vec<&str> = key.split('_').collect();
        if parts.len() != 3 || parts[0] != "pheno" {
            return Err(ApiKeyError::InvalidFormat);
        }
        
        let environment = parts[1];
        let random_part = parts[2];
        
        if random_part.len() != 24 {
            return Err(ApiKeyError::InvalidFormat);
        }
        
        // Compute hash for lookup
        let hash = self.hash_key(key);
        let prefix = format!("pheno_{}_{}", environment, &random_part[..8]);
        let id = format!("{}_{}", prefix, &hash[..8]);
        
        // Check cache first
        if let Some(cached) = self.cache.get::<ApiKey>(&id).await? {
            return self.validate_cached(cached).await;
        }
        
        // Check database
        let api_key = self.db.get(&id).await?
            .ok_or(ApiKeyError::NotFound)?;
        
        self.validate_cached(api_key).await
    }
    
    async fn validate_cached(&self, api_key: ApiKey) -> Result<ApiKey, ApiKeyError> {
        // Check revocation
        if api_key.revoked {
            return Err(ApiKeyError::Revoked);
        }
        
        // Check expiration
        if let Some(expires) = api_key.expires_at {
            if Utc::now() > expires {
                return Err(ApiKeyError::Expired);
            }
        }
        
        // Update last used
        self.db.update_last_used(&api_key.id).await?;
        
        Ok(api_key)
    }
    
    fn hash_key(&self, key: &str) -> String {
        let mut hasher = Sha256::new();
        hasher.update(key.as_bytes());
        hasher.update(b"phenotype-key-salt-v1");  // Pepper
        hex::encode(hasher.finalize())
    }
    
    /// Revoke a key
    pub async fn revoke_key(&self, id: &str) -> Result<(), ApiKeyError> {
        self.db.revoke(id).await?;
        self.cache.delete(id).await?;
        Ok(())
    }
}
```

### Python

```python
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import secrets
import hashlib
import hmac
from dataclasses import dataclass, asdict

@dataclass
class ApiKeyMetadata:
    name: str
    owner: str
    service: str
    rate_limit: int = 100  # requests per minute

@dataclass
class ApiKey:
    id: str
    prefix: str
    hash: str
    scope: List[str]
    environment: str
    created_at: datetime
    expires_at: Optional[datetime]
    last_used: Optional[datetime]
    revoked: bool
    metadata: ApiKeyMetadata

class ApiKeyService:
    def __init__(self, db, cache):
        self._db = db
        self._cache = cache
    
    def generate_key(
        self,
        metadata: ApiKeyMetadata,
        environment: str = "live",
        scope: List[str] = None,
        expires_days: Optional[int] = None
    ) -> tuple[str, ApiKey]:
        """Generate new API key. Returns (plaintext_key, api_key_record)."""
        
        # Generate secure random string
        random_part = secrets.token_urlsafe(18)[:24]
        key = f"pheno_{environment}_{random_part}"
        
        prefix = key[:16]
        key_hash = self._hash_key(key)
        key_id = f"{prefix}_{key_hash[:8]}"
        
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        api_key = ApiKey(
            id=key_id,
            prefix=prefix,
            hash=key_hash,
            scope=scope or [],
            environment=environment,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            last_used=None,
            revoked=False,
            metadata=metadata
        )
        
        # Store in database
        self._db.store(asdict(api_key))
        
        # Cache for fast lookup
        self._cache.set(key_id, api_key, ttl=3600)
        
        # Return plaintext (shown only once)
        return key, api_key
    
    def validate_key(self, key: str) -> ApiKey:
        """Validate API key from request header."""
        
        # Validate format
        parts = key.split('_')
        if len(parts) != 3 or parts[0] != 'pheno':
            raise AuthenticationError("Invalid API key format")
        
        environment, random_part = parts[1], parts[2]
        
        if len(random_part) != 24:
            raise AuthenticationError("Invalid API key length")
        
        # Compute hash
        key_hash = self._hash_key(key)
        prefix = f"pheno_{environment}_{random_part[:8]}"
        key_id = f"{prefix}_{key_hash[:8]}"
        
        # Check cache
        cached = self._cache.get(key_id)
        if cached:
            return self._validate_cached(cached)
        
        # Check database
        record = self._db.get(key_id)
        if not record:
            raise AuthenticationError("API key not found")
        
        api_key = ApiKey(**record)
        return self._validate_cached(api_key)
    
    def _hash_key(self, key: str) -> str:
        """Hash API key with pepper."""
        pepper = b"phenotype-key-salt-v1"
        return hmac.new(
            pepper,
            key.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def _validate_cached(self, api_key: ApiKey) -> ApiKey:
        """Validate cached/decoded API key."""
        
        if api_key.revoked:
            raise AuthenticationError("API key revoked")
        
        if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
            raise AuthenticationError("API key expired")
        
        # Update last used
        self._db.update_last_used(api_key.id, datetime.utcnow())
        
        return api_key
    
    def revoke_key(self, key_id: str):
        """Revoke API key."""
        self._db.revoke(key_id)
        self._cache.delete(key_id)
```

## Security Best Practices

### 1. Storage Security
```python
# ❌ NEVER store plaintext keys
class BadStorage:
    def store(self, key: str):  # WRONG
        self.db.insert({"api_key": key})

# ✅ Store only hashed keys
class GoodStorage:
    def store(self, api_key: ApiKey):  # RIGHT
        self.db.insert({
            "id": api_key.id,
            "hash": api_key.hash,  # SHA-256 + pepper
            "prefix": api_key.prefix  # For display only
        })
```

### 2. Rate Limiting
```rust
pub async fn check_rate_limit(
    &self,
    key_id: &str,
    limit: u32,
) -> Result<(), RateLimitError> {
    let window = 60; // 1 minute window
    let key = format!("rate_limit:{}", key_id);
    
    let current = self.cache.increment(&key, 1).await?;
    
    if current == 1 {
        // First request, set expiry
        self.cache.expire(&key, window).await?;
    }
    
    if current > limit {
        return Err(RateLimitError::Exceeded);
    }
    
    Ok(())
}
```

### 3. Key Rotation
```python
class KeyRotationService:
    async def rotate_key(self, old_key_id: str) -> tuple[str, ApiKey]:
        """Rotate API key while preserving permissions."""
        
        # Get old key permissions
        old_key = self.service.get_key(old_key_id)
        
        # Generate new key with same scope
        new_key, new_record = self.service.generate_key(
            metadata=old_key.metadata,
            environment=old_key.environment,
            scope=old_key.scope,
            expires_days=365
        )
        
        # Schedule old key expiration (grace period)
        grace_period = timedelta(days=7)
        self.service.schedule_revocation(
            old_key_id, 
            datetime.utcnow() + grace_period
        )
        
        return new_key, new_record
```

## Testing

```rust
#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_key_lifecycle() {
        let service = test_service();
        let metadata = test_metadata();
        
        // Generate key
        let (key, record) = service.generate_key(
            metadata,
            "test",
            vec!["read".to_string()]
        ).await.unwrap();
        
        assert!(key.starts_with("pheno_test_"));
        assert_eq!(record.scope, vec!["read"]);
        
        // Validate key
        let validated = service.validate_key(&key).await.unwrap();
        assert_eq!(validated.id, record.id);
        
        // Revoke and validate rejection
        service.revoke_key(&record.id).await.unwrap();
        let result = service.validate_key(&key).await;
        assert!(matches!(result, Err(ApiKeyError::Revoked)));
    }
    
    #[tokio::test]
    async fn test_rate_limiting() {
        let service = test_service();
        let metadata = ApiKeyMetadata {
            name: "test".to_string(),
            owner: "test".to_string(),
            service: "test".to_string(),
            rate_limit: 5,
        };
        
        let (key, _) = service.generate_key(metadata, "test", vec![])
            .await.unwrap();
        
        // 5 requests should succeed
        for _ in 0..5 {
            assert!(service.validate_key(&key).await.is_ok());
        }
        
        // 6th request should fail
        let result = service.validate_key(&key).await;
        assert!(matches!(result, Err(ApiKeyError::RateLimited)));
    }
    
    #[test]
    fn test_invalid_format_rejected() {
        let service = test_service();
        
        let invalid_keys = vec![
            "invalid_key",
            "pheno_live_short",
            "pheno_invalid_abcdefghijklmnopqrstuv",
            "pheno_test_!@#$%^&*()_+-=[]{}|\\",
        ];
        
        for key in invalid_keys {
            let result = service.validate_key(key);
            assert!(
                matches!(result, Err(ApiKeyError::InvalidFormat)),
                "Key '{}' should be rejected", key
            );
        }
    }
}
```

## Comparison with Other Patterns

| Pattern | Use Case | Stateless | Revocation | Complexity |
|---------|----------|-----------|------------|------------|
| API Key | Service-to-service | Yes | Via cache | Low |
| JWT | User sessions, distributed | Yes | Via jti + cache | Medium |
| OAuth-PKCE | Mobile/SPA auth | No | Via revocation endpoint | High |
| mTLS | Internal services | Yes | Via cert revocation | High |

## Phenotype Integration

```rust
// Middleware layer
pub async fn api_key_middleware<B>(
    service: State<ApiKeyService>,
    headers: HeaderMap,
    request: Request<B>,
    next: Next<B>,
) -> Result<Response, ApiKeyError> {
    let key = headers
        .get("X-API-Key")
        .ok_or(ApiKeyError::MissingHeader)?
        .to_str()
        .map_err(|_| ApiKeyError::InvalidHeader)?;
    
    let api_key = service.validate_key(key).await?;
    
    // Check rate limit
    service.check_rate_limit(&api_key.id, api_key.metadata.rate_limit).await?;
    
    // Add to request extensions
    request.extensions_mut().insert(api_key);
    
    Ok(next.run(request).await)
}
```