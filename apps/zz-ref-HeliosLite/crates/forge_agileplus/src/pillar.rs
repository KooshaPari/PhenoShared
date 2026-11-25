//! The 31 engineering pillars that compose the AgilePlus scorecard.
//!
//! The list is derived 1:1 from `docs/31-pillar-scorecard.md` (HeliosLite
//! forgecode, audit date 2026-09-01). Variant order **is** the canonical
//! pillar index — `Pillar::ProjectStructure` is pillar #1 and
//! `Pillar::DisasterRecovery` is pillar #31.
//!
//! Each pillar carries a [`Score`] in the closed range `0..=10` and a
//! per-pillar [`Pillar::target_threshold`] (all 8.0 in the current
//! scorecard spec).

use serde::{Deserialize, Serialize};

/// A pillar score in the closed range `0..=10`.
#[derive(Debug, Clone, Copy, PartialEq, PartialOrd, Serialize, Deserialize)]
pub struct Score(pub f32);

impl Score {
    /// Minimum valid score.
    pub const MIN: f32 = 0.0;
    /// Maximum valid score.
    pub const MAX: f32 = 10.0;

    /// Construct a new score. Returns `None` if the score is outside
    /// `0..=10` or non-finite.
    pub fn new(value: f32) -> Option<Self> {
        if value.is_finite() && (Self::MIN..=Self::MAX).contains(&value) {
            Some(Self(value))
        } else {
            None
        }
    }

    /// Wrap as `Score` (clamped into the valid range). Used by helpers
    /// that already know the input should be a score.
    pub fn clamped(value: f32) -> Self {
        let v = if value.is_finite() {
            value.clamp(Self::MIN, Self::MAX)
        } else {
            Self::MIN
        };
        Self(v)
    }

    /// Raw score value.
    pub fn value(self) -> f32 {
        self.0
    }
}

/// The 31 engineering pillars tracked by the AgilePlus scorecard.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Pillar {
    /// #1 — hexagonal workspace boundary enforcement.
    ProjectStructure,
    /// #2 — GitHub Actions pipelines with SLSA L2 provenance.
    CiCd,
    /// #3 — test files, snapshot + fuzz coverage.
    Testing,
    /// #4 — clippy / rustfmt gates in CI.
    Linting,
    /// #5 — cargo-deny, TruffleHog, CodeQL, Gitleaks, Dependabot.
    Security,
    /// #6 — feature-request catalog, threat model, README, edition consistency.
    Documentation,
    /// #7 — compile-time type safety, serde, thiserror.
    TypeSafety,
    /// #8 — TUI screen-reader support, keyboard navigation.
    Accessibility,
    /// #9 — string externalization with `rust-i18n` / `fluent`.
    I18n,
    /// #10 — PostHog + `tracing` + OTel pipeline maturity.
    Observability,
    /// #11 — Python chaos suite + Rust integration fault injection.
    ChaosEngineering,
    /// #12 — burn-rate monitor + DORA metrics pipeline.
    SloSli,
    /// #13 — Terraform for AWS regions, state in S3 + DynamoDB.
    Iac,
    /// #14 — distroless production Dockerfile, multi-arch builds.
    Containerization,
    /// #15 — Diesel migrations, SQLite FTS5, r2d2 pooling.
    Database,
    /// #16 — port boundary interfaces + OpenAPI / JSON Schema publication.
    ApiDesign,
    /// #17 — thiserror enums, retry taxonomy, circuit breakers, bulkheads.
    ErrorHandling,
    /// #18 — cargo-deny, Dependabot, Renovate, `Cargo.lock` reproducibility.
    DependencyManagement,
    /// #19 — `cargo-llvm-cov` + Codecov with PR delta comments.
    CodeCoverage,
    /// #20 — Criterion benchmarks, perf-regression CI gate.
    Performance,
    /// #21 — Prometheus / Jaeger / Grafana stack wiring in production.
    Monitoring,
    /// #22 — PR template, CODEOWNERS, required reviews.
    CodeReview,
    /// #23 — approval + signed commits + status checks.
    BranchProtection,
    /// #24 — 5-layer pipeline (build → test → scan → sign → publish), 9 platforms.
    ReleaseManagement,
    /// #25 — 16+ infra traits + 20+ service traits for adapter substitution.
    DependencyInjection,
    /// #26 — `tracing-subscriber` JSON, dual-mode writer, span propagation.
    Logging,
    /// #27 — `cacache`, TTL, `LazyLock` singletons.
    Caching,
    /// #28 — token-bucket rate limiting for LLM / API calls.
    RateLimiting,
    /// #29 — OAuth (GitHub / GitLab), policy engine, `keyring` storage.
    AuthAuthz,
    /// #30 — 5-layer config stack: defaults → file → env → CLI → programmatic.
    ConfigManagement,
    /// #31 — backup / restore, RTO / RPO definition, runbook.
    DisasterRecovery,
}

impl Pillar {
    /// Total number of pillars in the scorecard. Always 31.
    pub const COUNT: usize = 31;
    /// Per-pillar target threshold (matches `docs/31-pillar-scorecard.md`,
    /// target 8.0/10 across the scorecard).
    pub const TARGET_THRESHOLD: f32 = 8.0;

