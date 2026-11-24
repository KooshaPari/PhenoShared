// Output formatting functions for tables, markdown, and audit reports

use crate::models::*;

pub fn print_coverage_table(report: &CoverageReport) {
    println!("Pricing Coverage ({})", report.month);
    println!("  Total Events:             {}", report.totals.events);
    println!("  Total Tokens:             {}", report.totals.tokens);
    println!("  Priced Events:            {}", report.priced_count);
    println!("  Unpriced Events:          {}", report.unpriced_count);
    println!();

    println!("Missing Providers");
    if report.missing_providers.is_empty() {
        println!("  (none)");
    } else {
        for provider in &report.missing_providers {
            let suggestions = report
                .suggested_provider_aliases
                .get(provider)
                .cloned()
                .unwrap_or_default();
            if suggestions.is_empty() {
                println!("  {}", provider);
            } else {
                println!("  {} -> {}", provider, suggestions.join(", "));
            }
        }
    }
    println!();

    println!("Missing Models By Provider");
    if report.missing_models_by_provider.is_empty() {
        println!("  (none)");
    } else {
        for (provider, models) in &report.missing_models_by_provider {
            println!("  {}", provider);
            for model in models {
                println!("    - {}", model);
            }
        }
    }
    println!();

    println!("Suggested Model Aliases By Provider");
    if report.suggested_model_aliases_by_provider.is_empty() {
        println!("  (none)");
    } else {
        for (provider, suggestions) in &report.suggested_model_aliases_by_provider {
            println!("  {}", provider);
            for suggestion in suggestions {
                println!("    - {} ({})", suggestion.model, suggestion.count);
            }
        }
    }
}

pub fn print_pricing_audit_report(report: &PricingAuditReport) {
    println!("Pricing Audit");
    println!("  Pricing Path:         {}", report.pricing_path);
    println!("  Checked At:           {}", report.checked_at);
    println!("  Metadata Present:     {}", report.metadata_present);
    println!("  Source Present:       {}", report.source_present);
    println!("  Updated At Present:   {}", report.updated_at_present);
    if let Some(age_days) = report.age_days {
        println!("  Age Days:             {}", age_days);
    } else {
        println!("  Age Days:             (unknown)");
    }
    println!("  Stale:                {}", report.stale);
    println!("  Pass:                 {}", report.pass);
    if !report.violations.is_empty() {
        println!("  Violations:");
        for violation in &report.violations {
            println!("    - {}", violation);
        }
    }
    if !report.warnings.is_empty() {
        println!("  Warnings:");
        for warning in &report.warnings {
            println!("    - {}", warning);
        }
    }
}

pub fn print_table(
    label: &str,
    report: &CostBreakdown,
    top_providers: Option<usize>,
    top_models: Option<usize>,
) {
    println!("{} Cost Summary", label);
    println!(
        "  Variable Cost:            ${:.2}",
        report.variable_cost_usd
    );
    println!(
        "  Subscription Allocated:   ${:.2}",
        report.subscription_allocated_usd
    );
    println!(
        "  Monthly Total:            ${:.2}",
        report.monthly_total_usd
    );
    println!(
        "  Blended Cost / MTok:      ${:.4}",
        report.blended_usd_per_mtok
    );
    println!("  Total Tokens:             {}", report.total_tokens);
    println!("  Total MTok:               {:.4}", report.total_mtok);
    println!("  Sessions:                 {}", report.session_count);
    println!(
        "  Skipped Unpriced Events:  {}",
        report.skipped_unpriced_count
    );
    println!();

    println!("Per Provider");
    for row in top_rows(&report.provider_breakdown, top_providers) {
        println!(
            "  {:<16} tokens={} total=${:.2} blended=${:.4}/MTok sessions={} tool_share={:.2}%",
            row.name,
            row.tokens,
            row.total_cost_usd,
            row.blended_usd_per_mtok,
            row.session_count,
            row.tool_share * 100.0
        );
    }
    println!();

    println!("Per Model");
    for row in top_rows(&report.model_breakdown, top_models) {
        println!(
            "  {:<24} tokens={} total=${:.2} blended=${:.4}/MTok sessions={} tool_share={:.2}%",
            row.name,
            row.tokens,
            row.total_cost_usd,
            row.blended_usd_per_mtok,
            row.session_count,
            row.tool_share * 100.0
        );
    }
    println!();

    println!("Suggestions");
    for tip in &report.suggestions {
        println!("  - {}", tip);
    }
}

