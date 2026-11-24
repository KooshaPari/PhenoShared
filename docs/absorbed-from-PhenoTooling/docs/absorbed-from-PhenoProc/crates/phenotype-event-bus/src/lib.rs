//! Phenotype event bus library

pub struct EventBus;

impl EventBus {
    pub fn new() -> Self {
        Self
    }
}

impl Default for EventBus {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn new_creates_event_bus() {
        let _ = EventBus::new();
    }

    #[test]
    fn default_matches_new() {
        let a: EventBus = EventBus::default();
        let b = EventBus::new();
        let _ = (a, b);
    }
}
