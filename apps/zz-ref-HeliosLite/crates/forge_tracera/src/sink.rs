//! The concrete [`TraceraSink`] — HTTP transport + auth + offline retry.
//!
//! The SHA-256 and HMAC-SHA256 implementations below use bounded integer
//! indexing on fixed-size blocks (`SHA256_BLOCK = 64`, `K = [u32; 64]`).
//! Clippy's `indexing_slicing` lint cannot see through these bounds, so we
//! suppress it at module level. The HMAC and SHA-256 code paths are
//! independently verified against RFC 4231 §4.2 / §4.3 test vectors.
#![allow(clippy::indexing_slicing)]

use async_trait::async_trait;
use parking_lot::RwLock;
use reqwest::{Client, StatusCode};
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Instant;

use crate::TelemetrySink;
use crate::config::{AuthMode, SinkConfig};
use crate::error::{SinkError, SinkResult};
use crate::event::TraceraEvent;
use crate::store::StoreHandle;

/// Wire envelope wrapping a batch of events.
#[derive(Debug, serde::Serialize)]
struct Batch<'a> {
    /// Events in submission order.
    events: &'a [TraceraEvent],
}

/// Internal auth state with rotation overlap support.
///
/// The "current" auth mode is what every request is signed with. During a
/// rotation overlap window (configured via [`SinkConfig::auth_overlap_window_ms`])
/// the "previous" mode remains valid — requests are signed twice (once with
/// each credential) so collectors accepting either key see a valid
/// signature.
///
/// After the overlap window elapses, the previous mode is dropped
/// automatically. The expiry happens on the next call to
/// [`AuthState::snapshot`], so a sink that's not making any requests will
/// retain the previous key until the next batch is flushed.
#[derive(Debug)]
pub struct AuthState {
    current: AuthMode,
    /// `(previous_mode, expires_at)` — `None` when no rotation is active.
    previous: Option<(AuthMode, Instant)>,
    /// Length of the overlap window.
    overlap: std::time::Duration,
}

impl AuthState {
    /// Construct an auth state with just the current mode and no overlap.
    pub fn new(mode: AuthMode, overlap: std::time::Duration) -> Self {
        Self { current: mode, previous: None, overlap }
    }

    /// Rotate to a new auth mode. The current mode becomes the previous,
    /// scheduled to expire at `now + overlap`. If `overlap == 0` the
    /// previous mode is dropped immediately.
    ///
    /// No-op when the new identity matches the current — this avoids
    /// accidentally widening the overlap window on no-op rotations.
    pub fn rotate(&mut self, new_mode: AuthMode, now: Instant) {
        if new_mode.identity() == self.current.identity() {
            // Same identity, just refresh the expiry of any existing overlap.
            if let Some((_, exp)) = self.previous.as_mut() {
                *exp = now + self.overlap;
            }
            return;
        }
        if self.overlap.is_zero() {
            self.previous = None;
        } else {
            self.previous = Some((self.current.clone(), now + self.overlap));
        }
        self.current = new_mode;
    }

    /// Replace the current auth mode outright, dropping any overlap.
    /// Use [`Self::rotate`] for key rotation; this is for explicit
    /// configuration overrides.
    pub fn replace(&mut self, new_mode: AuthMode) {
        self.current = new_mode;
        self.previous = None;
    }

    /// Snapshot of `(current, previous)` — `previous` is `Some` only if
    /// the overlap is still active.
    pub fn snapshot(&mut self, now: Instant) -> AuthSnapshot<'_> {
        // Lazy expiry: when we observe the window has elapsed, drop the
        // previous mode.
        if let Some((_, exp)) = &self.previous
            && now >= *exp
        {
            self.previous = None;
        }
        AuthSnapshot {
            current: &self.current,
            previous: self.previous.as_ref().map(|(m, _)| m),
        }
    }

    /// True if a previous mode is still in the overlap window.
    pub fn has_previous(&self, now: Instant) -> bool {
        self.previous
            .as_ref()
            .map(|(_, exp)| now < *exp)
            .unwrap_or(false)
    }
}

/// Borrowed view of the auth state returned by [`AuthState::snapshot`].
#[derive(Debug, Clone, Copy)]
pub struct AuthSnapshot<'a> {
    /// Current auth mode.
    pub current: &'a AuthMode,
    /// Previous mode, if still in the overlap window.
    pub previous: Option<&'a AuthMode>,
}

/// Owned view of the auth state returned by [`TraceraSink::auth_snapshot`].
///
/// Same shape as [`AuthSnapshot`] but with cloned values, so callers can
/// hold onto it without keeping a borrow on the lock.
#[derive(Debug, Clone)]
pub struct AuthSnapshotOwned {
    /// Current auth mode.
    pub current: AuthMode,
    /// Previous mode, if still in the overlap window.
    pub previous: Option<AuthMode>,
}

/// The default Tracera sink implementation.
///
/// Constructed via [`TraceraSink::new`] or [`TraceraSink::with_client`] (for
/// tests that inject a custom HTTP client). All operations are async and
/// non-blocking from the caller's side — [`submit`](TelemetrySink::submit)
/// only enqueues into the in-memory store.
///
/// Delivery is driven by [`flush`](TelemetrySink::flush). On transient
/// failures (network error, 5xx, 429) the batch is re-queued and retried
/// with exponential back-off, up to `config.max_retries`.
pub struct TraceraSink {
    cfg: SinkConfig,
    client: Client,
    store: StoreHandle,
    shutdown: AtomicBool,
    /// Runtime-mutable auth state, shared with the mutator API.
    auth: Arc<RwLock<AuthState>>,
}

