//! Phenotype router plane — HTTP delegate to cliproxy (H11).
//!
//! Absorbed from `phenotype-gateway/spikes/rust/router` (Wave H13/H10 spike).
//! `ComboVariant` routing for the six auto-combo variants; `/v1/*` HTTP
//! delegate to cliproxy++ (Go plane). Combo scoring stays in Rust.

pub mod alias;
pub mod delegate;
pub mod multimodal;
pub mod rate_limit;
pub mod sse;

use std::fmt;

/// Routing strategy for auto-combo variants (subset of OmniRoute spec).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ComboVariant {
    /// Bare "auto" alias — quality-weighted coder.
    Auto,
    /// Default coder (quality-weighted).
    Coding,
    /// Latency-weighted.
    Fast,
    /// Cost-weighted.
    Cheap,
    /// Local-only (offline).
    Offline,
    /// Top-of-graph (capability-weighted).
    Smart,
}

impl ComboVariant {
    pub fn parse(model_id: &str) -> Option<Self> {
        match model_id {
            "auto" => Some(Self::Auto),
            "auto/" => Some(Self::Auto),
            "auto/coding" => Some(Self::Coding),
            "auto/fast" => Some(Self::Fast),
            "auto/cheap" => Some(Self::Cheap),
            "auto/offline" => Some(Self::Offline),
            "auto/smart" => Some(Self::Smart),
            _ => None,
        }
    }

    /// Upstream profile tag used by cliproxy to pick a provider pool.
    pub fn delegate_target(self) -> &'static str {
        match self {
            Self::Auto | Self::Coding => "cliproxy-delegate-quality",
            Self::Fast => "cliproxy-delegate-latency",
            Self::Cheap => "cliproxy-delegate-cost",
            Self::Offline => "cliproxy-delegate-local",
            Self::Smart => "cliproxy-delegate-frontier",
        }
    }
}

impl fmt::Display for ComboVariant {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(match self {
            Self::Auto => "auto",
            Self::Coding => "auto/coding",
            Self::Fast => "auto/fast",
            Self::Cheap => "auto/cheap",
            Self::Offline => "auto/offline",
            Self::Smart => "auto/smart",
        })
    }
}

/// Minimal route resolver — spike scope; H12 replaces with full request router.
pub trait Router {
    fn select_route(&self, model_id: &str) -> Option<ComboVariant>;
}

pub struct ComboRouter;

impl Router for ComboRouter {
    fn select_route(&self, model_id: &str) -> Option<ComboVariant> {
        ComboVariant::parse(model_id)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn auto_variants_delegate() {
        let r = ComboRouter;
        for id in [
            "auto",
            "auto/",
            "auto/coding",
            "auto/fast",
            "auto/cheap",
            "auto/offline",
            "auto/smart",
        ] {
            assert!(r.select_route(id).is_some(), "expected route for {id}");
        }
    }

    #[test]
    fn non_auto_returns_none() {
        let r = ComboRouter;
        assert!(r.select_route("gpt-4").is_none());
        assert!(r.select_route("auto/unknown").is_none());
    }

    #[test]
    fn variant_targets() {
        assert_eq!(
            ComboVariant::Coding.delegate_target(),
            "cliproxy-delegate-quality"
        );
        assert_eq!(
            ComboVariant::Fast.delegate_target(),
            "cliproxy-delegate-latency"
        );
    }
}
