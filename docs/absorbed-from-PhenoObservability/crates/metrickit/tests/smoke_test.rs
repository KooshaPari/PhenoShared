// Traces to: FR-001
#[test]
fn smoke_test_loads() {
    use metrickit::domain::MetricType;
    assert_eq!(MetricType::Counter, MetricType::Counter);
}