    /// Every pillar in canonical scorecard order (1..=31).
    pub fn all() -> [Pillar; Self::COUNT] {
        [
            Pillar::ProjectStructure,
            Pillar::CiCd,
            Pillar::Testing,
            Pillar::Linting,
            Pillar::Security,
            Pillar::Documentation,
            Pillar::TypeSafety,
            Pillar::Accessibility,
            Pillar::I18n,
            Pillar::Observability,
            Pillar::ChaosEngineering,
            Pillar::SloSli,
            Pillar::Iac,
            Pillar::Containerization,
            Pillar::Database,
            Pillar::ApiDesign,
            Pillar::ErrorHandling,
            Pillar::DependencyManagement,
            Pillar::CodeCoverage,
            Pillar::Performance,
            Pillar::Monitoring,
            Pillar::CodeReview,
            Pillar::BranchProtection,
            Pillar::ReleaseManagement,
            Pillar::DependencyInjection,
            Pillar::Logging,
            Pillar::Caching,
            Pillar::RateLimiting,
            Pillar::AuthAuthz,
            Pillar::ConfigManagement,
            Pillar::DisasterRecovery,
        ]
    }

    /// 1-based pillar ordinal (matches the #N headers in the scorecard doc).
    pub fn ordinal(self) -> usize {
        // Safe: `Pillar::all()` is a `[Pillar; 31]` with one of each variant.
        Pillar::all()
            .iter()
            .position(|p| *p == self)
            .expect("Pillar variant is in Pillar::all()")
            + 1
    }

    /// Per-pillar target threshold (currently identical for all pillars;
    /// kept on the enum so future per-pillar targets can be added without
    /// changing callers).
    pub fn target_threshold(self) -> f32 {
        Self::TARGET_THRESHOLD
    }

    /// Human-readable display name.
    pub fn display_name(self) -> &'static str {
        match self {
            Pillar::ProjectStructure => "Project Structure",
            Pillar::CiCd => "CI/CD",
            Pillar::Testing => "Testing",
            Pillar::Linting => "Linting",
            Pillar::Security => "Security",
            Pillar::Documentation => "Documentation",
            Pillar::TypeSafety => "Type Safety",
            Pillar::Accessibility => "Accessibility",
            Pillar::I18n => "Internationalization (i18n)",
            Pillar::Observability => "Observability",
            Pillar::ChaosEngineering => "Chaos Engineering",
            Pillar::SloSli => "SLO/SLI",
            Pillar::Iac => "Infrastructure as Code (IaC)",
            Pillar::Containerization => "Containerization",
            Pillar::Database => "Database",
            Pillar::ApiDesign => "API Design",
            Pillar::ErrorHandling => "Error Handling",
            Pillar::DependencyManagement => "Dependency Management",
            Pillar::CodeCoverage => "Code Coverage",
            Pillar::Performance => "Performance",
            Pillar::Monitoring => "Monitoring",
            Pillar::CodeReview => "Code Review",
            Pillar::BranchProtection => "Branch Protection",
            Pillar::ReleaseManagement => "Release Management",
            Pillar::DependencyInjection => "Dependency Injection",
            Pillar::Logging => "Logging",
            Pillar::Caching => "Caching",
            Pillar::RateLimiting => "Rate Limiting",
            Pillar::AuthAuthz => "Auth/AuthZ",
            Pillar::ConfigManagement => "Config Management",
            Pillar::DisasterRecovery => "Disaster Recovery",
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pillar_count_is_31() {
        assert_eq!(Pillar::COUNT, 31);
        assert_eq!(Pillar::all().len(), 31);
    }

    #[test]
    fn score_validation_in_range() {
        for raw in [0.0_f32, 0.001, 5.0, 7.5, 10.0] {
            assert!(Score::new(raw).is_some(), "expected {raw} to validate");
        }
    }

    #[test]
    fn score_validation_rejects_out_of_range() {
        for raw in [-0.01_f32, -1.0, 10.01, 11.0, 100.0] {
            assert!(Score::new(raw).is_none(), "expected {raw} to be rejected");
        }
    }

    #[test]
    fn score_validation_rejects_non_finite() {
        assert!(Score::new(f32::NAN).is_none());
        assert!(Score::new(f32::INFINITY).is_none());
        assert!(Score::new(f32::NEG_INFINITY).is_none());
    }

    #[test]
    fn score_clamped_handles_extremes() {
        assert_eq!(Score::clamped(99.0).value(), 10.0);
        assert_eq!(Score::clamped(-5.0).value(), 0.0);
        assert_eq!(Score::clamped(f32::NAN).value(), 0.0);
    }

    #[test]
    fn all_31_variants_exist() {
        // Defensive: enumerate via debug output. If a variant is ever
        // removed from the enum, this test fails to compile and forces the
        // scorecard module to be revisited.
        for pillar in Pillar::all() {
            let _ = format!("{pillar:?}");
        }
        assert_eq!(Pillar::all().len(), 31);
    }

    #[test]
    fn all_display_names_are_unique() {
        let mut names: Vec<&str> = Pillar::all().iter().map(|p| p.display_name()).collect();
        let original_len = names.len();
        names.sort();
        names.dedup();
        assert_eq!(names.len(), original_len, "display names must be unique");
    }

    #[test]
    fn ordinals_are_one_indexed_and_dense() {
        let ordinals: Vec<usize> = Pillar::all().iter().map(|p| p.ordinal()).collect();
        let expected: Vec<usize> = (1..=31).collect();
        assert_eq!(ordinals, expected);
    }

    #[test]
    fn target_threshold_is_eight_for_every_pillar() {
        for pillar in Pillar::all() {
            assert!((pillar.target_threshold() - 8.0).abs() < f32::EPSILON);
        }
    }

    #[test]
    fn pillar_serialization_roundtrips() {
        for pillar in Pillar::all() {
            let json = serde_json::to_string(&pillar).expect("serialize");
            let back: Pillar = serde_json::from_str(&json).expect("deserialize");
            assert_eq!(back, pillar);
        }
    }
}
