//! Plugin system for pareto-rs.
//!
//! Provides trait-based extensibility for cost calculation, pricing book
//! management, and provider routing. Plugins are registered in a global
//! registry and invoked at well-defined hook points.

use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};

pub type PluginId = String;

pub type HookPoint = &'static str;
pub const HOOK_PRE_COST: &str = "pre_cost";
pub const HOOK_POST_COST: &str = "post_cost";
pub const HOOK_PRE_ROUTE: &str = "pre_route";
pub const HOOK_POST_ROUTE: &str = "post_route";
pub const HOOK_PRICE_BOOK_LOAD: &str = "price_book_load";

pub type PluginResult<T> = Result<T, PluginError>;

#[derive(Debug)]
pub enum PluginError {
    InvalidData(PluginId, String),
    ExecutionFailed(PluginId, String),
    NotFound(PluginId),
}

impl std::fmt::Display for PluginError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            PluginError::InvalidData(id, msg) => {
                write!(f, "plugin {} returned invalid data: {}", id, msg)
            }
            PluginError::ExecutionFailed(id, msg) => write!(f, "plugin {} failed: {}", id, msg),
            PluginError::NotFound(id) => write!(f, "plugin {} not found in registry", id),
        }
    }
}

impl std::error::Error for PluginError {}

#[derive(Debug, Clone)]
pub struct HookCall {
    pub plugin_id: PluginId,
    pub hook_point: HookPoint,
    pub duration_micros: u128,
    pub success: bool,
}

pub trait Plugin: Send + Sync {
    fn id(&self) -> PluginId;
    fn version(&self) -> &str;
    fn hook_points(&self) -> Vec<HookPoint>;

    fn pre_cost(&self, _provider: &str, _model: &str, _input_tokens: u64, _output_tokens: u64) {}
    fn post_cost(
        &self,
        _provider: &str,
        _model: &str,
        _input_tokens: u64,
        _output_tokens: u64,
        _cost: f64,
    ) {
    }
    fn pre_route(&self, _criteria: &str, _max_price: Option<f64>) {}
    fn post_route(&self, _criteria: &str, _selected_model: &str, _price: f64) {}
    fn price_book_load(&self, _book_id: &str, _model_count: usize) {}
}

pub struct LoggingPlugin {
    pub calls: Mutex<Vec<HookCall>>,
}

impl LoggingPlugin {
    pub fn new() -> Self {
        Self {
            calls: Mutex::new(Vec::new()),
        }
    }
    pub fn record(&self, call: HookCall) {
        self.calls.lock().unwrap().push(call);
    }
    pub fn history(&self) -> Vec<HookCall> {
        self.calls.lock().unwrap().clone()
    }
    pub fn clear(&self) {
        self.calls.lock().unwrap().clear();
    }
}

impl Default for LoggingPlugin {
    fn default() -> Self {
        Self::new()
    }
}

impl Plugin for LoggingPlugin {
    fn id(&self) -> PluginId {
        "logging".into()
    }
    fn version(&self) -> &str {
        "0.1.0"
    }
    fn hook_points(&self) -> Vec<HookPoint> {
        vec![
            HOOK_PRE_COST,
            HOOK_POST_COST,
            HOOK_PRE_ROUTE,
            HOOK_POST_ROUTE,
            HOOK_PRICE_BOOK_LOAD,
        ]
    }
}

pub struct BudgetPlugin {
    pub limits: Mutex<HashMap<String, f64>>,
    pub spend: Mutex<HashMap<String, f64>>,
}

impl BudgetPlugin {
    pub fn new() -> Self {
        Self {
            limits: Mutex::new(HashMap::new()),
            spend: Mutex::new(HashMap::new()),
        }
    }
    pub fn set_limit(&self, provider: &str, limit: f64) {
        self.limits.lock().unwrap().insert(provider.into(), limit);
    }
    pub fn spend(&self, provider: &str) -> f64 {
        *self.spend.lock().unwrap().get(provider).unwrap_or(&0.0)
    }
    pub fn remaining(&self, provider: &str) -> f64 {
        let limit = self
            .limits
            .lock()
            .unwrap()
            .get(provider)
            .copied()
            .unwrap_or(0.0);
        limit - self.spend(provider)
    }
    pub fn total_spend(&self) -> f64 {
        self.spend.lock().unwrap().values().sum()
    }
    pub fn total_limit(&self) -> f64 {
        self.limits.lock().unwrap().values().sum()
    }
}

