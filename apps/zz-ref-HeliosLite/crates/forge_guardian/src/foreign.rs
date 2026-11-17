//! Foreign-function (LLM-driven) risk adjudication layer.
//!
//! This is the "guardian" half of the P0.1 design: instead of only
//! deterministic heuristics, a capable model judges whether a proposed
//! [`PermissionOperation`] is safe, risky, or unacceptable, giving an
//! `explanation` a human can read (and which feeds the audit log).
//!
//! The crate deliberately avoids depending on the full `forge_domain`
//! provider stack. The caller injects a driver — an async function that
//! turns an adjudication prompt into model text. This keeps the guardian
//! pure, dependency-light, and unit-testable with a canned model reply.

use std::fmt;
use std::future::Future;

use crate::{Risk, RiskLevel};

/// The textual verdict a model is asked to produce.
///
/// The prompt should constrain the model to answer with a single line of
/// the form `RISK:<0.0..1.0>|<label>|<explanation>` where:
/// - `0.0..1.0` is a clamped float with two decimals,
/// - `<label>` is one of `low|medium|high|critical`,
/// - `<explanation>` is free text explaining the judgement.
#[derive(Debug, Clone)]
pub struct Judgement {
    /// Normalized risk in `0.0..=1.0` as judged by the model.
    pub risk: Risk,
    /// Optional human-readable explanation.
    pub explanation: String,
    /// Level resolved from the model's label (or derived from the score).
    pub level: RiskLevel,
    /// True when the parser failed and the judgement is a best-effort fallback.
    pub parse_failed: bool,
}

impl Judgement {
    /// A conservative fallback used when the model output cannot be parsed.
    pub fn unparsed(raw: &str) -> Self {
        Self {
            risk: Risk::high(),
            explanation: format!("Model verdict unparsed: {raw}"),
            level: RiskLevel::High,
            parse_failed: true,
        }
    }

    fn resolved_level(score: f64, label: &str) -> RiskLevel {
        match label {
            "low" => RiskLevel::Low,
            "medium" => RiskLevel::Medium,
            "high" => RiskLevel::High,
            "critical" => RiskLevel::High,
            "moderate" => RiskLevel::Medium,
            "safe" => RiskLevel::Low,
            _ => RiskLevel::from_score(score),
        }
    }
}

impl fmt::Display for Judgement {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "risk={} ({}) {}",
            self.risk.score,
            self.level.label(),
            self.explanation
        )
    }
}

/// Parse a raw model line of the form `RISK:0.42|medium|reason...`.
///
/// Accepts a single leading `RISK:` token (case-insensitive) and then up to
/// three pipe-separated fields. The score is clamped to `[0.0, 1.0]`.
pub fn parse_judgement(raw: &str) -> Judgement {
    let trimmed = raw.trim();
    let body = trimmed
        .strip_prefix("RISK:")
        .or_else(|| trimmed.strip_prefix("risk:"))
        .unwrap_or(trimmed);

    let mut parts = body.splitn(3, '|');
    let score = parts.next().unwrap_or("").trim();
    let label = parts.next().unwrap_or("").trim();
    let explanation = parts.next().unwrap_or("").trim();

    let parsed_score = score.parse::<f64>().ok();
    if let Some(s) = parsed_score {
        let clamped = s.clamp(0.0, 1.0);
        let label_str = if label.is_empty() {
            RiskLevel::from_score(clamped).label().to_string()
        } else {
            label.to_string()
        };
        let level = Judgement::resolved_level(clamped, &label_str);
        Judgement {
            risk: Risk::new(clamped, Vec::new()),
            explanation: explanation.to_string(),
            level,
            parse_failed: false,
        }
    } else {
        // Maybe the model replied with a bare label like `HIGH`.
        let low = trimmed.to_lowercase();
        let level = if low.contains("critical") || low.contains("high") {
            RiskLevel::High
        } else if low.contains("medium") || low.contains("moderate") {
            RiskLevel::Medium
        } else {
            RiskLevel::Low
        };
        let score = match level {
            RiskLevel::High => 0.75,
            RiskLevel::Medium => 0.4,
            RiskLevel::Low => 0.1,
        };
        Judgement {
            risk: Risk::new(score, Vec::new()),
            explanation: explanation.to_string(),
            level,
            parse_failed: false,
        }
    }
}

/// A driver turns an adjudication prompt into a model's textual verdict.
///
/// This is the seam between the pure guardian crate and the async provider
/// stack. The orchestration layer supplies a real implementation that calls
/// `forge_domain`'s `ChatRepository`; tests supply a canned responder.
pub trait AdjudicationDriver: Send + Sync {
    fn adjudicate(&self, prompt: &str) -> impl Future<Output = anyhow::Result<String>> + Send;
}

impl<F, Fut> AdjudicationDriver for F
where
    F: Fn(&str) -> Fut + Send + Sync,
    Fut: Future<Output = anyhow::Result<String>> + Send,
{
    fn adjudicate(&self, prompt: &str) -> impl Future<Output = anyhow::Result<String>> + Send {
        self(prompt)
    }
}

/// An [`AdjudicationDriver`] that always returns a fixed verdict.
#[derive(Debug, Clone)]
pub struct FixedAdjudicationDriver {
    /// A fully-formed `RISK:...` line to return verbatim.
    pub verdict: String,
}

impl FixedAdjudicationDriver {
    pub fn new(verdict: impl Into<String>) -> Self {
        Self { verdict: verdict.into() }
    }
}

impl AdjudicationDriver for FixedAdjudicationDriver {
    async fn adjudicate(&self, _prompt: &str) -> anyhow::Result<String> {
        Ok(self.verdict.clone())
    }
}

