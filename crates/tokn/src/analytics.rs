use anyhow::{anyhow, Result};
use chrono::Datelike;
use std::collections::BTreeMap;

use crate::cli::{CoverageArgs, DailyArgs, MonthlyArgs, OutputMode, QueryArgs};
use crate::models::{CostBreakdown, DailyEntry, DailyReport, UsageEvent};
use crate::utils::{
    build_coverage_report, collect_unpriced_events, compute_costs, filter_month,
    filter_provider_model, load_events, load_pricing, maybe_write_unpriced_outputs,
    print_coverage_table, print_daily_markdown, print_daily_table, render_cost_breakdown,
};

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