impl Default for BudgetPlugin {
    fn default() -> Self {
        Self::new()
    }
}

impl Plugin for BudgetPlugin {
    fn id(&self) -> PluginId {
        "budget".into()
    }
    fn version(&self) -> &str {
        "0.1.0"
    }
    fn hook_points(&self) -> Vec<HookPoint> {
        vec![HOOK_POST_COST]
    }

    fn post_cost(&self, provider: &str, _model: &str, _input: u64, _output: u64, cost: f64) {
        let mut binding = self.spend.lock().unwrap();
        let entry = binding.entry(provider.into()).or_insert(0.0);
        *entry += cost;
    }
}

#[derive(Debug, Clone)]
pub struct TimelineEvent {
    pub timestamp_millis: u128,
    pub provider: String,
    pub model: String,
    pub input_tokens: u64,
    pub output_tokens: u64,
    pub cost: f64,
}

pub struct TimelinePlugin {
    pub events: Mutex<Vec<TimelineEvent>>,
}

impl TimelinePlugin {
    pub fn new() -> Self {
        Self {
            events: Mutex::new(Vec::new()),
        }
    }
    pub fn snapshot(&self) -> Vec<TimelineEvent> {
        self.events.lock().unwrap().clone()
    }
    pub fn clear(&self) {
        self.events.lock().unwrap().clear();
    }
    pub fn total_cost(&self) -> f64 {
        self.events.lock().unwrap().iter().map(|e| e.cost).sum()
    }
    pub fn total_tokens(&self) -> u64 {
        self.events
            .lock()
            .unwrap()
            .iter()
            .map(|e| e.input_tokens + e.output_tokens)
            .sum()
    }
    pub fn len(&self) -> usize {
        self.events.lock().unwrap().len()
    }
    pub fn is_empty(&self) -> bool {
        self.events.lock().unwrap().is_empty()
    }
}

impl Default for TimelinePlugin {
    fn default() -> Self {
        Self::new()
    }
}

impl Plugin for TimelinePlugin {
    fn id(&self) -> PluginId {
        "timeline".into()
    }
    fn version(&self) -> &str {
        "0.1.0"
    }
    fn hook_points(&self) -> Vec<HookPoint> {
        vec![HOOK_POST_COST]
    }

    fn post_cost(&self, provider: &str, model: &str, input: u64, output: u64, cost: f64) {
        let ev = TimelineEvent {
            timestamp_millis: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|d| d.as_millis())
                .unwrap_or(0),
            provider: provider.into(),
            model: model.into(),
            input_tokens: input,
            output_tokens: output,
            cost,
        };
        self.events.lock().unwrap().push(ev);
    }
}

pub struct PluginRegistry {
    plugins: Mutex<Vec<Arc<dyn Plugin>>>,
}

impl PluginRegistry {
    pub fn new() -> Self {
        Self {
            plugins: Mutex::new(Vec::new()),
        }
    }

    pub fn register(&self, plugin: Arc<dyn Plugin>) {
        self.plugins.lock().unwrap().push(plugin);
    }

    pub fn unregister(&self, id: &str) -> bool {
        let mut plugins = self.plugins.lock().unwrap();
        let pos = plugins.iter().position(|p| p.id() == id);
        if let Some(i) = pos {
            plugins.remove(i);
            true
        } else {
            false
        }
    }

    pub fn get(&self, id: &str) -> Option<Arc<dyn Plugin>> {
        self.plugins
            .lock()
            .unwrap()
            .iter()
            .find(|p| p.id() == id)
            .cloned()
    }

    pub fn list(&self) -> Vec<PluginId> {
        self.plugins
            .lock()
            .unwrap()
            .iter()
            .map(|p| p.id())
            .collect()
    }

    pub fn count(&self) -> usize {
        self.plugins.lock().unwrap().len()
    }

    pub fn invoke_pre_cost(&self, provider: &str, model: &str, input: u64, output: u64) {
        for p in self.plugins.lock().unwrap().iter() {
            p.pre_cost(provider, model, input, output);
        }
    }

