//! Token usage and cost tracking.

/// Tracks token usage and cost against a configurable budget.
///
/// # Examples
///
/// ```
/// use helios_ai::CostTracker;
///
/// let mut tracker = CostTracker::new(0.000_030, 0.000_060, 1.0);
/// tracker.record_usage(1_000, 500);
/// assert!(!tracker.is_over_budget());
/// assert!(tracker.total_cost_usd() > 0.0);
/// ```
pub struct CostTracker {
    total_input_tokens: u64,
    total_output_tokens: u64,
    cost_per_input: f64,
    cost_per_output: f64,
    budget_usd: f64,
}

impl CostTracker {
    pub fn new(cost_per_input: f64, cost_per_output: f64, budget_usd: f64) -> Self {
        Self {
            total_input_tokens: 0,
            total_output_tokens: 0,
            cost_per_input,
            cost_per_output,
            budget_usd,
        }
    }

    pub fn record_usage(&mut self, input_tokens: u64, output_tokens: u64) {
        self.total_input_tokens += input_tokens;
        self.total_output_tokens += output_tokens;
    }

    pub fn total_cost_usd(&self) -> f64 {
        (self.total_input_tokens as f64) * self.cost_per_input
            + (self.total_output_tokens as f64) * self.cost_per_output
    }

    pub fn remaining_budget_usd(&self) -> f64 {
        (self.budget_usd - self.total_cost_usd()).max(0.0)
    }

    pub fn is_over_budget(&self) -> bool {
        self.total_cost_usd() > self.budget_usd
    }

    pub fn usage_summary(&self) -> String {
        format!(
            "Tokens - input: {}, output: {} | Cost: ${:.6} / ${:.2} budget | Remaining: ${:.6}",
            self.total_input_tokens,
            self.total_output_tokens,
            self.total_cost_usd(),
            self.budget_usd,
            self.remaining_budget_usd(),
        )
    }
}
