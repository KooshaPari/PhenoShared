// SPDX-License-Identifier: MIT OR Apache-2.0
//
//! HTTP delegate design — router revamp forwards `/v1/*` to cliproxy++ (Go plane).
//!
//! Paths, targets, and scoring profiles are resolved from [`phenotype_config::RouterConfig`]
//! rather than hardcoded.

use phenotype_config::RouterConfig;

/// Resolved upstream target for a combo route.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DelegateRequest {
    pub target: String,
    pub path: String,
    pub variant: super::ComboVariant,
}

/// Build cliproxy delegate URL from config + model ID.
pub fn build_delegate_request(
    cfg: &RouterConfig,
    model_id: &str,
) -> Option<DelegateRequest> {
    let variant = super::ComboVariant::parse(model_id)?;
    let base = cfg.cliproxy_base_url.trim_end_matches('/');
    let chat_path = &cfg.paths.chat_completions;
    Some(DelegateRequest {
        target: format!("{base}{chat_path}"),
        path: chat_path.clone(),
        variant,
    })
}

/// Map delegate target name to scoring profile query param using config.
pub fn scoring_profile<'a>(cfg: &'a RouterConfig, target: &str) -> Option<&'a str> {
    if target == cfg.delegates.quality {
        Some(&cfg.scoring_profiles.quality)
    } else if target == cfg.delegates.latency {
        Some(&cfg.scoring_profiles.latency)
    } else if target == cfg.delegates.cost {
        Some(&cfg.scoring_profiles.cost)
    } else if target == cfg.delegates.quota {
        Some(&cfg.scoring_profiles.quota)
    } else {
        None
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
    fn builds_chat_completions_delegate_url() {
        let cfg = test_config();
        let req = build_delegate_request(&cfg, "auto/coding").unwrap();
        assert_eq!(req.target, "http://127.0.0.1:8317/v1/chat/completions");
        assert_eq!(req.path, "/v1/chat/completions");
        assert_eq!(req.variant, super::super::ComboVariant::Coding);
    }

    #[test]
    fn scoring_profiles_map_from_config() {
        let cfg = test_config();
        assert_eq!(scoring_profile(&cfg, "cliproxy-delegate-latency"), Some("latency"));
        assert_eq!(scoring_profile(&cfg, "unknown"), None);
    }
}
