//! ParetoRs — pure utility functions.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// Raw harness record from a run log.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RawHarnessRecord {
    pub provider: String,
    pub model: String,
    pub input_tokens: u64,
    pub output_tokens: u64,
    pub latency_ms: Option<f64>,
    pub success: bool,
    pub timestamp: DateTime<Utc>,
}

/// Parse a CSV row of harness records (provider,model,itokens,otokens,latency,success,timestamp).
pub fn parse_harness_csv_line(line: &str) -> Option<RawHarnessRecord> {
    let parts: Vec<&str> = line.split(',').collect();
    if parts.len() < 6 {
        return None;
    }
    let provider = parts[0].trim().to_string();
    let model = parts[1].trim().to_string();
    let input_tokens = parts[2].trim().parse().ok()?;
    let output_tokens = parts[3].trim().parse().ok()?;
    let latency_ms = parts[4].trim().parse().ok();
    let success = parts[5].trim().parse().ok()?;
    let timestamp = if parts.len() > 6 {
        DateTime::parse_from_rfc3339(parts[6].trim())
            .map(|dt| dt.with_timezone(&Utc))
            .ok()
    } else {
        Some(Utc::now())
    }?;
    Some(RawHarnessRecord {
        provider,
        model,
        input_tokens,
        output_tokens,
        latency_ms,
        success,
        timestamp,
    })
}

/// Format cost as a dollar string.
pub fn format_cost(cost: f64) -> String {
    if cost < 0.001 {
        format!("${:.6}", cost)
    } else if cost < 1.0 {
        format!("${:.4}", cost)
    } else {
        format!("${:.2}", cost)
    }
}

/// Format a percentage (0-100).
pub fn format_pct(pct: f64) -> String {
    format!("{:.2}%", pct)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_format_cost_micro() {
        assert_eq!(format_cost(0.0005), "$0.000500");
    }

    #[test]
    fn test_format_cost_sub_dollar() {
        assert_eq!(format_cost(0.5), "$0.5000");
    }

    #[test]
    fn test_format_cost_above_dollar() {
        assert_eq!(format_cost(12.345), "$12.35");
    }

    #[test]
    fn test_format_cost_zero() {
        assert_eq!(format_cost(0.0), "$0.000000");
    }

    #[test]
    fn test_format_cost_negative() {
        // negative cost is < 0.001, so uses 6 decimal format
        let result = format_cost(-0.5);
        assert!(result.starts_with('$'));
    }

    #[test]
    fn test_format_pct_basic() {
        assert_eq!(format_pct(50.0), "50.00%");
    }

    #[test]
    fn test_format_pct_zero() {
        assert_eq!(format_pct(0.0), "0.00%");
    }

    #[test]
    fn test_format_pct_large() {
        assert_eq!(format_pct(99.99), "99.99%");
    }

    #[test]
    fn test_parse_harness_csv_line_valid() {
        let line = "openai,gpt-4o,1000,500,150.0,true,2026-01-15T10:30:00Z";
        let record = parse_harness_csv_line(line).unwrap();
        assert_eq!(record.provider, "openai");
        assert_eq!(record.model, "gpt-4o");
        assert_eq!(record.input_tokens, 1000);
        assert_eq!(record.output_tokens, 500);
        assert_eq!(record.latency_ms, Some(150.0));
        assert!(record.success);
    }

    #[test]
    fn test_parse_harness_csv_line_too_few_fields() {
        let line = "openai,gpt-4o,1000";
        let result = parse_harness_csv_line(line);
        assert!(result.is_none());
    }

    #[test]
    fn test_parse_harness_csv_line_invalid_tokens() {
        let line = "openai,gpt-4o,not_a_number,500,150.0,true,2026-01-15T10:30:00Z";
        let result = parse_harness_csv_line(line);
        assert!(result.is_none());
    }

    #[test]
    fn test_parse_harness_csv_line_invalid_success() {
        let line = "openai,gpt-4o,1000,500,150.0,notabool,2026-01-15T10:30:00Z";
        let result = parse_harness_csv_line(line);
        assert!(result.is_none());
    }

    #[test]
    fn test_parse_harness_csv_line_no_timestamp() {
        // Without timestamp, uses Utc::now() as default
        let line = "openai,gpt-4o,1000,500,150.0,true";
        let result = parse_harness_csv_line(line);
        assert!(result.is_some());
    }

    #[test]
    fn test_parse_harness_csv_line_none_latency() {
        let line = "anthropic,claude-3,2000,800,,true,2026-01-15T10:30:00Z";
        let record = parse_harness_csv_line(line).unwrap();
        assert_eq!(record.latency_ms, None);
    }

    #[test]
    fn test_parse_harness_csv_line_false_success() {
        let line = "openai,gpt-4o,1000,500,150.0,false,2026-01-15T10:30:00Z";
        let record = parse_harness_csv_line(line).unwrap();
        assert!(!record.success);
    }
}
