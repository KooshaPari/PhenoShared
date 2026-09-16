# ADR-007: Security Architecture

**Document ID:** BYTEPORT_ADR_007  
**Status:** Accepted  
**Last Updated:** 2026-04-04  
**Author:** BytePort Architecture Team

---

## Context

BytePort operates in environments where security is critical:
- Financial services (transaction data)
- Healthcare (PHI/PII)
- Enterprise (confidential communications)
- IoT (device authentication)

We must provide comprehensive security including encryption, authentication, integrity verification, and replay protection.

## Decision

We implement a **layered security model** with multiple independent mechanisms:

```
+-----------------------------------------------------------------------------+
|                         BytePort Security Layers                               |
|                                                                             |
|  +-------------------------------------------------------------------------+   |
|  |  Layer 1: Transport Security                                              |   |
|  |  TLS 1.3 + mTLS for all network communication                          |   |
|  +-------------------------------------------------------------------------+   |
|                                    |                                           |
|  +-------------------------------------------------------------------------+   |
|  |  Layer 2: Message Integrity                                              |   |
|  |  CRC32C checksum + HMAC-SHA256 message authentication                   |   |
|  +-------------------------------------------------------------------------+   |
|                                    |                                           |
|  +-------------------------------------------------------------------------+   |
|  |  Layer 3: Replay Protection                                              |   |
|  |  Nonce tracking + timestamp validation with sliding window                |   |
|  +-------------------------------------------------------------------------+   |
|                                                                             |
+-----------------------------------------------------------------------------+
```

## Security Features Matrix

| Feature | Implementation | Protection Against |
|---------|----------------|-------------------|
| TLS 1.3 | rustls | Eavesdropping, MITM |
| mTLS | Certificate verification | Unauthorized clients |
| CRC32C | crc32fast | Transmission errors |
| HMAC | hmac::HMAC_SHA256 | Message tampering |
| Nonce | Sliding window | Replay attacks |
| Timestamp | Max age validation | Stale messages |

## TLS Configuration

```rust
pub struct TlsConfig {
    pub cert: rustls::Certificate,
    pub key: rustls::PrivateKey,
    pub ca_cert: Option<rustls::Certificate>,
    pub min_version: rustls::ProtocolVersion,
    cipher_suites: Vec<rustls::SupportedCipherSuite>,
}

impl TlsConfig {
    pub fn server_config(&self) -> Result<rustls::ServerConfig, TlsError> {
        let builder = rustls::ServerConfig::builder()
            .with_safe_default_cipher_suites()
            .with_safe_default_kx_groups()
            .with_protocol_versions(&[&rustls::version::TLS13])?;
        
        let mut config = if let Some(ca) = &self.ca_cert {
            // mTLS mode
            let mut store = rustls::RootCertStore::empty();
            store.add(ca)?;
            builder.client_cert_verifier(
                rustls::server::AllowAnyAuthenticatedClient::new(store)
            )
        } else {
            // Server-only TLS
            builder.with_no_client_auth()
        };
        
        config.set_single_cert(vec![self.cert.clone()], self.key.clone())?;
        config.alpn_protocols = vec![b"byteport/1".to_vec()];
        
        Ok(config)
    }
}
```

## Message Authentication

```rust
pub struct MacAuthenticator {
    key: hmac::Key,
}

impl MacAuthenticator {
    pub fn new(key: &[u8]) -> Self {
        Self {
            key: hmac::Key::new(hmac::HMAC_SHA256, key),
        }
    }
    
    pub fn compute_mac(&self, frame: &Frame) -> [u8; 32] {
        use hmac::Mac;
        let mut mac = self.key.clone();
        mac.update(&frame.header_bytes());
        mac.update(&frame.payload);
        let tag = mac.finalize();
        tag.into_bytes().try_into().unwrap()
    }
    
    pub fn verify_mac(&self, frame: &Frame, expected: &[u8; 32]) -> Result<(), MacError> {
        let computed = self.compute_mac(frame);
        if computed == *expected {
            Ok(())
        } else {
            Err(MacError::VerificationFailed)
        }
    }
}

pub struct AuthenticatedFrame {
    pub frame: Frame,
    pub mac: [u8; 32],
    pub nonce: u64,
    pub timestamp: u64,
}
```

## Replay Protection

```rust
pub struct ReplayProtector {
    window_size: usize,
    max_age: Duration,
    seen_nonces: RwLock<HashMap<u64, Instant>>,
    seen_timestamps: RwLock<BTreeSet<u64>>,
}

impl ReplayProtector {
    pub fn new(window_size: usize, max_age: Duration) -> Self {
        Self {
            window_size,
            max_age,
            seen_nonces: RwLock::new(HashMap::new()),
            seen_timestamps: RwLock::new(BTreeSet::new()),
        }
    }
    
    pub fn is_replay(&self, nonce: u64, timestamp: u64) -> bool {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();
        
        // Timestamp validation
        if now > timestamp + self.max_age.as_secs() {
            return true; // Message too old
        }
        
        // Nonce deduplication
        {
            let seen = self.seen_nonces.read().unwrap();
            if seen.contains_key(&nonce) {
                return true; // Replay detected
            }
        }
        
        // Cleanup old entries
        self.cleanup(now);
        
        // Record new nonce
        {
            let mut seen = self.seen_nonces.write().unwrap();
            seen.insert(nonce, Instant::now());
        }
        
        false
    }
    
    fn cleanup(&self, now: u64) {
        let cutoff = Instant::now() - self.max_age;
        
        // Remove old nonces
        let mut seen_nonces = self.seen_nonces.write().unwrap();
        seen_nonces.retain(|_, time| *time > cutoff);
        
        // Remove old timestamps
        let mut seen_ts = self.seen_timestamps.write().unwrap();
        seen_ts.retain(|&ts| ts > now - self.max_age.as_secs());
    }
}
```

## Security Configuration

```rust
#[derive(Debug, Clone)]
pub struct SecurityConfig {
    pub tls: Option<TlsConfig>,
    pub mac_key: Option<Vec<u8>>,
    pub replay_protection: ReplayProtectionConfig,
    pub rate_limit: Option<RateLimitConfig>,
}

#[derive(Debug, Clone)]
pub struct ReplayProtectionConfig {
    pub enabled: bool,
    pub window_size: usize,
    pub max_age: Duration,
}

#[derive(Debug, Clone)]
pub struct RateLimitConfig {
    pub max_requests_per_second: u64,
    pub burst_size: u64,
}
```

## Consequences

**Positive:**
- Defense in depth with multiple security layers
- TLS 1.3 provides strong encryption
- mTLS enables service-to-service authentication
- Replay protection prevents replay attacks

**Negative:**
- Security overhead increases latency
- Certificate management complexity
- Key rotation requires coordination

---

*End of ADR-007*
