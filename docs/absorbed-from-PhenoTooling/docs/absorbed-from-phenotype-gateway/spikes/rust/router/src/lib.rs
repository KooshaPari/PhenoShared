// SPDX-License-Identifier: MIT OR Apache-2.0
//
//! Router plane trait sketch — Wave H13/H10 spike.
//! HTTP `/v1/*` delegates to cliproxy++ (Go); combo logic stays here.
//!
//! Configuration (paths, delegate targets, scoring profiles) is loaded from
//! the [`phenotype_config`] crate — see [`RouterConfig`] for defaults.

pub mod delegate;

use phenotype_config::RouterConfig;

/// Routing strategy for auto-combo variants (subset of OmniRoute spec).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ComboVariant {
    Auto,
    Coding,
    Fast,
    Cheap,
    Offline,
    Smart,
}

impl ComboVariant {
    /// Parse a model ID string into a combo variant.
    ///
    /// Returns `None` for non-"auto" prefixed IDs (direct model routes).
    pub fn parse(model_id: &str) -> Option<Self> {
        let suffix = model_id.strip_prefix("auto")?;
        match suffix {
            "" | "/" => Some(Self::Auto),
            "/coding" => Some(Self::Coding),
            "/fast" => Some(Self::Fast),
            "/cheap" => Some(Self::Cheap),
            "/offline" => Some(Self::Offline),
            "/smart" => Some(Self::Smart),
            _ => None,
        }
    }

    /// Return the delegate target name for this variant, resolved from config.
    pub fn delegate_target(&self, cfg: &RouterConfig) -> &str {
        match self {
            Self::Auto | Self::Coding | Self::Smart => &cfg.delegates.quality,
            Self::Fast => &cfg.delegates.latency,
            Self::Cheap => &cfg.delegates.cost,
            Self::Offline => &cfg.delegates.quota,
        }
    }
}

pub trait RouterPlane {
    fn select_route(&self, model_id: &str) -> Option<String>;
}

pub struct ComboRouter {
    /// Router configuration.
    pub config: RouterConfig,
}

impl ComboRouter {
    #[must_use]
    pub fn new(config: RouterConfig) -> Self {
        Self { config }
    }
}

impl RouterPlane for ComboRouter {
    fn select_route(&self, model_id: &str) -> Option<String> {
        ComboVariant::parse(model_id)
            .map(|v| v.delegate_target(&self.config).into())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use phenotype_config::GatewayConfig;

    fn test_config() -> RouterConfig {
        GatewayConfig::default().router
    }

    #[test]
    fn auto_variants_delegate() {
        let r = ComboRouter::new(test_config());
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
        let r = ComboRouter::new(test_config());
        assert!(r.select_route("gpt-4").is_none());
        assert!(r.select_route("auto/unknown").is_none());
    }

    #[test]
    fn variant_targets_use_config_defaults() {
        let cfg = test_config();
        assert_eq!(
            ComboVariant::Coding.delegate_target(&cfg),
            "cliproxy-delegate-quality"
        );
        assert_eq!(
            ComboVariant::Fast.delegate_target(&cfg),
            "cliproxy-delegate-latency"
        );
    }
}