pub fn print_markdown(
    label: &str,
    report: &CostBreakdown,
    top_providers: Option<usize>,
    top_models: Option<usize>,
) {
    println!("## {} Cost Summary", label);
    println!();
    println!("- Variable Cost: `${:.2}`", report.variable_cost_usd);
    println!(
        "- Subscription Allocated: `${:.2}`",
        report.subscription_allocated_usd
    );
    println!("- Monthly Total: `${:.2}`", report.monthly_total_usd);
    println!(
        "- Blended Cost / MTok: `${:.4}`",
        report.blended_usd_per_mtok
    );
    println!("- Total Tokens: `{}`", report.total_tokens);
    println!("- Total MTok: `{:.4}`", report.total_mtok);
    println!("- Sessions: `{}`", report.session_count);
    println!(
        "- Skipped Unpriced Events: `{}`",
        report.skipped_unpriced_count
    );
    println!();

    println!("### Per Provider");
    println!("| Provider | Tokens | Total USD | Blended USD/MTok | Sessions | Tool Share |",);
    println!("|---|---:|---:|---:|---:|---:|");
    for row in top_rows(&report.provider_breakdown, top_providers) {
        println!(
            "| {} | {} | {:.2} | {:.4} | {} | {:.2}% |",
            row.name,
            row.tokens,
            row.total_cost_usd,
            row.blended_usd_per_mtok,
            row.session_count,
            row.tool_share * 100.0
        );
    }
    println!();

    println!("### Per Model");
    println!("| Model | Tokens | Total USD | Blended USD/MTok | Sessions | Tool Share |",);
    println!("|---|---:|---:|---:|---:|---:|");
    for row in top_rows(&report.model_breakdown, top_models) {
        println!(
            "| {} | {} | {:.2} | {:.4} | {} | {:.2}% |",
            row.name,
            row.tokens,
            row.total_cost_usd,
            row.blended_usd_per_mtok,
            row.session_count,
            row.tool_share * 100.0
        );
    }
    println!();

    println!("### Suggestions");
    for tip in &report.suggestions {
        println!("- {}", tip);
    }
}

pub fn print_daily_table(
    report: &DailyReport,
    top_providers: Option<usize>,
    top_models: Option<usize>,
) {
    println!("Daily Cost Summary ({})", report.month);
    println!();
    print_table("Monthly Totals", &report.totals, top_providers, top_models);
    println!();

    for day in &report.days {
        println!("==================================================");
        println!("Day: {}", day.day);
        print_table("Daily", &day.breakdown, top_providers, top_models);
        println!();
    }
}

pub fn print_daily_markdown(
    report: &DailyReport,
    top_providers: Option<usize>,
    top_models: Option<usize>,
) {
    println!("# Daily Cost Summary ({})", report.month);
    println!();
    print_markdown("Monthly Totals", &report.totals, top_providers, top_models);

    for day in &report.days {
        println!();
        println!("---");
        println!();
        println!("## {}", day.day);
        println!();
        print_markdown("Daily", &day.breakdown, top_providers, top_models);
    }
}

pub fn top_rows(rows: &[NamedMetric], top_n: Option<usize>) -> Vec<&NamedMetric> {
    let mut sorted: Vec<&NamedMetric> = rows.iter().collect();
    sorted.sort_by(|a, b| b.tokens.cmp(&a.tokens).then_with(|| a.name.cmp(&b.name)));
    if let Some(limit) = top_n {
        sorted.truncate(limit);
    }
    sorted
}

pub fn default_generated_at() -> chrono::DateTime<chrono::Utc> {
    chrono::Utc::now()
}

pub fn round2(v: f64) -> f64 {
    (v * 100.0).round() / 100.0
}

pub fn round4(v: f64) -> f64 {
    (v * 10_000.0).round() / 10_000.0
}

#[cfg(test)]
mod tests {
    use super::*;

    #[allow(clippy::approx_constant)]
    const PI_ROUNDED_2: f64 = 3.14;
    #[allow(clippy::approx_constant)]
    const PI_ROUNDED_4: f64 = 3.1416;
    const TOLERANCE_2: f64 = 0.001;
    const TOLERANCE_4: f64 = 0.00001;

    #[test]
    fn test_round2_basic() {
        let pi = std::f64::consts::PI;
        let rounded_pi = round2(pi);
        assert!((rounded_pi - PI_ROUNDED_2).abs() < TOLERANCE_2);
        assert_eq!(round2(1.234), 1.23);
        assert_eq!(round2(1.999), 2.00);
    }

    #[test]
    fn test_round2_zero() {
        assert_eq!(round2(0.0), 0.0);
    }

    #[test]
    fn test_round2_negative() {
        let pi = std::f64::consts::PI;
        let rounded_neg_pi = round2(-pi);
        assert!((rounded_neg_pi - (-PI_ROUNDED_2)).abs() < TOLERANCE_2);
        assert_eq!(round2(-1.234), -1.23);
    }

    #[test]
    fn test_round4_basic() {
        let pi = std::f64::consts::PI;
        let rounded_pi = round4(pi);
        assert!((rounded_pi - PI_ROUNDED_4).abs() < TOLERANCE_4);
        assert_eq!(round4(1.23456), 1.2346);
        assert_eq!(round4(1.99999), 2.0000);
    }

    #[test]
    fn test_round4_zero() {
        assert_eq!(round4(0.0), 0.0);
    }

    #[test]
    fn test_round4_negative() {
        let pi = std::f64::consts::PI;
        let rounded_neg_pi = round4(-pi);
        assert!((rounded_neg_pi - (-PI_ROUNDED_4)).abs() < TOLERANCE_4);
        assert_eq!(round4(-1.23456), -1.2346);
    }

    #[test]
    fn test_round2_and_round4_relationship() {
        let pi = std::f64::consts::PI;
        let r2 = round2(pi);
        let r4 = round4(pi);
        assert!((r2 - PI_ROUNDED_2).abs() < TOLERANCE_2);
        assert!((r4 - PI_ROUNDED_4).abs() < TOLERANCE_4);
    }
}