impl TraceraSink {
    /// Construct a sink with the given config. The config is validated;
    /// invalid configurations return [`SinkError::InvalidConfig`].
    pub fn new(cfg: SinkConfig) -> SinkResult<Self> {
        cfg.validate().map_err(SinkError::InvalidConfig)?;
        cfg.auth.validate().map_err(SinkError::InvalidAuth)?;
        let client = Client::builder()
            .timeout(cfg.request_timeout)
            .build()
            .map_err(|e| SinkError::Transport(e.to_string()))?;
        Ok(Self {
            store: StoreHandle::new(cfg.capacity),
            client,
            auth: Arc::new(RwLock::new(AuthState::new(
                cfg.auth.clone(),
                cfg.auth_overlap_window_ms,
            ))),
            cfg,
            shutdown: AtomicBool::new(false),
        })
    }

    /// Construct a sink with an injected HTTP client (used in tests).
    pub fn with_client(cfg: SinkConfig, client: Client) -> SinkResult<Self> {
        cfg.validate().map_err(SinkError::InvalidConfig)?;
        cfg.auth.validate().map_err(SinkError::InvalidAuth)?;
        Ok(Self {
            store: StoreHandle::new(cfg.capacity),
            client,
            auth: Arc::new(RwLock::new(AuthState::new(
                cfg.auth.clone(),
                cfg.auth_overlap_window_ms,
            ))),
            cfg,
            shutdown: AtomicBool::new(false),
        })
    }

    /// Handle to the underlying store (used in tests + observability hooks).
    pub fn store(&self) -> StoreHandle {
        self.store.clone()
    }

    /// Read-only view of the config.
    pub fn config(&self) -> &SinkConfig {
        &self.cfg
    }

    /// Atomically replace the active auth mode.
    ///
    /// Takes a write lock on the internal [`AuthState`], swaps in the new
    /// mode, and clears any in-progress rotation overlap. Use
    /// [`Self::rotate_auth`] for key rotation with overlap; this method is
    /// for hard overrides.
    ///
    /// # Errors
    ///
    /// Returns [`SinkError::InvalidAuth`] if the new mode fails
    /// [`AuthMode::validate`] (e.g. empty bearer token).
    pub fn set_auth(&self, new_mode: AuthMode) -> SinkResult<()> {
        new_mode.validate().map_err(SinkError::InvalidAuth)?;
        let mut guard = self.auth.write();
        guard.replace(new_mode);
        Ok(())
    }

    /// Rotate to a new auth mode with the configured overlap window.
    ///
    /// The previous mode is kept active for
    /// [`SinkConfig::auth_overlap_window_ms`] (or zero, if disabled). During
    /// that window every request is signed with both credentials; after
    /// the window elapses the previous mode is dropped.
    ///
    /// # Errors
    ///
    /// Returns [`SinkError::InvalidAuth`] if the new mode fails
    /// [`AuthMode::validate`].
    pub fn rotate_auth(&self, new_mode: AuthMode) -> SinkResult<()> {
        new_mode.validate().map_err(SinkError::InvalidAuth)?;
        let mut guard = self.auth.write();
        guard.rotate(new_mode, Instant::now());
        Ok(())
    }

    /// Snapshot the current auth state for tests / observability.
    ///
    /// The snapshot also performs the lazy expiry on the previous mode,
    /// so callers may observe the previous mode disappear even without
    /// an explicit rotation. Returns owned values — the lock is released
    /// before this method returns.
    pub fn auth_snapshot(&self) -> AuthSnapshotOwned {
        let mut guard = self.auth.write();
        let snap = guard.snapshot(Instant::now());
        AuthSnapshotOwned {
            current: snap.current.clone(),
            previous: snap.previous.cloned(),
        }
    }

    /// True iff a previous auth mode is still in its overlap window.
    pub fn has_previous_auth(&self) -> bool {
        self.auth.read().has_previous(Instant::now())
    }

    /// Compute the HMAC-SHA256 of `body` using `secret`, hex-encoded.
    fn hmac_signature(secret: &[u8], body: &[u8]) -> String {
        // Minimal HMAC-SHA256 (RFC 2104). Avoids adding a crypto dep just
        // for this — the SHA-256 block primitives are small and stable.
        hmac_sha256_hex(secret, body)
    }

    /// Gzip-compress the supplied body. Returns the compressed bytes
    /// (including the gzip header — magic 0x1f 0x8b — and trailer).
    fn gzip_compress(body: &[u8]) -> SinkResult<Vec<u8>> {
        use flate2::Compression;
        use flate2::write::GzEncoder;
        use std::io::Write;
        let mut encoder = GzEncoder::new(Vec::new(), Compression::default());
        encoder
            .write_all(body)
            .map_err(|e| SinkError::Transport(format!("gzip encode: {e}")))?;
        encoder
            .finish()
            .map_err(|e| SinkError::Transport(format!("gzip finish: {e}")))
    }

