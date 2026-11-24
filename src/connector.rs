//! Phenotype registry connector contract.
//!
//! [`Connector`] adapters (`PlaneConnector`, `GitHubConnector`,
//! `ImportConnector`) expose change records to a polling consumer.
//!
//! # Contract
//!
//! - [`Connector::connect`] validates a [`ConnectorConfig`] matches
//!   the connector's [`ConnectorKind`]; mismatches return
//!   [`ConnectorError::KindMismatch`].
//! - [`Connector::fetch_changes`] returns [`Change`]s since the last
//!   call. Implementations must:
//!   1. Track a cursor (last-seen id) and emit strictly-increasing
//!      ids.
//!   2. Return `Ok(vec![])` (not an error) when there are no new
//!      changes.
//!   3. Never fabricate hard-coded identifiers like the historical
//!      `"stub-change"` literal — see [`ChangesProvider`].
//!
//! Default providers are deterministic and produce distinct,
//! sequential ids (e.g. `Import:1`, `Import:2`).

use std::future::Future;
use std::pin::Pin;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Mutex;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ConnectorKind {
    Plane,
    GitHub,
    Import,
}

/// Configuration for connecting to a phenotype data source.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ConnectorConfig {
    pub kind: ConnectorKind,
    pub endpoint: String,
}