    pub fn invoke_post_cost(
        &self,
        provider: &str,
        model: &str,
        input: u64,
        output: u64,
        cost: f64,
    ) {
        for p in self.plugins.lock().unwrap().iter() {
            p.post_cost(provider, model, input, output, cost);
        }
    }

    pub fn invoke_pre_route(&self, criteria: &str, max_price: Option<f64>) {
        for p in self.plugins.lock().unwrap().iter() {
            p.pre_route(criteria, max_price);
        }
    }

    pub fn invoke_post_route(&self, criteria: &str, model: &str, price: f64) {
        for p in self.plugins.lock().unwrap().iter() {
            p.post_route(criteria, model, price);
        }
    }

    pub fn invoke_price_book_load(&self, book_id: &str, count: usize) {
        for p in self.plugins.lock().unwrap().iter() {
            p.price_book_load(book_id, count);
        }
    }
}

impl Default for PluginRegistry {
    fn default() -> Self {
        Self::new()
    }
}

pub fn default_registry() -> PluginRegistry {
    let r = PluginRegistry::new();
    r.register(Arc::new(LoggingPlugin::new()));
    r.register(Arc::new(BudgetPlugin::new()));
    r.register(Arc::new(TimelinePlugin::new()));
    r
}

#[cfg(test)]
mod tests {
    use super::*;

    #[derive(Default)]
    struct RecordingPlugin {
        calls: Mutex<Vec<String>>,
    }

    impl RecordingPlugin {
        fn calls(&self) -> Vec<String> {
            self.calls.lock().unwrap().clone()
        }

        fn record(&self, call: String) {
            self.calls.lock().unwrap().push(call);
        }
    }

    impl Plugin for RecordingPlugin {
        fn id(&self) -> PluginId {
            "recording".into()
        }

        fn version(&self) -> &str {
            "test"
        }

        fn hook_points(&self) -> Vec<HookPoint> {
            vec![
                HOOK_PRE_COST,
                HOOK_PRE_ROUTE,
                HOOK_POST_ROUTE,
                HOOK_PRICE_BOOK_LOAD,
            ]
        }

        fn pre_cost(&self, provider: &str, model: &str, input: u64, output: u64) {
            self.record(format!("pre_cost:{provider}:{model}:{input}:{output}"));
        }

        fn pre_route(&self, criteria: &str, max_price: Option<f64>) {
            self.record(format!("pre_route:{criteria}:{max_price:?}"));
        }

        fn post_route(&self, criteria: &str, model: &str, price: f64) {
            self.record(format!("post_route:{criteria}:{model}:{price}"));
        }

        fn price_book_load(&self, book_id: &str, model_count: usize) {
            self.record(format!("price_book_load:{book_id}:{model_count}"));
        }
    }

    #[test]
    fn default_registry_has_three_plugins() {
        let r = default_registry();
        assert_eq!(r.count(), 3);
        assert!(r.get("logging").is_some());
        assert!(r.get("budget").is_some());
        assert!(r.get("timeline").is_some());
    }

    #[test]
    fn budget_plugin_tracks_spend() {
        let p = BudgetPlugin::new();
        p.set_limit("openai", 100.0);
        assert_eq!(p.remaining("openai"), 100.0);
        p.post_cost("openai", "gpt-4o", 1000, 500, 4.0);
        assert!((p.spend("openai") - 4.0).abs() < f64::EPSILON);
        assert!((p.remaining("openai") - 96.0).abs() < f64::EPSILON);
    }

    #[test]
    fn budget_plugin_aggregates_totals() {
        let p = BudgetPlugin::new();
        p.set_limit("openai", 100.0);
        p.set_limit("anthropic", 200.0);
        p.post_cost("openai", "gpt-4o", 1, 1, 5.0);
        p.post_cost("anthropic", "claude", 1, 1, 10.0);
        assert!((p.total_spend() - 15.0).abs() < f64::EPSILON);
        assert!((p.total_limit() - 300.0).abs() < f64::EPSILON);
    }

