use chrono::{DateTime, Utc};
use serde::Serialize;

use crate::analytics::SlidingWindow;
use crate::models::UsageEvent;

#[derive(Debug, Clone, Eq, PartialEq)]
pub struct BudgetLimit {
    pub provider: Option<String>,
    pub model: Option<String>,
    pub window: SlidingWindow,
    pub max_tokens: u64,
}

#[derive(Debug, Clone, Serialize)]
pub struct BudgetAlert {
    pub provider: Option<String>,
    pub model: Option<String>,
    pub window: String,
    pub start: DateTime<Utc>,
    pub end: DateTime<Utc>,
    pub observed_tokens: u64,
    pub max_tokens: u64,
    pub utilization: f64,
    pub burn_rate_tokens_per_hour: f64,
}

pub fn evaluate_budget_guardrails(
    events: &[UsageEvent],
    end: DateTime<Utc>,
    limits: &[BudgetLimit],
) -> Vec<BudgetAlert> {
    limits
        .iter()
        .filter_map(|limit| {
            let start = end - limit.window.duration();
            let observed_tokens = events
                .iter()
                .filter(|event| event.timestamp > start && event.timestamp <= end)
                .filter(|event| {
                    limit
                        .provider
                        .as_deref()
                        .is_none_or(|provider| provider == event.provider)
                })
                .filter(|event| {
                    limit
                        .model
                        .as_deref()
                        .is_none_or(|model| model == event.model)
                })
                .map(|event| event.usage.total())
                .sum::<u64>();

            if observed_tokens <= limit.max_tokens {
                return None;
            }

            let hours = limit.window.duration().num_seconds() as f64 / 3_600.0;
            Some(BudgetAlert {
                provider: limit.provider.clone(),
                model: limit.model.clone(),
                window: limit.window.label().to_string(),
                start,
                end,
                observed_tokens,
                max_tokens: limit.max_tokens,
                utilization: observed_tokens as f64 / limit.max_tokens as f64,
                burn_rate_tokens_per_hour: observed_tokens as f64 / hours,
            })
        })
        .collect()
}