impl ConnectorConfig {
    pub fn new(kind: ConnectorKind, endpoint: impl Into<String>) -> Self {
        ConnectorConfig {
            kind,
            endpoint: endpoint.into(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Connection {
    pub kind: ConnectorKind,
    pub endpoint: String,
    pub connected: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Change {
    pub id: String,
    pub source: ConnectorKind,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ConnectorError {
    KindMismatch {
        expected: ConnectorKind,
        actual: ConnectorKind,
    },
    /// The provider did not yield any changes.
    NoChangesAvailable,
}

// ---------------------------------------------------------------------------
// ChangesProvider — the real source-of-truth contract
// ---------------------------------------------------------------------------

/// Pluggable backend that produces [`Change`]s.
///
/// `fetch` is sync + returns a boxed `Future` so the trait is
/// dyn-compatible (plain `async fn` is not).
pub trait ChangesProvider: Send + Sync {
    fn fetch(
        &self,
        from_sequence: u64,
    ) -> Pin<Box<dyn Future<Output = Result<Vec<Change>, ConnectorError>> + Send + '_>>;
}

// ---------------------------------------------------------------------------
// Built-in test providers (deterministic, no network)
// ---------------------------------------------------------------------------

#[derive(Debug, Default, Clone, Copy)]
pub struct EmptyChangesProvider;

impl ChangesProvider for EmptyChangesProvider {
    fn fetch(
        &self,
        _from_sequence: u64,
    ) -> Pin<Box<dyn Future<Output = Result<Vec<Change>, ConnectorError>> + Send + '_>> {
        Box::pin(async move { Ok(Vec::new()) })
    }
}

/// Yields a fixed script of synthetic changes per call.
#[derive(Debug)]
pub struct SequenceChangesProvider {
    source: ConnectorKind,
    script: Vec<String>,
    cursor: std::sync::atomic::AtomicUsize,
}

impl SequenceChangesProvider {
    /// Construct a sequence provider yielding `<source>:1`, … per call.
    pub fn with_length(source: ConnectorKind, len: usize) -> Self {
        Self {
            source,
            script: (1..=len).map(|i| format!("{source:?}:{i}")).collect(),
            cursor: std::sync::atomic::AtomicUsize::new(0),
        }
    }

    pub fn remaining(&self) -> usize {
        self.script
            .len()
            .saturating_sub(self.cursor.load(Ordering::SeqCst))
    }
}

impl ChangesProvider for SequenceChangesProvider {
    fn fetch(
        &self,
        _from_sequence: u64,
    ) -> Pin<Box<dyn Future<Output = Result<Vec<Change>, ConnectorError>> + Send + '_>> {
        let idx = self.cursor.fetch_add(1, Ordering::SeqCst);
        let source = self.source;
        let result = if idx < self.script.len() {
            Ok(vec![Change {
                id: self.script[idx].clone(),
                source,
            }])
        } else {
            Ok(Vec::new())
        };
        Box::pin(async move { result })
    }
}

// ---------------------------------------------------------------------------
// Connector trait
// ---------------------------------------------------------------------------

#[allow(async_fn_in_trait)]
pub trait Connector {
    async fn connect(config: ConnectorConfig) -> Result<Connection, ConnectorError>
    where
        Self: Sized;

    async fn fetch_changes(&self) -> Result<Vec<Change>, ConnectorError>;
}

/// Shared connector state: backing provider, monotonic cursor and
/// dedup set of seen change ids.
struct ConnectorState {
    provider: Box<dyn ChangesProvider>,
    cursor_seq: AtomicU64,
    seen: Mutex<Vec<String>>,
}

impl std::fmt::Debug for ConnectorState {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ConnectorState")
            .field("cursor_seq", &self.cursor_seq.load(Ordering::SeqCst))
            .field("seen_len", &self.seen.lock().map(|g| g.len()).unwrap_or(0))
            .finish()
    }
}

impl ConnectorState {
    fn new(provider: impl ChangesProvider + 'static) -> Self {
        Self {
            provider: Box::new(provider),
            cursor_seq: AtomicU64::new(0),
            seen: Mutex::new(Vec::new()),
        }
    }

    /// Pull new changes since `cursor_seq` and update the cursor.
    async fn pull_new(&self) -> Result<Vec<Change>, ConnectorError> {
        let prev_seq = self.cursor_seq.load(Ordering::SeqCst);
        let mut changes: Vec<Change> = self.provider.fetch(prev_seq).await?;
        // Stable fallback ordering by id.
        changes.sort_by(|a, b| a.id.cmp(&b.id));

        let mut seen = self.seen.lock().expect("seen mutex poisoned");
        let fresh: Vec<Change> = changes
            .into_iter()
            .filter(|c| !seen.contains(&c.id))
            .collect();
        for c in &fresh {
            seen.push(c.id.clone());
        }
        if !fresh.is_empty() {
            self.cursor_seq
                .store(prev_seq.wrapping_add(fresh.len() as u64), Ordering::SeqCst);
        }
        Ok(fresh)
    }
}

// ---------------------------------------------------------------------------
// Concrete connectors
// ---------------------------------------------------------------------------

#[derive(Debug)]
pub struct PlaneConnector {
    state: ConnectorState,
}

impl Default for PlaneConnector {
    fn default() -> Self {
        Self {
            state: ConnectorState::new(EmptyChangesProvider),
        }
    }
}

impl PlaneConnector {
    /// Construct a `PlaneConnector` backed by `provider`.
    pub fn with_provider(provider: impl ChangesProvider + 'static) -> Self {
        Self {
            state: ConnectorState::new(provider),
        }
    }
}

impl Connector for PlaneConnector {
    async fn connect(config: ConnectorConfig) -> Result<Connection, ConnectorError> {
        connection_for(ConnectorKind::Plane, config)
    }

    async fn fetch_changes(&self) -> Result<Vec<Change>, ConnectorError> {
        self.state.pull_new().await
    }
}

#[derive(Debug)]
pub struct GitHubConnector {
    state: ConnectorState,
}

impl Default for GitHubConnector {
    fn default() -> Self {
        Self {
            state: ConnectorState::new(EmptyChangesProvider),
        }
    }
}

impl GitHubConnector {
    pub fn with_provider(provider: impl ChangesProvider + 'static) -> Self {
        Self {
            state: ConnectorState::new(provider),
        }
    }
}

impl Connector for GitHubConnector {
    async fn connect(config: ConnectorConfig) -> Result<Connection, ConnectorError> {
        connection_for(ConnectorKind::GitHub, config)
    }

    async fn fetch_changes(&self) -> Result<Vec<Change>, ConnectorError> {
        self.state.pull_new().await
    }
}

#[derive(Debug)]
pub struct ImportConnector {
    state: ConnectorState,
}

impl Default for ImportConnector {
    fn default() -> Self {
        Self {
            state: ConnectorState::new(EmptyChangesProvider),
        }
    }
}

impl ImportConnector {
    pub fn with_provider(provider: impl ChangesProvider + 'static) -> Self {
        Self {
            state: ConnectorState::new(provider),
        }
    }
}

impl Connector for ImportConnector {
    async fn connect(config: ConnectorConfig) -> Result<Connection, ConnectorError> {
        connection_for(ConnectorKind::Import, config)
    }

    async fn fetch_changes(&self) -> Result<Vec<Change>, ConnectorError> {
        self.state.pull_new().await
    }
}

// ---------------------------------------------------------------------------
// Shared connection validation
// ---------------------------------------------------------------------------

fn connection_for(
    expected: ConnectorKind,
    config: ConnectorConfig,
) -> Result<Connection, ConnectorError> {
    if config.kind != expected {
        return Err(ConnectorError::KindMismatch {
            expected,
            actual: config.kind,
        });
    }

    Ok(Connection {
        kind: config.kind,
        endpoint: config.endpoint,
        connected: true,
    })
}

// ===========================================================================
// Tests
// ===========================================================================

#[cfg(test)]
mod tests {
    use super::*;
    use std::future::Future;
    use std::pin::pin;
    use std::task::{Context, Poll, Waker};

    fn block_on<T>(future: impl Future<Output = T>) -> T {
        let waker = Waker::noop();
        let mut context = Context::from_waker(waker);
        let mut future = pin!(future);

        loop {
            match future.as_mut().poll(&mut context) {
                Poll::Ready(output) => return output,
                Poll::Pending => std::thread::yield_now(),
            }
        }
    }

    fn config(kind: ConnectorKind) -> ConnectorConfig {
        ConnectorConfig {
            kind,
            endpoint: format!("local://{kind:?}"),
        }
    }

    #[test]
    fn connector_kind_covers_requested_adapters() {
        assert_eq!(ConnectorKind::Plane, ConnectorKind::Plane);
        assert_eq!(ConnectorKind::GitHub, ConnectorKind::GitHub);
        assert_eq!(ConnectorKind::Import, ConnectorKind::Import);
    }

    #[test]
    fn plane_connector_connects_and_yields_empty_when_provider_is_empty() {
        let connection = block_on(PlaneConnector::connect(config(ConnectorKind::Plane))).unwrap();
        let changes = block_on(PlaneConnector::default().fetch_changes()).unwrap();

        assert_eq!(connection.kind, ConnectorKind::Plane);
        assert!(connection.connected);
        assert!(changes.is_empty());
    }

    #[test]
    fn github_connector_connects_and_yields_empty_by_default() {
        let connection = block_on(GitHubConnector::connect(config(ConnectorKind::GitHub))).unwrap();
        let changes = block_on(GitHubConnector::default().fetch_changes()).unwrap();

        assert_eq!(connection.kind, ConnectorKind::GitHub);
        assert!(connection.connected);
        assert!(changes.is_empty());
    }

    #[test]
    fn import_connector_rejects_mismatched_config() {
        let error = block_on(ImportConnector::connect(config(ConnectorKind::Plane))).unwrap_err();

        assert_eq!(
            error,
            ConnectorError::KindMismatch {
                expected: ConnectorKind::Import,
                actual: ConnectorKind::Plane,
            }
        );
    }

    #[test]
    fn connection_for_matching_kind_succeeds() {
        let cfg = config(ConnectorKind::Plane);
        let conn = connection_for(ConnectorKind::Plane, cfg).unwrap();
        assert_eq!(conn.kind, ConnectorKind::Plane);
        assert!(conn.connected);
    }

    #[test]
    fn connection_for_non_matching_kind_fails() {
        let cfg = config(ConnectorKind::GitHub);
        let err = connection_for(ConnectorKind::Plane, cfg).unwrap_err();
        assert_eq!(
            err,
            ConnectorError::KindMismatch {
                expected: ConnectorKind::Plane,
                actual: ConnectorKind::GitHub,
            }
        );
    }

    #[test]
    fn sequence_provider_emits_each_change_once_per_call() {
        let provider = SequenceChangesProvider::with_length(ConnectorKind::Import, 3);
        let connector = ImportConnector::with_provider(provider);

        let first = block_on(connector.fetch_changes()).unwrap();
        let second = block_on(connector.fetch_changes()).unwrap();
        let third = block_on(connector.fetch_changes()).unwrap();
        let fourth = block_on(connector.fetch_changes()).unwrap();

        assert_eq!(first.len(), 1);
        assert_eq!(second.len(), 1);
        assert_eq!(third.len(), 1);
        assert!(fourth.is_empty(), "provider should exhaust at length 3");

        let all_ids: Vec<&String> = first
            .iter()
            .chain(second.iter())
            .chain(third.iter())
            .map(|c| &c.id)
            .collect();
        assert_eq!(all_ids.len(), 3);
        for id in &all_ids {
            assert!(
                !id.contains("stub-change"),
                "ids must not encode the historical stub literal: {id}"
            );
        }
        assert!(all_ids.iter().any(|s| s.as_str() == "Import:1"));
        assert!(all_ids.iter().any(|s| s.as_str() == "Import:2"));
        assert!(all_ids.iter().any(|s| s.as_str() == "Import:3"));
    }

    #[test]
    fn connector_deduplicates_changes_across_calls() {
        // Provider returns the same id on every call: connector must emit
        // it once and then dedupe subsequent calls.
        #[derive(Debug)]
        struct EchoProvider(ConnectorKind);
        impl ChangesProvider for EchoProvider {
            fn fetch(
                &self,
                _: u64,
            ) -> Pin<Box<dyn Future<Output = Result<Vec<Change>, ConnectorError>> + Send + '_>>
            {
                let id = format!("{:?}:always", self.0);
                let source = self.0;
                Box::pin(async move {
                    Ok(vec![Change {
                        id,
                        source,
                    }])
                })
            }
        }

        let connector = PlaneConnector::with_provider(EchoProvider(ConnectorKind::Plane));
        let first = block_on(connector.fetch_changes()).unwrap();
        let second = block_on(connector.fetch_changes()).unwrap();
        let third = block_on(connector.fetch_changes()).unwrap();

        assert_eq!(first.len(), 1);
        assert!(second.is_empty(), "duplicate id must not be re-emitted");
        assert!(third.is_empty());
    }

    #[test]
    fn sequence_provider_remaining_tracks_consumption() {
        let provider = SequenceChangesProvider::with_length(ConnectorKind::GitHub, 2);
        assert_eq!(provider.remaining(), 2);
        let _ = block_on(provider.fetch(0));
        assert_eq!(provider.remaining(), 1);
        let _ = block_on(provider.fetch(0));
        assert_eq!(provider.remaining(), 0);
        assert!(block_on(provider.fetch(0)).unwrap().is_empty());
    }
}