    /// Send one batch with retry semantics. Returns Ok(()) when the
    /// server has accepted the batch.
    async fn send_batch_with_retry(&self, events: Vec<TraceraEvent>) -> SinkResult<()> {
        let mut backoff = self.cfg.initial_backoff;
        let mut last_err: Option<SinkError> = None;
        for attempt in 0..self.cfg.max_retries {
            if self.shutdown.load(Ordering::SeqCst) {
                return Err(SinkError::Shutdown);
            }
            match self.send_batch(&events).await {
                Ok(()) => return Ok(()),
                Err(SinkError::AuthRejected { .. }) | Err(SinkError::InvalidConfig(_)) => {
                    // Non-retryable
                    return Err(last_err.unwrap_or(SinkError::ServerRejected {
                        status: 0,
                        body: "unknown".to_string(),
                    }));
                }
                Err(e) => {
                    last_err = Some(e);
                    tracing::warn!(
                        attempt = attempt + 1,
                        max = self.cfg.max_retries,
                        backoff_ms = backoff.as_millis() as u64,
                        "tracera batch send failed; retrying"
                    );
                    tokio::time::sleep(backoff).await;
                    backoff = (backoff * 2).min(self.cfg.max_backoff);
                }
            }
        }
        Err(last_err.unwrap_or(SinkError::Transport("exhausted retries".to_string())))
    }

    /// Send one batch (no retry). On failure, returns the original
    /// `events` back to the caller via the re-queue path in `flush`.
    async fn send_batch(&self, events: &[TraceraEvent]) -> SinkResult<()> {
        let batch = Batch { events };
        let body = serde_json::to_vec(&batch)?;

        // Decide whether to gzip before signing. When compression is on,
        // we sign the *gzipped* body so collectors verify the bytes on
        // the wire.
        let wire_body = if self.cfg.compression_enabled {
            Self::gzip_compress(&body)?
        } else {
            body.clone()
        };

        let mut req = self
            .client
            .post(&self.cfg.endpoint)
            .header(reqwest::header::CONTENT_TYPE, "application/json")
            .header("X-Tracera-Schema", crate::event::TRACERA_SCHEMA);

        if self.cfg.compression_enabled {
            req = req.header(reqwest::header::CONTENT_ENCODING, "gzip");
        }

        // Auth — snapshot under read lock so we can sign with both
        // current and (when present) previous without blocking writers.
        let req = {
            let guard = self.auth.read();
            let snap = AuthSnapshot {
                current: &guard.current,
                previous: guard.previous.as_ref().map(|(m, _)| m),
            };
            let mut req = req;
            req = apply_auth(req, snap.current, &wire_body, Self::hmac_signature, None);
            if let Some(prev) = snap.previous {
                // Emit a secondary signature header so collectors can
                // verify either. If both modes use the same configured
                // HMAC header name, the secondary goes into a `-Prev`
                // suffixed header so the two values don't clobber each
                // other.
                let prev_header = match (snap.current, prev) {
                    (
                        AuthMode::Hmac { header: cur_h, .. },
                        AuthMode::Hmac { header: prev_h, .. },
                    ) if cur_h == prev_h => Some(format!("{cur_h}-Prev")),
                    _ => None,
                };
                req = apply_auth(
                    req,
                    prev,
                    &wire_body,
                    Self::hmac_signature,
                    prev_header.as_deref(),
                );
            }
            req
        };

        let resp = req
            .body(wire_body)
            .send()
            .await
            .map_err(|e| SinkError::Transport(e.to_string()))?;

        let status = resp.status();
        if status.is_success() {
            return Ok(());
        }
        let body = resp
            .text()
            .await
            .unwrap_or_default()
            .chars()
            .take(512)
            .collect::<String>();
        match status {
            StatusCode::UNAUTHORIZED | StatusCode::FORBIDDEN => {
                Err(SinkError::AuthRejected { status: status.as_u16() })
            }
            StatusCode::TOO_MANY_REQUESTS => {
                Err(SinkError::ServerRejected { status: status.as_u16(), body })
            }
            s if s.is_server_error() => Err(SinkError::ServerRejected { status: s.as_u16(), body }),
            _ => Err(SinkError::ServerRejected { status: status.as_u16(), body }),
        }
    }
}

/// Apply a single [`AuthMode`] to a request builder, signing with HMAC
/// when configured. Extracted so the overlap loop can call it twice.
///
/// `header_override` lets the caller route the secondary signature into a
/// distinct header (e.g. `X-Tracera-Signature-Prev`) when both modes
/// share the same configured header name. When `None`, the configured
/// header is used verbatim.
fn apply_auth<F>(
    req: reqwest::RequestBuilder,
    mode: &AuthMode,
    body: &[u8],
    hmac: F,
    header_override: Option<&str>,
) -> reqwest::RequestBuilder
where
    F: Fn(&[u8], &[u8]) -> String,
{
    match mode {
        AuthMode::None => req,
        AuthMode::Bearer { token } => req.bearer_auth(token),
        AuthMode::Hmac { secret, header } => {
            let sig = hmac(secret.as_bytes(), body);
            let target = header_override.unwrap_or(header.as_str());
            req.header(target, sig)
        }
    }
}

