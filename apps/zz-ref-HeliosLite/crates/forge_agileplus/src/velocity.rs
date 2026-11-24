//! Velocity reports — per-sprint velocity + the rolling five-sprint rule.
//!
//! A [`VelocityReport`] describes one sprint's planned vs. completed story
//! points plus the carryover (points not finished) and a rolling
//! five-sprint [`VelocityReport::rolling_average`] used for capacity
//! planning per `docs/AGILEPLUS-SETUP.md`.

use serde::{Deserialize, Serialize};

/// Rolling window for the velocity predictor. Matches
/// `docs/AGILEPLUS-SETUP.md` ("rolling five-sprint measurement").
pub const ROLLING_WINDOW: usize = 5;

/// One sprint's velocity snapshot.
///
/// `sprint_id` is the human-readable identifier (e.g. "sprint-47"); the
/// integer sprint number lives in [`crate::sprint::Sprint::number`].
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct VelocityReport {
    /// Sprint identifier (e.g. "sprint-47").
    pub sprint_id: String,
    /// Story points the team committed to.
    pub planned_points: f32,
    /// Story points actually completed at end-of-sprint.
    pub completed_points: f32,
    /// Story points carried over to the next sprint
    /// (`planned_points - completed_points`, clamped to `>= 0`).
    pub carryover: f32,
    /// Rolling 5-sprint average of `completed_points` including this
    /// sprint. `0.0` when fewer than one prior sprint has been recorded.
    #[serde(default)]
    pub rolling_average: f32,
}

impl VelocityReport {
    /// Construct a velocity report for a single sprint.
    pub fn new(sprint_id: impl Into<String>, planned_points: f32, completed_points: f32) -> Self {
        let carryover = (planned_points - completed_points).max(0.0);
        Self {
            sprint_id: sprint_id.into(),
            planned_points,
            completed_points,
            carryover,
            rolling_average: 0.0,
        }
    }

    /// Completion ratio: `completed_points / planned_points`. Returns
    /// `None` when no commitment was made.
    pub fn completion_ratio(&self) -> Option<f32> {
        if self.planned_points <= 0.0 {
            None
        } else {
            Some((self.completed_points / self.planned_points).clamp(0.0, f32::MAX))
        }
    }
}

/// Compute the rolling five-sprint average completion velocity for a
/// Compute the rolling-window average of completed points across a chronologically
/// ordered series of velocity reports.
///
/// `reports` is expected to be ordered chronologically (oldest first).
/// The result is the simple moving average of the **last
/// [`ROLLING_WINDOW`] entries** (or all entries if fewer than the window
/// has been recorded). Returns `0.0` when the input is empty.
#[allow(clippy::indexing_slicing)] // bounded by reports.len() checks below
pub fn rolling_average(reports: &[VelocityReport]) -> f32 {
    if reports.is_empty() {
        return 0.0;
    }
    let window = reports.len().min(ROLLING_WINDOW);
    // Take the last `window` entries. `start = len - window <= len`, so the
    // slice index is sound; the lint allow above documents the invariant.
    let start = reports.len() - window;
    let slice = &reports[start..];
    let total: f32 = slice.iter().map(|r| r.completed_points).sum();
    total / window as f32
}

/// Build a fully-populated [`VelocityReport`] list, computing the rolling
/// average for each entry.
#[allow(clippy::indexing_slicing)] // i < reports.len() and window_start <= window_end <= i+1 <= len
pub fn with_rolling_averages(reports: Vec<VelocityReport>) -> Vec<VelocityReport> {
    let mut out = Vec::with_capacity(reports.len());
    for i in 0..reports.len() {
        let mut r = reports[i].clone();
        // Window for entry i: the previous up-to-(WINDOW-1) entries plus this one.
        // window_start uses saturating_sub, so the lower bound is always <= i + 1
        // (= window_end). The slice is therefore in-bounds.
        let window_start = (i + 1).saturating_sub(ROLLING_WINDOW);
        let window_end = i + 1;
        let slice = &reports[window_start..window_end];
        let total: f32 = slice.iter().map(|r| r.completed_points).sum();
        r.rolling_average = total / slice.len() as f32;
        out.push(r);
    }
    out
}
#[cfg(test)]
mod tests {
    use super::*;

    fn reports(values: &[f32]) -> Vec<VelocityReport> {
        values
            .iter()
            .enumerate()
            .map(|(i, v)| VelocityReport::new(format!("sprint-{}", i + 1), *v, *v))
            .collect()
    }

    #[test]
    fn new_computes_carryover() {
        let r = VelocityReport::new("sprint-1", 30.0, 22.0);
        assert_eq!(r.planned_points, 30.0);
        assert_eq!(r.completed_points, 22.0);
        assert_eq!(r.carryover, 8.0);
        assert_eq!(r.completion_ratio(), Some(22.0 / 30.0));
    }

    #[test]
    fn carryover_never_negative() {
        let r = VelocityReport::new("sprint-1", 20.0, 25.0);
        assert_eq!(r.carryover, 0.0);
    }

    #[test]
    fn completion_ratio_handles_zero_commitment() {
        let r = VelocityReport::new("sprint-1", 0.0, 5.0);
        assert_eq!(r.completion_ratio(), None);
    }

    #[test]
    fn rolling_average_uses_last_five() {
        let v = reports(&[10.0, 12.0, 14.0, 16.0, 18.0, 20.0]);
        // Last 5 of 6 entries → [12, 14, 16, 18, 20] = 80 / 5 = 16
        assert!((rolling_average(&v) - 16.0).abs() < 1e-5);
    }

    #[test]
    fn rolling_average_handles_smaller_history() {
        let v = reports(&[10.0, 20.0]);
        // Only 2 entries → (10 + 20) / 2 = 15
        assert!((rolling_average(&v) - 15.0).abs() < 1e-5);
    }

    #[test]
    fn rolling_average_handles_exactly_five() {
        let v = reports(&[5.0, 5.0, 5.0, 5.0, 5.0]);
        assert!((rolling_average(&v) - 5.0).abs() < 1e-5);
    }

    #[test]
    fn rolling_average_on_empty_is_zero() {
        assert_eq!(rolling_average(&[]), 0.0);
    }

    #[test]
    #[allow(clippy::indexing_slicing)] // indices are bounded by reports.len() and known-good
    fn with_rolling_averages_walks_chronologically() {
        let v = reports(&[10.0, 20.0, 30.0, 40.0, 50.0, 60.0]);
        let out = with_rolling_averages(v);
        assert_eq!(out.len(), 6);
        // Entry 0: just itself → 10
        assert!((out[0].rolling_average - 10.0).abs() < 1e-4);
        // Entry 4: last 5 = [10, 20, 30, 40, 50] / 5 = 30
        assert!((out[4].rolling_average - 30.0).abs() < 1e-4);
        // Entry 5: last 5 = [20, 30, 40, 50, 60] / 5 = 40
        assert!((out[5].rolling_average - 40.0).abs() < 1e-4);
    }
    #[test]
    fn json_round_trip_preserves_velocity_report() {
        let r = VelocityReport::new("sprint-47", 30.0, 25.0);
        let json = serde_json::to_string(&r).unwrap();
        let back: VelocityReport = serde_json::from_str(&json).unwrap();
        assert_eq!(back, r);
    }

    #[test]
    fn rolling_window_constant_is_five() {
        assert_eq!(ROLLING_WINDOW, 5);
    }
}