    #[test]
    fn built_in_plugin_metadata_matches_declared_hooks() {
        let logging = LoggingPlugin::new();
        assert_eq!(logging.version(), "0.1.0");
        assert_eq!(
            logging.hook_points(),
            vec![
                HOOK_PRE_COST,
                HOOK_POST_COST,
                HOOK_PRE_ROUTE,
                HOOK_POST_ROUTE,
                HOOK_PRICE_BOOK_LOAD,
            ]
        );

        let budget = BudgetPlugin::new();
        assert_eq!(budget.version(), "0.1.0");
        assert_eq!(budget.hook_points(), vec![HOOK_POST_COST]);

        let timeline = TimelinePlugin::new();
        assert_eq!(timeline.version(), "0.1.0");
        assert_eq!(timeline.hook_points(), vec![HOOK_POST_COST]);
    }

    #[test]
    fn timeline_plugin_records_events() {
        let p = TimelinePlugin::new();
        p.post_cost("anthropic", "claude-3-haiku", 100, 50, 0.005);
        p.post_cost("openai", "gpt-4o", 200, 100, 0.01);
        let snap = p.snapshot();
        assert_eq!(snap.len(), 2);
        assert!((p.total_cost() - 0.015).abs() < 1e-9);
        assert_eq!(p.total_tokens(), 450);
    }

    #[test]
    fn timeline_plugin_clear_works() {
        let p = TimelinePlugin::new();
        assert_eq!(p.len(), 0);
        assert!(p.is_empty());
        p.post_cost("openai", "gpt-4o", 1, 1, 0.01);
        assert_eq!(p.len(), 1);
        assert!(!p.is_empty());
        p.clear();
        assert_eq!(p.len(), 0);
        assert!(p.is_empty());
    }

    #[test]
    fn logging_plugin_records_history() {
        let p = LoggingPlugin::new();
        p.record(HookCall {
            plugin_id: "x".into(),
            hook_point: HOOK_PRE_COST,
            duration_micros: 10,
            success: true,
        });
        assert_eq!(p.history().len(), 1);
        p.clear();
        assert!(p.history().is_empty());
    }

    #[test]
    fn registry_lookup_and_list_preserve_registered_plugin_identity() {
        let r = PluginRegistry::new();
        r.register(Arc::new(LoggingPlugin::new()));
        r.register(Arc::new(BudgetPlugin::new()));

        assert_eq!(r.list(), vec!["logging", "budget"]);
        assert_eq!(
            r.get("logging").map(|plugin| plugin.id()),
            Some("logging".into())
        );
        assert!(r.get("missing").is_none());
    }

    #[test]
    fn registry_dispatches_each_non_cost_hook_with_its_arguments() {
        let r = PluginRegistry::new();
        let recording = Arc::new(RecordingPlugin::default());
        r.register(recording.clone());

        r.invoke_pre_cost("openai", "gpt-4o", 11, 7);
        r.invoke_pre_route("lowest-cost", Some(2.5));
        r.invoke_post_route("lowest-cost", "gpt-4o-mini", 0.15);
        r.invoke_price_book_load("2026-08", 42);

        assert_eq!(
            recording.calls(),
            vec![
                "pre_cost:openai:gpt-4o:11:7",
                "pre_route:lowest-cost:Some(2.5)",
                "post_route:lowest-cost:gpt-4o-mini:0.15",
                "price_book_load:2026-08:42",
            ]
        );
    }

    #[test]
    fn registry_invokes_all_listeners() {
        let r = PluginRegistry::new();
        let budget = Arc::new(BudgetPlugin::new());
        let timeline = Arc::new(TimelinePlugin::new());
        budget.set_limit("openai", 100.0);
        r.register(budget.clone());
        r.register(timeline.clone());

        r.invoke_post_cost("openai", "gpt-4o", 1000, 500, 5.0);
        assert!((budget.spend("openai") - 5.0).abs() < f64::EPSILON);
        assert_eq!(timeline.snapshot().len(), 1);
    }

    #[test]
    fn registry_unregister_works() {
        let r = default_registry();
        assert_eq!(r.count(), 3);
        assert!(r.unregister("logging"));
        assert_eq!(r.count(), 2);
        assert!(!r.unregister("nonexistent"));
    }

    #[test]
    fn plugin_error_display() {
        let e = PluginError::InvalidData("foo".into(), "bad".into());
        assert!(format!("{}", e).contains("bad"));
    }
}