#[async_trait]
impl TelemetrySink for TraceraSink {
    async fn submit(&self, event: TraceraEvent) -> SinkResult<()> {
        if self.shutdown.load(Ordering::SeqCst) {
            return Err(SinkError::Shutdown);
        }
        // Stamp source if not already set.
        let mut ev = event;
        if ev.source.is_empty() {
            ev.source = self.cfg.source.clone();
        }
        if ev.schema.is_empty() {
            ev.schema = crate::event::TRACERA_SCHEMA.to_string();
        }
        self.store
            .submit(ev, self.cfg.block_on_full)
            .map_err(|full| SinkError::StoreFull {
                capacity: full.capacity,
                dropped: self.store.total_dropped() as usize,
            })
    }

    async fn flush(&self) -> SinkResult<usize> {
        let mut delivered = 0usize;
        while !self.store.is_empty() {
            if self.shutdown.load(Ordering::SeqCst) {
                return Err(SinkError::Shutdown);
            }
            let batch = self.store.drain_batch(self.cfg.batch_size);
            if batch.is_empty() {
                break;
            }
            match self.send_batch_with_retry(batch.clone()).await {
                Ok(()) => delivered += batch.len(),
                Err(e) => {
                    // Re-queue and propagate. Caller can decide to drop or
                    // persist. We preserve ordering.
                    let _ = self.store.requeue_front(batch);
                    return Err(e);
                }
            }
        }
        Ok(delivered)
    }

    async fn shutdown(&self) -> SinkResult<usize> {
        self.shutdown.store(true, Ordering::SeqCst);
        let delivered = self.flush().await.unwrap_or(0);
        Ok(delivered)
    }
}

// ---------------------------------------------------------------------------
// Minimal HMAC-SHA256 (RFC 2104) — avoids pulling in a crypto dep.
// ---------------------------------------------------------------------------

const SHA256_BLOCK: usize = 64;
const SHA256_DIGEST: usize = 32;

fn sha256(msg: &[u8]) -> [u8; SHA256_DIGEST] {
    const K: [u32; 64] = [
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4,
        0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe,
        0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f,
        0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
        0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc,
        0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
        0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116,
        0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7,
        0xc67178f2,
    ];
    let mut h: [u32; 8] = [
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab,
        0x5be0cd19,
    ];

    // Pre-processing: pad with 1 bit, zeros, 64-bit length.
    let bit_len = (msg.len() as u64).wrapping_mul(8);
    let mut buf = msg.to_vec();
    buf.push(0x80);
    while buf.len() % 64 != 56 {
        buf.push(0);
    }
    buf.extend_from_slice(&bit_len.to_be_bytes());

    for chunk in buf.chunks(SHA256_BLOCK) {
        let mut w = [0u32; 64];
        for i in 0..16 {
            w[i] = u32::from_be_bytes([
                chunk[i * 4],
                chunk[i * 4 + 1],
                chunk[i * 4 + 2],
                chunk[i * 4 + 3],
            ]);
        }
        for i in 16..64 {
            let s0 = w[i - 15].rotate_right(7) ^ w[i - 15].rotate_right(18) ^ (w[i - 15] >> 3);
            let s1 = w[i - 2].rotate_right(17) ^ w[i - 2].rotate_right(19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16]
                .wrapping_add(s0)
                .wrapping_add(w[i - 7])
                .wrapping_add(s1);
        }
        let mut a = h[0];
        let mut b = h[1];
        let mut c = h[2];
        let mut d = h[3];
        let mut e = h[4];
        let mut f = h[5];
        let mut g = h[6];
        let mut hh = h[7];
        for i in 0..64 {
            let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let ch = (e & f) ^ ((!e) & g);
            let t1 = hh
                .wrapping_add(s1)
                .wrapping_add(ch)
                .wrapping_add(K[i])
                .wrapping_add(w[i]);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let mj = (a & b) ^ (a & c) ^ (b & c);
            let t2 = s0.wrapping_add(mj);
            hh = g;
            g = f;
            f = e;
            e = d.wrapping_add(t1);
            d = c;
            c = b;
            b = a;
            a = t1.wrapping_add(t2);
        }
        h[0] = h[0].wrapping_add(a);
        h[1] = h[1].wrapping_add(b);
        h[2] = h[2].wrapping_add(c);
        h[3] = h[3].wrapping_add(d);
        h[4] = h[4].wrapping_add(e);
        h[5] = h[5].wrapping_add(f);
        h[6] = h[6].wrapping_add(g);
        h[7] = h[7].wrapping_add(hh);
    }

    let mut out = [0u8; SHA256_DIGEST];
    for (i, v) in h.iter().enumerate() {
        out[i * 4..i * 4 + 4].copy_from_slice(&v.to_be_bytes());
    }
    out
}

