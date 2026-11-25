use std::collections::HashMap;
use std::sync::Mutex;

/// Event types emitted by the cost engine.
#[derive(Debug, Clone, PartialEq)]
pub enum Event {
    CostCalculated {
        request_id: String,
        cost: f64,
        tokens: u64,
    },
    PriceBookLoaded {
        provider: String,
        model_count: usize,
    },
    RouteChosen {
        request_id: String,
        route: String,
        estimated_cost: f64,
    },
    BudgetExceeded {
        user_id: String,
        spent: f64,
        limit: f64,
    },
    LedgerEntry {
        entry_id: String,
        amount: f64,
        description: String,
    },
}

/// Callback type for event subscribers.
pub type EventCallback = Box<dyn Fn(&Event) + Send + Sync>;

/// Trait for event distribution.
pub trait EventBus: Send + Sync {
    fn subscribe(&self, event_type: &str, callback: EventCallback);
    fn publish(&self, event: &Event);
    fn clear(&self);
}

/// In-memory implementation of the EventBus.
pub struct InMemoryEventBus {
    subscribers: Mutex<HashMap<String, Vec<EventCallback>>>,
}

impl InMemoryEventBus {
    pub fn new() -> Self {
        Self {
            subscribers: Mutex::new(HashMap::new()),
        }
    }

    fn get_event_type(event: &Event) -> &'static str {
        match event {
            Event::CostCalculated { .. } => "CostCalculated",
            Event::PriceBookLoaded { .. } => "PriceBookLoaded",
            Event::RouteChosen { .. } => "RouteChosen",
            Event::BudgetExceeded { .. } => "BudgetExceeded",
            Event::LedgerEntry { .. } => "LedgerEntry",
        }
    }
}

impl Default for InMemoryEventBus {
    fn default() -> Self {
        Self::new()
    }
}

impl EventBus for InMemoryEventBus {
    fn subscribe(&self, event_type: &str, callback: EventCallback) {
        let mut subs = self.subscribers.lock().unwrap();
        subs.entry(event_type.to_string())
            .or_default()
            .push(callback);
    }

    fn publish(&self, event: &Event) {
        let event_type = Self::get_event_type(event);
        let subs = self.subscribers.lock().unwrap();

        if let Some(callbacks) = subs.get(event_type) {
            for callback in callbacks {
                callback(event);
            }
        }

        // Also notify wildcard subscribers
        if let Some(callbacks) = subs.get("*") {
            for callback in callbacks {
                callback(event);
            }
        }
    }

