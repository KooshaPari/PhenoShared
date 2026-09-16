use anyhow::{Result, anyhow};
use chrono::{DateTime, Datelike, Duration, Utc};
use serde::Serialize;
use std::collections::BTreeMap;

use crate::cli::{CoverageArgs, DailyArgs, MonthlyArgs, OutputMode, QueryArgs};
use crate::models::{CostBreakdown, DailyEntry, DailyReport, UsageEvent};
use crate::utils::{
    build_coverage_report, collect_unpriced_events, compute_costs, filter_month,
    filter_provider_model, load_events, load_pricing, maybe_write_unpriced_outputs,
    print_coverage_table, print_daily_markdown, print_daily_table, render_cost_breakdown,
};

#[derive(Debug, Clone, Copy, Eq, PartialEq, Serialize)]
pub enum SlidingWindow {
    FiveMinutes,
    OneHour,
    OneDay,
}

impl SlidingWindow {
    pub const ALL: [Self; 3] = [Self::FiveMinutes, Self::OneHour, Self::OneDay];

    pub fn duration(self) -> Duration {
        match self {
            Self::FiveMinutes => Duration::minutes(5),
            Self::OneHour => Duration::hours(1),
            Self::OneDay => Duration::hours(24),
        }
    }

    pub fn label(self) -> &'static str {
        match self {
            Self::FiveMinutes => "5m",
            Self::OneHour => "1h",
            Self::OneDay => "24h",
        }
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct SlidingWindowMetric {
    pub window: String,
    pub start: DateTime<Utc>,
    pub end: DateTime<Utc>,
    pub event_count: usize,
    pub session_count: usize,
    pub tokens: u64,
    pub tokens_per_second: f64,
    pub tokens_by_provider: BTreeMap<String, u64>,
}

pub fn build_sliding_window_metrics(
    events: &[UsageEvent],
    end: DateTime<Utc>,
) -> Vec<SlidingWindowMetric> {
    SlidingWindow::ALL
        .into_iter()
        .map(|window| {
            let start = end - window.duration();
            let selected = events
                .iter()
                .filter(|event| event.timestamp > start && event.timestamp <= end);
            let mut sessions = std::collections::BTreeSet::new();
            let mut tokens_by_provider = BTreeMap::new();
            let mut event_count = 0;
            let mut tokens = 0;

            for event in selected {
                event_count += 1;
                sessions.insert(&event.session_id);
                tokens += event.usage.total();
                *tokens_by_provider
                    .entry(event.provider.clone())
                    .or_insert(0) += event.usage.total();
            }

            let seconds = window.duration().num_seconds() as f64;
            SlidingWindowMetric {
                window: window.label().to_string(),
                start,
                end,
                event_count,
                session_count: sessions.len(),
                tokens,
                tokens_per_second: tokens as f64 / seconds,
                tokens_by_provider,
            }
        })
        .collect()
}

pub fn run_monthly(args: MonthlyArgs) -> Result<()> {
    let report = build_monthly_report(&args.query, args.month.as_deref())?;
    render_cost_breakdown(
        "Monthly",
        &report,
        args.query.output,
        args.query.top_providers,
        args.query.top_models,
    )?;

    Ok(())
}

pub fn run_daily(args: DailyArgs) -> Result<()> {
    let report = build_daily_report(&args.query, args.month.as_deref())?;
    render_daily_report(
        &report,
        args.query.output,
        args.query.top_providers,
        args.query.top_models,
    )
}

pub fn run_coverage(args: CoverageArgs) -> Result<()> {
    let pricing = load_pricing(&args.pricing)?;
    let events = load_events(&args.events)?;
    let normalized = crate::utils::normalize_events(events, &pricing);
    let filtered = filter_month(normalized, args.month.as_deref())?;
    if filtered.is_empty() {
        return Err(anyhow!("no events matched selected month filters"));
    }

    let report = build_coverage_report(&filtered, &pricing);
    let unpriced_events = collect_unpriced_events(&filtered, &pricing);
    maybe_write_unpriced_outputs(
        &filtered,
        &unpriced_events,
        &pricing,
        args.write_patch.as_deref(),
        args.write_unpriced_events.as_deref(),
    )?;

    if args.json_output {
        println!("{}", serde_json::to_string_pretty(&report)?);
    } else {
        print_coverage_table(&report);
    }
    Ok(())
}

pub fn build_monthly_report(query: &QueryArgs, month: Option<&str>) -> Result<CostBreakdown> {
    let pricing = load_pricing(&query.pricing)?;

    let events = load_events(&query.events)?;
    let normalized = crate::utils::normalize_events(events, &pricing);
    let month_filtered = filter_month(normalized, month)?;
    let filtered = filter_provider_model(month_filtered, &pricing, &query.providers, &query.models);
    if filtered.is_empty() {
        return Err(anyhow!(
            "no events matched selected month/provider/model filters"
        ));
    }

    compute_costs(&filtered, &pricing, query.on_unpriced)
}

pub fn build_daily_report(query: &QueryArgs, month: Option<&str>) -> Result<DailyReport> {
    let pricing = load_pricing(&query.pricing)?;

    let events = load_events(&query.events)?;
    let normalized = crate::utils::normalize_events(events, &pricing);
    let month_filtered = filter_month(normalized, month)?;
    let filtered = filter_provider_model(month_filtered, &pricing, &query.providers, &query.models);
    if filtered.is_empty() {
        return Err(anyhow!(
            "no events matched selected month/provider/model filters"
        ));
    }

    let totals = compute_costs(&filtered, &pricing, query.on_unpriced)?;
    let month = format!(
        "{:04}-{:02}",
        filtered[0].timestamp.year(),
        filtered[0].timestamp.month()
    );

    let mut by_day: BTreeMap<chrono::NaiveDate, Vec<UsageEvent>> = BTreeMap::new();
    for event in filtered {
        by_day
            .entry(event.timestamp.date_naive())
            .or_default()
            .push(event);
    }

    let mut days = Vec::with_capacity(by_day.len());
    for (day, day_events) in by_day {
        let breakdown = compute_costs(&day_events, &pricing, query.on_unpriced)?;
        days.push(DailyEntry {
            day: day.format("%Y-%m-%d").to_string(),
            breakdown,
        });
    }

    let report = DailyReport {
        month,
        totals,
        days,
    };
    Ok(report)
}

pub fn render_daily_report(
    report: &DailyReport,
    output: OutputMode,
    top_providers: Option<usize>,
    top_models: Option<usize>,
) -> Result<()> {
    match output {
        OutputMode::Json => println!("{}", serde_json::to_string_pretty(&report)?),
        OutputMode::Table => print_daily_table(report, top_providers, top_models),
        OutputMode::Markdown => print_daily_markdown(report, top_providers, top_models),
    }

    Ok(())
}