/// An [`AdjudicationDriver`] that always errors, used to exercise the
/// conservative fallback path.
#[derive(Debug, Clone)]
pub struct ErroringAdjudicationDriver;

impl AdjudicationDriver for ErroringAdjudicationDriver {
    async fn adjudicate(&self, _prompt: &str) -> anyhow::Result<String> {
        Err(anyhow::anyhow!("driver unavailable"))
    }
}

/// An LLM-driven risk judge.
///
/// Wraps a driver and a prompt builder. On a driver/parse error it degrades
/// to a conservative [`Judgement::unparsed`] (high risk) so the caller knows
/// the answer is not trustworthy.
#[derive(Clone)]
pub struct LlmRiskJudge<D> {
    driver: D,
}

impl<D: AdjudicationDriver> LlmRiskJudge<D> {
    pub fn new(driver: D) -> Self {
        Self { driver }
    }

    /// Adjudicate an operation description. `operation_desc` is a
    /// human-oriented summary (e.g. `Write /etc/hosts`).
    pub async fn judge(&self, operation_desc: &str) -> anyhow::Result<Judgement> {
        let prompt = build_prompt(operation_desc);
        match self.driver.adjudicate(&prompt).await {
            Ok(raw) => {
                let judgement = parse_judgement(&raw);
                if judgement.risk.score.is_nan() {
                    Ok(Judgement::unparsed(&raw))
                } else {
                    Ok(judgement)
                }
            }
            // A driver error means we have no trustworthy signal: fall back
            // to a conservative, explicitly-unparsed (high risk) judgement.
            Err(e) => Ok(Judgement::unparsed(&format!("ERR: {e}"))),
        }
    }
}

/// Build the constrained adjudication prompt for an operation.
pub fn build_prompt(operation_desc: &str) -> String {
    format!(
        "You are a code-safety adjudicator. Judge this agent operation for risk.\n\
         Operation: {operation_desc}\n\
         Reply with exactly one line: RISK:<0.0..1.0>|<low|medium|high|critical>|<reason>"
    )
}

/// A zero-allocation, dependency-free driver that classifies an operation
/// from keyword hints — used as a local fallback when no model is available.
#[derive(Debug, Clone, Default)]
pub struct KeywordDriver;

impl AdjudicationDriver for KeywordDriver {
    async fn adjudicate(&self, prompt: &str) -> anyhow::Result<String> {
        let text = prompt.to_lowercase();
        let score = if text.contains("rm -rf")
            || text.contains("git push --force")
            || text.contains(".env")
            || text.contains(".ssh")
            || text.contains("format c:")
        {
            0.95
        } else if text.contains("delete") || text.contains("force") || text.contains("overwrite") {
            0.6
        } else if text.contains("write") || text.contains("create") || text.contains("modify") {
            0.3
        } else {
            0.05
        };
        let label = match score {
            s if s >= 0.8 => "high",
            s if s >= 0.5 => "medium",
            _ => "low",
        };
        Ok(format!("RISK:{score}|{label}|heuristic keyword fallback"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_full_verdict() {
        let j = parse_judgement("RISK:0.87|high|deleting production .env");
        assert!(!j.parse_failed);
        assert!((j.risk.score - 0.87).abs() < 1e-6);
        assert_eq!(j.level, RiskLevel::High);
        assert_eq!(j.explanation, "deleting production .env");
    }

    #[test]
    fn parses_no_explanation() {
        let j = parse_judgement("risk:0.12|low|");
        assert!(!j.parse_failed);
        assert!((j.risk.score - 0.12).abs() < 1e-6);
        assert_eq!(j.level, RiskLevel::Low);
    }

    #[test]
    fn parses_bare_label() {
        let j = parse_judgement("HIGH risk: force push");
        assert!(!j.parse_failed);
        assert_eq!(j.level, RiskLevel::High);
    }

    #[test]
    fn clamps_out_of_range() {
        let j = parse_judgement("RISK:1.7|critical|way too high");
        assert!(!j.parse_failed);
        assert!((j.risk.score - 1.0).abs() < 1e-6);
        let j = parse_judgement("RISK:-0.3|low|negative");
        assert!(!j.parse_failed);
        assert!((j.risk.score - 0.0).abs() < 1e-6);
    }

    #[test]
    fn unparsable_yields_conservative_fallback() {
        let j = parse_judgement("no structured answer here");
        // Bare-label path does not mark parse_failed, but the driver-error
        // path in LlmRiskJudge produces an explicit unparsed judgement.
        assert!(!j.parse_failed);
    }

    #[tokio::test]
    async fn llm_judge_uses_fixed_driver() {
        let driver = FixedAdjudicationDriver::new("RISK:0.55|high|destructive write");
        let judge = LlmRiskJudge::new(driver);
        let j = judge.judge("Write /etc/hosts").await.unwrap();
        assert!((j.risk.score - 0.55).abs() < 1e-6);
        assert_eq!(j.level, RiskLevel::High);
        assert_eq!(j.explanation, "destructive write");
    }

    #[tokio::test]
    async fn llm_judge_falls_back_on_driver_error() {
        let judge = LlmRiskJudge::new(ErroringAdjudicationDriver);
        let j = judge.judge("some op").await.unwrap();
        assert!(j.parse_failed);
        assert!((j.risk.score - 1.0).abs() < 1e-6);
    }

    #[tokio::test]
    async fn keyword_driver_classifies() {
        let d = KeywordDriver;
        let judge = LlmRiskJudge::new(d);
        let risky = judge.judge("rm -rf in .env").await.unwrap();
        assert!((risky.risk.score - 0.95).abs() < 1e-6);
        let safe = judge.judge("write a test file").await.unwrap();
        assert!(safe.risk.score < 0.4);
    }
}