    fn clear(&self) {
        let mut subs = self.subscribers.lock().unwrap();
        subs.clear();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;
    use std::sync::atomic::{AtomicUsize, Ordering};

    #[test]
    fn test_event_creation() {
        let event = Event::CostCalculated {
            request_id: "req-123".to_string(),
            cost: 0.05,
            tokens: 1000,
        };
        assert!(matches!(event, Event::CostCalculated { .. }));
    }

    #[test]
    fn test_default_bus_accepts_subscriptions() {
        let bus = InMemoryEventBus::default();
        let counter = Arc::new(AtomicUsize::new(0));
        let counter_clone = counter.clone();
        bus.subscribe(
            "CostCalculated",
            Box::new(move |_| {
                counter_clone.fetch_add(1, Ordering::SeqCst);
            }),
        );

        bus.publish(&Event::CostCalculated {
            request_id: "req-default".to_string(),
            cost: 0.1,
            tokens: 1,
        });

        assert_eq!(counter.load(Ordering::SeqCst), 1);
    }

    #[test]
    fn test_subscribe_and_publish() {
        let bus = InMemoryEventBus::new();
        let counter = Arc::new(AtomicUsize::new(0));
        let counter_clone = counter.clone();

        bus.subscribe(
            "CostCalculated",
            Box::new(move |_| {
                counter_clone.fetch_add(1, Ordering::SeqCst);
            }),
        );

        let event = Event::CostCalculated {
            request_id: "req-1".to_string(),
            cost: 0.1,
            tokens: 500,
        };
        bus.publish(&event);

        assert_eq!(counter.load(Ordering::SeqCst), 1);
    }

    #[test]
    fn test_wildcard_subscriber() {
        let bus = InMemoryEventBus::new();
        let counter = Arc::new(AtomicUsize::new(0));
        let counter_clone = counter.clone();

        bus.subscribe(
            "*",
            Box::new(move |_| {
                counter_clone.fetch_add(1, Ordering::SeqCst);
            }),
        );

        bus.publish(&Event::CostCalculated {
            request_id: "req-1".to_string(),
            cost: 0.1,
            tokens: 100,
        });

        bus.publish(&Event::BudgetExceeded {
            user_id: "user-1".to_string(),
            spent: 100.0,
            limit: 50.0,
        });

        assert_eq!(counter.load(Ordering::SeqCst), 2);
    }

    #[test]
    fn test_multiple_subscribers() {
        let bus = InMemoryEventBus::new();
        let counter = Arc::new(AtomicUsize::new(0));

        for _ in 0..3 {
            let c = counter.clone();
            bus.subscribe(
                "CostCalculated",
                Box::new(move |_| {
                    c.fetch_add(1, Ordering::SeqCst);
                }),
            );
        }

        bus.publish(&Event::CostCalculated {
            request_id: "req-1".to_string(),
            cost: 0.1,
            tokens: 100,
        });

        assert_eq!(counter.load(Ordering::SeqCst), 3);
    }

    #[test]
    fn test_no_subscribers_does_not_panic() {
        let bus = InMemoryEventBus::new();
        bus.publish(&Event::LedgerEntry {
            entry_id: "entry-1".to_string(),
            amount: 10.0,
            description: "Test".to_string(),
        });
    }

    #[test]
    fn test_clear_bus() {
        let bus = InMemoryEventBus::new();
        let counter = Arc::new(AtomicUsize::new(0));
        let c = counter.clone();

        bus.subscribe(
            "CostCalculated",
            Box::new(move |_| {
                c.fetch_add(1, Ordering::SeqCst);
            }),
        );

        bus.publish(&Event::CostCalculated {
            request_id: "req-1".to_string(),
            cost: 0.1,
            tokens: 100,
        });

        bus.clear();

        bus.publish(&Event::CostCalculated {
            request_id: "req-2".to_string(),
            cost: 0.2,
            tokens: 200,
        });

        assert_eq!(counter.load(Ordering::SeqCst), 1);
    }

    #[test]
    fn test_event_type_extraction() {
        let e1 = Event::PriceBookLoaded {
            provider: "openai".to_string(),
            model_count: 5,
        };
        let e2 = Event::RouteChosen {
            request_id: "req-2".to_string(),
            route: "gpt-4".to_string(),
            estimated_cost: 0.5,
        };
        let e3 = Event::BudgetExceeded {
            user_id: "u-1".to_string(),
            spent: 10.0,
            limit: 5.0,
        };

        assert_eq!(InMemoryEventBus::get_event_type(&e1), "PriceBookLoaded");
        assert_eq!(InMemoryEventBus::get_event_type(&e2), "RouteChosen");
        assert_eq!(InMemoryEventBus::get_event_type(&e3), "BudgetExceeded");
    }

    #[test]
    fn test_specific_event_not_triggered() {
        let bus = InMemoryEventBus::new();
        let counter = Arc::new(AtomicUsize::new(0));
        let c = counter.clone();

        bus.subscribe(
            "BudgetExceeded",
            Box::new(move |_| {
                c.fetch_add(1, Ordering::SeqCst);
            }),
        );

        bus.publish(&Event::CostCalculated {
            request_id: "req-1".to_string(),
            cost: 0.1,
            tokens: 100,
        });

        assert_eq!(counter.load(Ordering::SeqCst), 0);
    }

    #[test]
    fn test_event_clone() {
        let event = Event::LedgerEntry {
            entry_id: "L-001".to_string(),
            amount: 25.0,
            description: "Service Fee".to_string(),
        };
        let cloned = event.clone();
        assert_eq!(event, cloned);
    }
}
