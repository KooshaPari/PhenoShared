use std::time::Duration;

use phenotype_time::DurationExt;

#[test]
fn format_human_zero_seconds() {
    assert_eq!(Duration::seconds(0).format_human(), "0s");
}

#[test]
fn format_human_single_second() {
    assert_eq!(Duration::seconds(1).format_human(), "1s");
}

#[test]
fn format_human_minutes_and_seconds() {
    assert_eq!(Duration::seconds(125).format_human(), "2m 5s");
}

#[test]
fn format_human_hours_minutes_seconds() {
    assert_eq!(Duration::seconds(3661).format_human(), "1h 1m 1s");
}

#[test]
fn format_human_days_hours_minutes_seconds() {
    assert_eq!(Duration::seconds(90061).format_human(), "1d 1h 1m 1s");
}

#[test]
fn format_human_only_days() {
    assert_eq!(Duration::days(3).format_human(), "3d");
}

#[test]
fn format_human_only_hours() {
    assert_eq!(Duration::hours(5).format_human(), "5h");
}

#[test]
fn format_human_only_minutes() {
    assert_eq!(Duration::minutes(10).format_human(), "10m");
}
