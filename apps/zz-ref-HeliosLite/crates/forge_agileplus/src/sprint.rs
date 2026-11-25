//! AgilePlus sprint records.
//!
//! A [`Sprint`] is a time-boxed iteration with a goal, acceptance criteria,
//! tracked risks, and a start/end date pair. The wire format is JSON; the
//! scorecard engine reads sprints to compute per-sprint velocity and
//! carryover for the rolling-five-sprint rule.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use thiserror::Error;

/// Sprint-specific errors.
#[derive(Debug, Error)]
pub enum SprintError {
    /// `start_date` is not strictly before `end_date`.
    #[error("invalid sprint dates: {0}")]
    InvalidDates(String),
    /// The goal string is empty / whitespace-only.
    #[error("invalid sprint goal: {0}")]
    EmptyGoal(String),
}

/// Crate-wide [`Result`] alias — re-exported from [`crate::scorecard`].
pub use crate::scorecard::Result;

/// A single AgilePlus sprint.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Sprint {
    /// 1-based sprint number (sprint #47 → `47`).
    pub number: u32,
    /// Short sprint goal. Must be non-empty.
    pub goal: String,
    /// Sprint start (inclusive), UTC.
    pub start_date: DateTime<Utc>,
    /// Sprint end (inclusive), UTC.
    pub end_date: DateTime<Utc>,
    /// Bulleted acceptance criteria for the goal.
    #[serde(default)]
    pub acceptance_criteria: Vec<String>,
    /// Tracked risks for the sprint.
    #[serde(default)]
    pub risks: Vec<String>,
}

impl Sprint {
    /// Construct and validate a sprint.
    ///
    /// Returns [`SprintError::EmptyGoal`] when `goal` is whitespace-only.
    /// Returns [`SprintError::InvalidDates`] when `start_date >= end_date`.
    pub fn new(
        number: u32,
        goal: impl Into<String>,
        start_date: DateTime<Utc>,
        end_date: DateTime<Utc>,
        acceptance_criteria: Vec<String>,
        risks: Vec<String>,
    ) -> std::result::Result<Self, SprintError> {
        let goal = goal.into();
        if goal.trim().is_empty() {
            return Err(SprintError::EmptyGoal(
                "sprint goal must be non-empty".to_string(),
            ));
        }
        if start_date >= end_date {
            return Err(SprintError::InvalidDates(format!(
                "start_date {} must be strictly before end_date {}",
                start_date, end_date
            )));
        }
        Ok(Self {
            number,
            goal,
            start_date,
            end_date,
            acceptance_criteria,
            risks,
        })
    }

    /// Validate an already-constructed sprint. Useful after JSON
    /// deserialization.
    pub fn validate(&self) -> std::result::Result<(), SprintError> {
        if self.goal.trim().is_empty() {
            return Err(SprintError::EmptyGoal(
                "sprint goal must be non-empty".to_string(),
            ));
        }
        if self.start_date >= self.end_date {
            return Err(SprintError::InvalidDates(format!(
                "start_date {} must be strictly before end_date {}",
                self.start_date, self.end_date
            )));
        }
        Ok(())
    }

    /// Serialize to JSON.
    pub fn to_json(&self) -> Result<String> {
        Ok(serde_json::to_string_pretty(self)?)
    }

    /// Deserialize from JSON.
    pub fn from_json(input: &str) -> std::result::Result<Self, crate::scorecard::AgilePlusError> {
        Ok(serde_json::from_str(input)?)
    }

    /// Sprint length in days.
    pub fn duration_days(&self) -> i64 {
        (self.end_date - self.start_date).num_days()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::TimeZone;

    fn utc(y: i32, m: u32, d: u32) -> DateTime<Utc> {
        Utc.with_ymd_and_hms(y, m, d, 0, 0, 0).unwrap()
    }

    #[test]
    fn valid_sprint_is_constructed() {
        let s = Sprint::new(
            47,
            "Quality Hardening",
            utc(2026, 8, 19),
            utc(2026, 8, 26),
            vec!["clippy clean".into(), "scorecard ≥ 7.6".into()],
            vec!["rate limit on coverage run".into()],
        )
        .expect("valid");
        assert_eq!(s.number, 47);
        assert_eq!(s.duration_days(), 7);
        assert_eq!(s.acceptance_criteria.len(), 2);
        assert_eq!(s.risks.len(), 1);
    }

    #[test]
    fn empty_goal_is_rejected() {
        let err =
            Sprint::new(1, "   ", utc(2026, 1, 1), utc(2026, 1, 8), vec![], vec![]).unwrap_err();
        assert!(matches!(err, SprintError::EmptyGoal(_)));
    }

    #[test]
    fn empty_string_goal_is_rejected() {
        let err = Sprint::new(1, "", utc(2026, 1, 1), utc(2026, 1, 8), vec![], vec![]).unwrap_err();
        assert!(matches!(err, SprintError::EmptyGoal(_)));
    }

    #[test]
    fn start_not_before_end_is_rejected() {
        let err =
            Sprint::new(1, "x", utc(2026, 1, 8), utc(2026, 1, 8), vec![], vec![]).unwrap_err();
        assert!(matches!(err, SprintError::InvalidDates(_)));
    }

    #[test]
    fn end_before_start_is_rejected() {
        let err =
            Sprint::new(1, "x", utc(2026, 1, 8), utc(2026, 1, 1), vec![], vec![]).unwrap_err();
        assert!(matches!(err, SprintError::InvalidDates(_)));
    }

    #[test]
    fn validate_after_json_round_trip() {
        let s = Sprint::new(
            47,
            "Quality Hardening",
            utc(2026, 8, 19),
            utc(2026, 8, 26),
            vec!["criterion green".into()],
            vec![],
        )
        .expect("valid");
        let json = s.to_json().expect("to_json");
        let back = Sprint::from_json(&json).expect("from_json");
        back.validate().expect("post-roundtrip");
        assert_eq!(back, s);
    }

    #[test]
    fn json_round_trip_preserves_acceptance_criteria_and_risks() {
        let s = Sprint::new(
            48,
            "i18n Spike",
            utc(2026, 8, 26),
            utc(2026, 9, 2),
            vec!["a".into(), "b".into(), "c".into()],
            vec!["risk-a".into()],
        )
        .expect("valid");
        let json = s.to_json().unwrap();
        let back: Sprint = serde_json::from_str(&json).unwrap();
        assert_eq!(back.acceptance_criteria, vec!["a", "b", "c"]);
        assert_eq!(back.risks, vec!["risk-a"]);
        assert_eq!(back, s);
    }

    #[test]
    fn default_fields_deserialize() {
        // `acceptance_criteria` and `risks` have `#[serde(default)]` so
        // older JSON without them still parses.
        let json = r#"{
            "number": 1,
            "goal": "Spike",
            "start_date": "2026-01-01T00:00:00Z",
            "end_date": "2026-01-08T00:00:00Z"
        }"#;
        let s: Sprint = serde_json::from_str(json).expect("deserialize");
        assert!(s.acceptance_criteria.is_empty());
        assert!(s.risks.is_empty());
        s.validate().expect("validate");
    }
}
