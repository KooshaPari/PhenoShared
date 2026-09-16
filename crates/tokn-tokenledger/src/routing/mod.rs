//! Hexagonal Architecture: Ports and Adapters for Routing Orchestration
//!
//! This module implements the "donut" layer around the harness, providing:
//! - Ports (interfaces/traits) for benchmark data
//! - Adapters for each system (CLIProxyAPI, HeliosHarness, thegent, agentapi)
//! - Provider-Harness-Model trio resolution
//! - Pareto scoring based on unified data
//!
//! Architecture:
//! ```text
//! ┌─────────────────────────────────────────────────────────┐
//! │              ROUTING ORCHESTRATION LAYER              │
//! │                                                      │
//! │   ┌─────────────────────────────────────────────┐    │
//! │   │              PORTS (Traits)                │    │
//! │   │  • BenchmarkPort                            │    │
//! │   │  • MetricsPort                             │    │
//! │   │  • RoutingPort                            │    │
//! │   │  • ModelMappingPort                       │    │
//! │   └─────────────────────────────────────────────┘    │
//! │                    ▲                               │
//! │                    │                               │
//! │   ┌───────────────┴───────────────┐              │
//! │   │         ADAPTERS              │              │
//! │   ├──────────────────────────────┤              │
//! │   │ • CLIProxyAdapter          │              │
//! │   │ • HeliosHarnessAdapter    │              │
//! │   │ • ThegentAdapter         │              │
//! │   │ • AgentAPIAdapter        │              │
//! │   │ • OpenRouterAdapter      │              │
//! │   │ • ArtificialAnalysisAdapt│              │
//! │   └──────────────────────────────┘              │
//! └─────────────────────────────────────────────────────────┘
//! ```

pub mod adapters;
pub mod mappings;
pub mod pareto_frontier;
pub mod pareto_router;
pub mod ports;

// Re-exports for convenience
pub use adapters::{
    AgentAPIAdapter, CLIProxyAdapter, HeliosHarnessAdapter, ThegentRoutingAdapter, UnifiedAdapter,
};
pub use mappings::resolve_trio;
pub use pareto_frontier::{
    ParetoCombo, ParetoObjective, ParetoOffer, ParetoResult, compute_combos, compute_pareto,
    pareto_front_mask,
};
pub use pareto_router::ParetoRouter;
pub use ports::{
    BenchmarkPort, MetricsPort, ModelMapping, ModelMappingPort, PortError, PortResult,
    ProviderHarnessModel, RoutingAlternative, RoutingCriteria, RoutingDecision, RoutingPort,
    TrioPort,
};
