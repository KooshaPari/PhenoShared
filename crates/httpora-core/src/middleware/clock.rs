use std::sync::Arc;
use std::time::Instant;

/// Shared clock function used by time-dependent middleware.
pub type Clock = Arc<dyn Fn() -> Instant + Send + Sync>;

pub fn system_clock() -> Clock {
    Arc::new(Instant::now)
}
