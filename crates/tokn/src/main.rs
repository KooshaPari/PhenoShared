use anyhow::Result;
use clap::Parser;

use tokenledger::analytics::{run_coverage, run_daily, run_monthly};
use tokenledger::bench::run_bench;
use tokenledger::cli::{Cli, Command};
use tokenledger::ingest::run_ingest;
use tokenledger::orchestrate::run_orchestrate;
use tokenledger::pricing::{
    run_pricing_apply, run_pricing_audit, run_pricing_check, run_pricing_lint,
    run_pricing_reconcile,
};

fn main() -> Result<()> {
    let cli = Cli::parse();
    match cli.command {
        Command::Monthly(args) => run_monthly(args),
        Command::Daily(args) => run_daily(args),
        Command::Coverage(args) => run_coverage(args),
        Command::PricingCheck(args) => run_pricing_check(args),
        Command::PricingApply(args) => run_pricing_apply(args),
        Command::PricingReconcile(args) => run_pricing_reconcile(args),
        Command::PricingLint(args) => run_pricing_lint(args),
        Command::PricingAudit(args) => run_pricing_audit(args),
        Command::Ingest(args) => run_ingest(args),
        Command::Bench(args) => run_bench(args),
        Command::Orchestrate(args) => run_orchestrate(args),
    }
}