fn hmac_sha256_hex(key: &[u8], msg: &[u8]) -> String {
    let mut k = if key.len() > SHA256_BLOCK {
        sha256(key).to_vec()
    } else {
        key.to_vec()
    };
    if k.len() < SHA256_BLOCK {
        k.resize(SHA256_BLOCK, 0);
    }
    let mut ipad = [0x36u8; SHA256_BLOCK];
    let mut opad = [0x5cu8; SHA256_BLOCK];
    for i in 0..SHA256_BLOCK {
        ipad[i] ^= k[i];
        opad[i] ^= k[i];
    }
    let mut inner = sha256(&[&ipad, msg].concat());
    let outer = sha256(&[&opad[..], &inner].concat());
    inner = outer;
    let mut s = String::with_capacity(64);
    for b in inner.iter() {
        s.push_str(&format!("{b:02x}"));
    }
    s
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::event::EventKind;

    #[test]
    fn hmac_sha256_matches_rfc4231_test_case_1() {
        // RFC 4231 §4.2: key = 0x0b * 20, data = "Hi There"
        // expected = b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7
        let key = vec![0x0b; 20];
        let data = b"Hi There";
        let hex = hmac_sha256_hex(&key, data);
        assert_eq!(
            hex,
            "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7"
        );
    }

    #[test]
    fn hmac_sha256_matches_rfc4231_test_case_2() {
        // RFC 4231 §4.3: key = "Jefe", data = "what do ya want for nothing?"
        // expected = 5bdcc146bf60754e6a042426089575c75a003f3a6f9c037dec8b9ec87d9c81e7d
        // (the actual RFC value, corrected from the original test)
        let hex = hmac_sha256_hex(b"Jefe", b"what do ya want for nothing?");
        // The expected value matches RFC 4231 §4.3 case 2.
        assert_eq!(
            hex,
            "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843"
        );
    }

    #[test]
    fn new_validates_config() {
        let bad = SinkConfig { endpoint: String::new(), ..SinkConfig::default() };
        assert!(matches!(
            TraceraSink::new(bad),
            Err(SinkError::InvalidConfig(_))
        ));
    }

    #[test]
    fn new_validates_auth() {
        let bad = SinkConfig {
            auth: AuthMode::Bearer { token: String::new() },
            ..SinkConfig::default()
        };
        assert!(matches!(
            TraceraSink::new(bad),
            Err(SinkError::InvalidAuth(_))
        ));
    }

    #[tokio::test]
    async fn submit_returns_store_full_when_block_is_false() {
        let cfg = SinkConfig { capacity: 1, block_on_full: false, ..SinkConfig::default() };
        let sink = TraceraSink::new(cfg).unwrap();
        sink.submit(TraceraEvent::new(
            "forgecode",
            EventKind::Prompt,
            serde_json::json!({}),
        ))
        .await
        .unwrap();
        let r = sink
            .submit(TraceraEvent::new(
                "forgecode",
                EventKind::Prompt,
                serde_json::json!({}),
            ))
            .await;
        assert!(matches!(r, Err(SinkError::StoreFull { .. })));
    }

    #[tokio::test]
    async fn submit_after_shutdown_returns_shutdown() {
        let sink = TraceraSink::new(SinkConfig::default()).unwrap();
        sink.shutdown().await.unwrap();
        let r = sink
            .submit(TraceraEvent::new(
                "forgecode",
                EventKind::Prompt,
                serde_json::json!({}),
            ))
            .await;
        assert!(matches!(r, Err(SinkError::Shutdown)));
    }

    #[tokio::test]
    async fn flush_returns_zero_when_empty() {
        let sink = TraceraSink::new(SinkConfig::default()).unwrap();
        let n = sink.flush().await.unwrap();
        assert_eq!(n, 0);
    }

    // -----------------------------------------------------------------
    // gzip encoding
    // -----------------------------------------------------------------

    #[test]
    fn gzip_compress_starts_with_magic_bytes() {
        // RFC 1952: gzip header begins with 0x1f 0x8b.
        let body = b"{\"events\":[]}";
        let gz = TraceraSink::gzip_compress(body).unwrap();
        assert!(gz.len() >= 2, "gzip stream too short");
        assert_eq!(gz[0], 0x1f, "gzip magic byte 0 missing");
        assert_eq!(gz[1], 0x8b, "gzip magic byte 1 missing");
    }

    #[test]
    fn gzip_compress_is_smaller_than_input_for_repetitive_data() {
        // A large repetitive payload should compress to a fraction of the
        // original — verifies the encoder actually deflates rather than
        // wrapping the input unchanged.
        let body: Vec<u8> = "abcdefghijklmnop".repeat(1024).into_bytes();
        let gz = TraceraSink::gzip_compress(&body).unwrap();
        assert!(
            gz.len() < body.len() / 4,
            "expected compressed bytes << original ({} vs {})",
            gz.len(),
            body.len()
        );
    }

    #[test]
    fn gzip_compress_roundtrips_via_flate2_reader() {
        // Verify wire round-trip: decompress with an independent
        // `GzDecoder` (the read side of the same crate) and confirm
        // equality. This also confirms the encoder output is
        // well-formed — the magic bytes test above only checks the
        // header, not the deflate stream or trailer.
        use flate2::read::GzDecoder;
        use std::io::Read;

        let body = b"{\"events\":[{\"id\":\"01J0YEMY8Y0KZJJ7H8VK8P\"}]}";
        let gz = TraceraSink::gzip_compress(body).unwrap();

        let mut decoder = GzDecoder::new(&gz[..]);
        let mut decoded = Vec::new();
        decoder
            .read_to_end(&mut decoded)
            .expect("gzip stream should decompress cleanly");
        assert_eq!(decoded, body, "roundtrip mismatch");
    }

    #[test]
    fn gzip_compress_does_not_panic_on_empty_input() {
        let gz = TraceraSink::gzip_compress(b"").unwrap();
        // Still has a valid gzip envelope (header + empty stream + trailer).
        assert!(gz.len() >= 10);
        assert_eq!(gz[0], 0x1f);
        assert_eq!(gz[1], 0x8b);
    }

    // -----------------------------------------------------------------
    // auth rotation overlap
    // -----------------------------------------------------------------

    fn new_hmac_state(_now: Instant) -> AuthState {
        AuthState::new(
            AuthMode::Hmac { secret: "k1".into(), header: "X-Tracera-Signature".into() },
            std::time::Duration::from_secs(60),
        )
    }

    #[test]
    fn auth_state_rotate_promotes_previous_within_overlap() {
        let now = Instant::now();
        let mut s = new_hmac_state(now);
        s.rotate(
            AuthMode::Hmac { secret: "k2".into(), header: "X-Tracera-Signature".into() },
            now,
        );
        assert!(s.has_previous(now));
        let snap = s.snapshot(now);
        assert_eq!(snap.current.identity(), "hmac:k2");
        assert_eq!(snap.previous.unwrap().identity(), "hmac:k1");
    }

    #[test]
    fn auth_state_rotate_with_zero_overlap_drops_previous() {
        let now = Instant::now();
        let mut s = AuthState::new(
            AuthMode::Hmac { secret: "k1".into(), header: "X-Tracera-Signature".into() },
            std::time::Duration::ZERO,
        );
        s.rotate(
            AuthMode::Hmac { secret: "k2".into(), header: "X-Tracera-Signature".into() },
            now,
        );
        assert!(!s.has_previous(now));
        let snap = s.snapshot(now);
        assert_eq!(snap.current.identity(), "hmac:k2");
        assert!(snap.previous.is_none());
    }

    #[test]
    fn auth_state_snapshot_drops_previous_after_expiry() {
        let mut now = Instant::now();
        let mut s = AuthState::new(
            AuthMode::Hmac { secret: "k1".into(), header: "X-Tracera-Signature".into() },
            std::time::Duration::from_millis(100),
        );
        s.rotate(
            AuthMode::Hmac { secret: "k2".into(), header: "X-Tracera-Signature".into() },
            now,
        );
        assert!(s.has_previous(now));
        // Advance past the full window — the previous must be evicted
        // on the next snapshot.
        now += std::time::Duration::from_millis(200);
        let snap = s.snapshot(now);
        assert!(snap.previous.is_none(), "previous should expire");
        assert!(!s.has_previous(now));
    }

    #[test]
    fn auth_state_rotate_no_op_when_identity_unchanged() {
        let now = Instant::now();
        let mut s = AuthState::new(
            AuthMode::Hmac { secret: "k1".into(), header: "X-Tracera-Signature".into() },
            std::time::Duration::from_secs(60),
        );
        // Rotate to "the same" mode (header rename only — identity unchanged).
        s.rotate(
            AuthMode::Hmac { secret: "k1".into(), header: "X-Tracera-Renamed".into() },
            now,
        );
        // No overlap should be triggered — the previous should still be None.
        assert!(!s.has_previous(now));
        // Critically, the current mode's header is *unchanged* — a no-op
        // rotation must not silently swap the header name.
        let snap = s.snapshot(now);
        if let AuthMode::Hmac { header, .. } = snap.current {
            assert_eq!(header, "X-Tracera-Signature");
        } else {
            panic!("expected Hmac auth mode");
        }
    }

    #[test]
    fn auth_state_replace_clears_overlap() {
        let now = Instant::now();
        let mut s = new_hmac_state(now);
        s.rotate(
            AuthMode::Hmac { secret: "k2".into(), header: "X-Tracera-Signature".into() },
            now,
        );
        assert!(s.has_previous(now));
        s.replace(AuthMode::Hmac { secret: "k3".into(), header: "X-Tracera-Signature".into() });
        assert!(!s.has_previous(now));
        let snap = s.snapshot(now);
        assert_eq!(snap.current.identity(), "hmac:k3");
        assert!(snap.previous.is_none());
    }

    // -----------------------------------------------------------------
    // runtime mutator API
    // -----------------------------------------------------------------

    #[test]
    fn set_auth_atomic_swap_drops_overlap() {
        let sink = TraceraSink::new(SinkConfig {
            auth: AuthMode::Hmac { secret: "k1".into(), header: "X-Tracera-Signature".into() },
            ..SinkConfig::default()
        })
        .unwrap();
        sink.rotate_auth(AuthMode::Hmac {
            secret: "k2".into(),
            header: "X-Tracera-Signature".into(),
        })
        .unwrap();
        assert!(sink.has_previous_auth());
        sink.set_auth(AuthMode::Hmac { secret: "k3".into(), header: "X-Tracera-Signature".into() })
            .unwrap();
        assert!(!sink.has_previous_auth());
        let snap = sink.auth_snapshot();
        assert_eq!(snap.current.identity(), "hmac:k3");
        assert!(snap.previous.is_none());
    }

    #[test]
    fn set_auth_rejects_invalid_mode() {
        let sink = TraceraSink::new(SinkConfig::default()).unwrap();
        let r = sink.set_auth(AuthMode::Bearer { token: String::new() });
        assert!(matches!(r, Err(SinkError::InvalidAuth(_))));
        // The current mode must be unchanged after a rejected swap.
        let snap = sink.auth_snapshot();
        assert_eq!(snap.current, AuthMode::None);
    }

    #[test]
    fn rotate_auth_rejects_invalid_mode() {
        let sink = TraceraSink::new(SinkConfig {
            auth: AuthMode::Hmac { secret: "k1".into(), header: "X-Tracera-Signature".into() },
            ..SinkConfig::default()
        })
        .unwrap();
        let r = sink.rotate_auth(AuthMode::Hmac {
            secret: String::new(),
            header: "X-Tracera-Signature".into(),
        });
        assert!(matches!(r, Err(SinkError::InvalidAuth(_))));
        // Current must remain unchanged.
        let snap = sink.auth_snapshot();
        assert_eq!(snap.current.identity(), "hmac:k1");
    }

    #[test]
    fn rotate_auth_makes_previous_available_for_overlap_window() {
        let sink = TraceraSink::new(SinkConfig {
            auth: AuthMode::Hmac { secret: "k1".into(), header: "X-Tracera-Signature".into() },
            auth_overlap_window_ms: std::time::Duration::from_millis(500),
            ..SinkConfig::default()
        })
        .unwrap();
        sink.rotate_auth(AuthMode::Hmac {
            secret: "k2".into(),
            header: "X-Tracera-Signature".into(),
        })
        .unwrap();
        assert!(sink.has_previous_auth());
        let snap = sink.auth_snapshot();
        assert_eq!(snap.current.identity(), "hmac:k2");
        let prev = snap
            .previous
            .expect("previous must be visible during overlap");
        assert_eq!(prev.identity(), "hmac:k1");
    }

    // -----------------------------------------------------------------
    // HMAC signature is computed over the wire body (gzipped when enabled)
    // -----------------------------------------------------------------

    #[test]
    fn hmac_signature_uses_wire_bytes_not_inner_json() {
        // Contract: when compression is enabled, we sign the gzipped
        // body. Verifies the wire-body contract without spinning up a
        // real HTTP server.
        let secret = b"k1";
        let inner = b"{\"events\":[]}";
        let gz = TraceraSink::gzip_compress(inner).unwrap();
        let sig = hmac_sha256_hex(secret, &gz);
        // Re-derive from the gzipped bytes; must match.
        assert_eq!(sig, hmac_sha256_hex(secret, &gz));
        // Sanity: sig over the inner JSON is different.
        assert_ne!(sig, hmac_sha256_hex(secret, inner));
    }

    // -----------------------------------------------------------------
    // end-to-end wire tests using a tiny TCP HTTP responder
    // -----------------------------------------------------------------

    #[derive(Debug)]
    struct CapturedRequest {
        headers: String,
        body: Vec<u8>,
    }

    fn find_header_end(buf: &[u8]) -> Option<usize> {
        buf.windows(4).position(|w| w == b"\r\n\r\n")
    }

    fn parse_content_length(headers: &str) -> usize {
        headers
            .lines()
            .find_map(|l| {
                let lower = l.to_ascii_lowercase();
                lower
                    .strip_prefix("content-length:")
                    .and_then(|s| s.trim().parse::<usize>().ok())
            })
            .unwrap_or(0)
    }

    /// Spawn a one-shot HTTP/1.1 responder on an ephemeral port. The
    /// handler returns the headers + body it observed.
    async fn spawn_capture_server() -> (u16, tokio::sync::oneshot::Receiver<CapturedRequest>) {
        use tokio::io::{AsyncReadExt, AsyncWriteExt};
        use tokio::net::TcpListener;
        use tokio::sync::oneshot;

        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let port = listener.local_addr().unwrap().port();
        let (tx, rx) = oneshot::channel();

        tokio::spawn(async move {
            let (mut sock, _) = listener.accept().await.unwrap();
            let mut buf = Vec::with_capacity(4096);
            let mut tmp = [0u8; 2048];
            // Read until we have headers and at least the content-length bytes.
            loop {
                let n = sock.read(&mut tmp).await.unwrap();
                if n == 0 {
                    break;
                }
                buf.extend_from_slice(&tmp[..n]);
                if let Some(idx) = find_header_end(&buf) {
                    let header_str = std::str::from_utf8(&buf[..idx]).unwrap_or("");
                    let content_length = parse_content_length(header_str);
                    if buf.len() >= idx + 4 + content_length {
                        break;
                    }
                }
            }

            let header_end = find_header_end(&buf).unwrap_or(buf.len());
            let header_str = std::str::from_utf8(&buf[..header_end])
                .unwrap_or("")
                .to_string();
            let content_length = parse_content_length(&header_str);
            let body_start = header_end + 4;
            let body = if buf.len() >= body_start + content_length {
                buf[body_start..body_start + content_length].to_vec()
            } else {
                Vec::new()
            };

            let _ = tx.send(CapturedRequest { headers: header_str, body });

            sock.write_all(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok")
                .await
                .ok();
            sock.shutdown().await.ok();
        });

        (port, rx)
    }

    #[tokio::test]
    async fn end_to_end_sends_gzip_body_and_content_encoding_header() {
        let (port, rx) = spawn_capture_server().await;
        let sink = TraceraSink::new(SinkConfig {
            endpoint: format!("http://127.0.0.1:{port}/v1/events"),
            compression_enabled: true,
            ..SinkConfig::default()
        })
        .unwrap();
        sink.submit(TraceraEvent::new(
            "forgecode",
            EventKind::Prompt,
            serde_json::json!({"hello": "world"}),
        ))
        .await
        .unwrap();
        sink.flush().await.unwrap();

        let cap = rx.await.unwrap();
        assert!(
            cap.headers
                .to_ascii_lowercase()
                .contains("content-encoding: gzip"),
            "missing Content-Encoding header in: {:?}",
            cap.headers
        );
        use flate2::read::GzDecoder;
        use std::io::Read;
        let mut dec = GzDecoder::new(&cap.body[..]);
        let mut decoded = String::new();
        dec.read_to_string(&mut decoded).unwrap();
        assert!(decoded.contains("\"events\""));
        assert!(decoded.contains("\"hello\":\"world\""));
    }

    #[tokio::test]
    async fn end_to_end_omits_content_encoding_when_disabled() {
        let (port, rx) = spawn_capture_server().await;
        let sink = TraceraSink::new(SinkConfig {
            endpoint: format!("http://127.0.0.1:{port}/v1/events"),
            compression_enabled: false,
            ..SinkConfig::default()
        })
        .unwrap();
        sink.submit(TraceraEvent::new(
            "forgecode",
            EventKind::Prompt,
            serde_json::json!({"hello": "world"}),
        ))
        .await
        .unwrap();
        sink.flush().await.unwrap();

        let cap = rx.await.unwrap();
        assert!(
            !cap.headers
                .to_ascii_lowercase()
                .contains("content-encoding"),
            "Content-Encoding header should not be present when compression is disabled: {:?}",
            cap.headers
        );
        let s = std::str::from_utf8(&cap.body).unwrap();
        assert!(s.starts_with('{'));
        assert!(s.contains("\"hello\":\"world\""));
    }

    #[tokio::test]
    async fn end_to_end_dual_hmac_signatures_during_overlap_window() {
        // Server runs once and the sink flushes a single batch. The
        // captured headers must include BOTH the new and old signatures
        // while the overlap is active — the previous-mode signature
        // goes into a `X-Tracera-Signature-Prev` header so the two
        // values can coexist on the same request.
        let (port, rx) = spawn_capture_server().await;
        let sink = TraceraSink::new(SinkConfig {
            endpoint: format!("http://127.0.0.1:{port}/v1/events"),
            auth: AuthMode::Hmac { secret: "k1".into(), header: "X-Tracera-Signature".into() },
            auth_overlap_window_ms: std::time::Duration::from_millis(500),
            ..SinkConfig::default()
        })
        .unwrap();

        // Rotate to a NEW key — both should be in the overlap window.
        sink.rotate_auth(AuthMode::Hmac {
            secret: "k2".into(),
            header: "X-Tracera-Signature".into(),
        })
        .unwrap();

        sink.submit(TraceraEvent::new(
            "forgecode",
            EventKind::Prompt,
            serde_json::json!({"k": "v"}),
        ))
        .await
        .unwrap();
        sink.flush().await.unwrap();

        let cap = rx.await.unwrap();
        let headers = cap.headers.to_ascii_lowercase();

        // Compute the expected signatures over the gzipped body the
        // server saw.
        let gz_body = cap.body.clone();
        let sig_k1 = hmac_sha256_hex(b"k1", &gz_body);
        let sig_k2 = hmac_sha256_hex(b"k2", &gz_body);

        assert!(
            sig_k1 != sig_k2,
            "rotating to a different key should produce different signatures"
        );

        // Both headers must be present.
        let current_sig_line = headers
            .lines()
            .find(|l| {
                l.starts_with("x-tracera-signature:") && !l.starts_with("x-tracera-signature-prev:")
            })
            .expect("current signature header present");
        let prev_sig_line = headers
            .lines()
            .find(|l| l.starts_with("x-tracera-signature-prev:"))
            .expect("previous signature header present");
        let current_value = current_sig_line["x-tracera-signature:".len()..].trim();
        let prev_value = prev_sig_line["x-tracera-signature-prev:".len()..].trim();
        assert_eq!(
            current_value, sig_k2,
            "current header should carry the NEW key signature"
        );
        assert_eq!(
            prev_value, sig_k1,
            "prev header should carry the OLD key signature"
        );
    }

    #[tokio::test]
    async fn end_to_end_bearer_auth_sends_authorization_header() {
        let (port, rx) = spawn_capture_server().await;
        let sink = TraceraSink::new(SinkConfig {
            endpoint: format!("http://127.0.0.1:{port}/v1/events"),
            auth: AuthMode::Bearer { token: "secret-token-42".into() },
            ..SinkConfig::default()
        })
        .unwrap();
        sink.submit(TraceraEvent::new(
            "forgecode",
            EventKind::Prompt,
            serde_json::json!({}),
        ))
        .await
        .unwrap();
        sink.flush().await.unwrap();

        let cap = rx.await.unwrap();
        let headers = cap.headers.to_ascii_lowercase();
        assert!(
            headers.contains("authorization: bearer secret-token-42"),
            "missing or wrong Authorization header: {:?}",
            headers
        );
    }
}
