//! LLM-driven / guardian policy layer (P0.1).
//!
//! Complements the rule-based [`forge_domain::policies`] engine with a
//! risk-adjudication layer that scores each tool operation *before* the
//! rule engine makes an allow/deny/confirm decision. This is the substrate
//! for the LLM "guardian" that can escalate, learn from feedback, and
//! feed a risk display in the interactive tool-call view (P0.4).
//!
//! # Architecture
//!
//! ```text
//!                RiskJudge                       PolicyEngine
//! Tool call ---------> score(op) -> Risk  -----> allow/deny/confirm
//!                          |                       ^
//!                          v                       |
//!                   guardian feedback  <-----------+ (human / LLM)
//! ```
//!
//! The [`RiskJudge`] is deliberately decoupled from the rule engine:
//! it produces a [`Risk`] score, the rule engine decides the outcome, and
//! the audit log (`forge_audit`) records the trail.

pub mod adjudicator;
pub mod foreign;
pub mod judge;
pub mod learn;
pub mod risk;
pub mod sandbox;
pub mod session;

pub use adjudicator::{GuardianAdjudicator, RuleVerdict};
pub use foreign::{
    AdjudicationDriver, FixedAdjudicationDriver, Judgement, KeywordDriver, LlmRiskJudge,
    build_prompt, parse_judgement,
};
pub use judge::{HeuristicRiskJudge, NoopRiskJudge, RiskJudge};
pub use learn::{LearnError, LearnedDecision, LearnedPermission, LearningStore};
pub use risk::{Risk, RiskFactor, RiskLabel, RiskLevel};
pub use sandbox::{SandboxPolicy, TieBreak, break_tie, can_contain, gap_label, tie_break_reason};
pub use session::SessionMode;
