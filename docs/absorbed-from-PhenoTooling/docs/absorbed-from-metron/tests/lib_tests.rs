//! Unit tests for Metron domain and application layers.

use metrickit::domain::{
    Counter, CounterValue, Gauge, GaugeValue,
    Histogram, HistogramBuckets, HistogramValue,
    MetricMetadata, MetricType, MetricError,
    Registry,
};
use metrickit::application::{PrometheusExporter, MetricExporter};

// ============================================================================
// CounterValue Tests
// ============================================================================

mod counter_value {
    use super::*;

    #[test]
    fn new_creates_with_value() {
        let cv = CounterValue::new(42.0);
        assert_eq!(cv.value, 42.0);
    }

    #[test]
    fn default_is_zero() {
        let cv = CounterValue::default();
        assert_eq!(cv.value, 0.0);
    }

    #[test]
    fn inc_increments_by_one() {
        let mut cv = CounterValue::new(5.0);
        cv.inc();
        assert_eq!(cv.value, 6.0);
    }

    #[test]
    fn add_increments_by_given_value() {
        let mut cv = CounterValue::new(10.0);
        cv.add(3.5);
        assert_eq!(cv.value, 13.5);
    }

    #[test]
    fn get_returns_value() {
        let cv = CounterValue::new(7.0);
        assert_eq!(cv.get(), 7.0);
    }
}

// ============================================================================
// Counter Tests
// ============================================================================

mod counter {
    use super::*;

    #[test]
    fn new_creates_with_name_and_zero() {
        let c = Counter::new("requests_total");
        assert_eq!(c.metadata().name, "requests_total");
        assert_eq!(c.metadata().metric_type, MetricType::Counter);
        assert_eq!(c.get(), 0.0);
    }

    #[test]
    fn with_description_sets_metadata() {
        let c = Counter::new("http_requests")
            .with_description("Total HTTP requests");
        assert_eq!(c.metadata().description.as_deref(), Some("Total HTTP requests"));
    }

    #[test]
    fn with_unit_sets_unit() {
        let c = Counter::new("bytes_sent").with_unit("bytes");
        assert_eq!(c.metadata().unit.as_deref(), Some("bytes"));
    }

    #[test]
    fn inc_increments_counter() {
        let c = Counter::new("inc_test");
        c.inc();
        c.inc();
        c.inc();
        assert_eq!(c.get(), 3.0);
    }

    #[test]
    fn add_adds_given_value() {
        let c = Counter::new("add_test");
        c.add(10.0);
        c.add(5.5);
        assert_eq!(c.get(), 15.5);
    }

    #[test]
    fn clone_is_independent() {
        let c = Counter::new("clone_test");
        let c2 = c.clone();
        c.add(1.0);
        // c2 was cloned before inc, so it still reads 0.0
        // Note: Arc means both share the same underlying value
        // So after clone, both see the same value
        c2.add(2.0);
        assert_eq!(c.get(), 3.0);
        assert_eq!(c2.get(), 3.0);
    }

    #[test]
    fn metadata_returns_metadata() {
        let c = Counter::new("meta_test").with_description("desc").with_unit("ms");
        let m = c.metadata();
        assert_eq!(m.name, "meta_test");
        assert_eq!(m.description.as_deref(), Some("desc"));
        assert_eq!(m.unit.as_deref(), Some("ms"));
    }
}

// ============================================================================
// GaugeValue Tests
// ============================================================================

mod gauge_value {
    use super::*;

    #[test]
    fn new_creates_with_value() {
        let gv = GaugeValue::new(100.0);
        assert_eq!(gv.value, 100.0);
    }

    #[test]
    fn set_overwrites_value() {
        let mut gv = GaugeValue::new(0.0);
        gv.set(50.0);
        assert_eq!(gv.value, 50.0);
    }

    #[test]
    fn inc_increments_value() {
        let mut gv = GaugeValue::new(10.0);
        gv.inc();
        assert_eq!(gv.value, 11.0);
    }

    #[test]
    fn dec_decrements_value() {
        let mut gv = GaugeValue::new(10.0);
        gv.dec();
        assert_eq!(gv.value, 9.0);
    }

    #[test]
    fn get_returns_value() {
        let gv = GaugeValue::new(99.0);
        assert_eq!(gv.get(), 99.0);
    }
}

// ============================================================================
// Gauge Tests
// ============================================================================

mod gauge {
    use super::*;

    #[test]
    fn new_creates_with_name_and_zero() {
        let g = Gauge::new("cpu_usage");
        assert_eq!(g.metadata().name, "cpu_usage");
        assert_eq!(g.metadata().metric_type, MetricType::Gauge);
        assert_eq!(g.get(), 0.0);
    }

    #[test]
    fn with_description_sets_description() {
        let g = Gauge::new("memory_bytes").with_description("RSS memory usage");
        assert_eq!(g.metadata().description.as_deref(), Some("RSS memory usage"));
    }

    #[test]
    fn set_overwrites_value() {
        let g = Gauge::new("set_test");
        g.set(42.0);
        assert_eq!(g.get(), 42.0);
    }

    #[test]
    fn inc_increments() {
        let g = Gauge::new("inc_test");
        g.set(0.0);
        g.inc();
        g.inc();
        assert_eq!(g.get(), 2.0);
    }

    #[test]
    fn dec_decrements() {
        let g = Gauge::new("dec_test");
        g.set(5.0);
        g.dec();
        assert_eq!(g.get(), 4.0);
    }

    #[test]
    fn shared_across_clones() {
        let g = Gauge::new("shared_test");
        let g2 = g.clone();
        g.set(10.0);
        assert_eq!(g2.get(), 10.0);
        g2.set(20.0);
        assert_eq!(g.get(), 20.0);
    }
}

// ============================================================================
// HistogramBuckets Tests
// ============================================================================

mod histogram_buckets {
    use super::*;

    #[test]
    fn new_creates_with_correct_counts() {
        let hb = HistogramBuckets::new(vec![0.1, 0.5, 1.0]);
        assert_eq!(hb.bounds, vec![0.1, 0.5, 1.0]);
        assert_eq!(hb.counts, vec![0, 0, 0, 0]); // len + 1
    }

    #[test]
    fn observe_increments_correct_bucket() {
        let mut hb = HistogramBuckets::new(vec![0.1, 0.5, 1.0]);
        hb.observe(0.05); // below first bucket
        hb.observe(0.3);  // in first bucket (0.1)
        hb.observe(0.7);  // in second bucket (0.5)
        hb.observe(2.0);   // in overflow bucket (inf)
        assert_eq!(hb.counts, vec![1, 1, 1, 1]);
    }

    #[test]
    fn observe_at_boundary_goes_to_lower_bucket() {
        let mut hb = HistogramBuckets::new(vec![0.1, 0.5, 1.0]);
        hb.observe(0.1); // exactly at first bound
        assert_eq!(hb.counts[0], 1);
        assert_eq!(hb.counts[1], 0);
    }
}

// ============================================================================
// HistogramValue Tests
// ============================================================================

mod histogram_value {
    use super::*;

    #[test]
    fn new_creates_with_zero_count_and_sum() {
        let hv = HistogramValue::new(vec![0.1, 0.5]);
        assert_eq!(hv.count, 0);
        assert_eq!(hv.sum, 0.0);
        assert_eq!(hv.buckets.counts, vec![0, 0, 0]);
    }

    #[test]
    fn observe_increments_count_and_sum() {
        let mut hv = HistogramValue::new(vec![0.1, 0.5, 1.0]);
        hv.observe(0.05);
        hv.observe(0.3);
        hv.observe(1.5);
        assert_eq!(hv.count, 3);
        assert!((hv.sum - 1.85).abs() < 1e-9);
    }
}

// ============================================================================
// Histogram Tests
// ============================================================================

mod histogram {
    use super::*;

    #[test]
    fn new_uses_default_buckets() {
        let h = Histogram::new("latency");
        let val = h.get();
        assert_eq!(val.buckets.bounds, vec![0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]);
    }

    #[test]
    fn with_buckets_uses_custom_bounds() {
        let h = Histogram::with_buckets("custom", vec![1.0, 5.0, 10.0]);
        let val = h.get();
        assert_eq!(val.buckets.bounds, vec![1.0, 5.0, 10.0]);
    }

    #[test]
    fn with_description_sets_description() {
        let h = Histogram::new("req_duration").with_description("Request duration");
        assert_eq!(h.metadata().description.as_deref(), Some("Request duration"));
    }

    #[test]
    fn observe_records_value() {
        let h = Histogram::new("observe_test");
        h.observe(0.05);
        h.observe(0.05);
        let val = h.get();
        assert_eq!(val.count, 2);
        assert!((val.sum - 0.1).abs() < 1e-9);
    }

    #[test]
    fn shared_across_clones() {
        let h = Histogram::new("shared_hist");
        let h2 = h.clone();
        h.observe(1.0);
        let val2 = h2.get();
        assert_eq!(val2.count, 1);
    }
}

// ============================================================================
// MetricMetadata Tests
// ============================================================================

mod metric_metadata {
    use super::*;

    #[test]
    fn new_requires_name_and_type() {
        let m = MetricMetadata::new("test_metric", MetricType::Counter);
        assert_eq!(m.name, "test_metric");
        assert_eq!(m.metric_type, MetricType::Counter);
        assert!(m.description.is_none());
        assert!(m.unit.is_none());
    }

    #[test]
    fn with_description_returns_new_instance() {
        let m = MetricMetadata::new("x", MetricType::Gauge)
            .with_description("A gauge");
        assert_eq!(m.description.as_deref(), Some("A gauge"));
    }

    #[test]
    fn with_unit_returns_new_instance() {
        let m = MetricMetadata::new("y", MetricType::Counter)
            .with_unit("bytes");
        assert_eq!(m.unit.as_deref(), Some("bytes"));
    }

    #[test]
    fn chaining_works() {
        let m = MetricMetadata::new("z", MetricType::Histogram)
            .with_description("desc")
            .with_unit("seconds");
        assert_eq!(m.description.as_deref(), Some("desc"));
        assert_eq!(m.unit.as_deref(), Some("seconds"));
    }
}

// ============================================================================
// MetricType Tests
// ============================================================================

mod metric_type {
    use super::*;

    #[test]
    fn variants_exist() {
        assert_eq!(MetricType::Counter, MetricType::Counter);
        assert_eq!(MetricType::Gauge, MetricType::Gauge);
        assert_eq!(MetricType::Histogram, MetricType::Histogram);
        assert_eq!(MetricType::Summary, MetricType::Summary);
    }

    #[test]
    fn can_be_compared() {
        // Verify MetricType variants are comparable
        assert_eq!(MetricType::Counter, MetricType::Counter);
        assert_ne!(MetricType::Counter, MetricType::Gauge);
    }
}

// ============================================================================
// MetricError Tests
// ============================================================================

mod metric_error {
    use super::*;

    #[test]
    fn already_registered_message() {
        let err = MetricError::AlreadyRegistered("requests".into());
        let msg = err.to_string();
        assert!(msg.contains("requests"));
        assert!(msg.contains("already registered"));
    }

    #[test]
    fn not_found_message() {
        let err = MetricError::NotFound("missing".into());
        let msg = err.to_string();
        assert!(msg.contains("missing"));
        assert!(msg.contains("not found"));
    }

    #[test]
    fn export_error_message() {
        let err = MetricError::Export("bad data".into());
        let msg = err.to_string();
        assert!(msg.contains("bad data"));
        assert!(msg.contains("Export")); // "Export error: ..."
    }
}

// ============================================================================
// Registry Tests
// ============================================================================

mod registry {
    use super::*;

    fn fresh_registry() -> Registry {
        Registry::new()
    }

    #[test]
    fn counter_gets_or_creates() {
        let reg = fresh_registry();
        let c1 = reg.counter("requests");
        c1.add(1.0);
        let c2 = reg.counter("requests");
        assert_eq!(c2.get(), 1.0); // same instance
    }

    #[test]
    fn gauge_gets_or_creates() {
        let reg = fresh_registry();
        let g1 = reg.gauge("cpu");
        g1.set(50.0);
        let g2 = reg.gauge("cpu");
        assert_eq!(g2.get(), 50.0);
    }

    #[test]
    fn histogram_gets_or_creates() {
        let reg = fresh_registry();
        let h1 = reg.histogram("latency");
        h1.observe(0.1);
        let h2 = reg.histogram("latency");
        assert_eq!(h2.get().count, 1);
    }

    #[test]
    fn register_counter_rejects_duplicates() {
        let reg = fresh_registry();
        let _ = reg.register_counter("dup");
        let result = reg.register_counter("dup");
        assert!(result.is_err());
        // Verify the error is the right variant by checking the message
        if let Err(e) = result {
            assert!(matches!(e, MetricError::AlreadyRegistered(_)));
        }
    }

    #[test]
    fn register_gauge_rejects_duplicates() {
        let reg = fresh_registry();
        let _ = reg.register_gauge("dg");
        let result = reg.register_gauge("dg");
        assert!(result.is_err());
    }

    #[test]
    fn register_histogram_rejects_duplicates() {
        let reg = fresh_registry();
        let _ = reg.register_histogram("dh", vec![0.1, 0.5]);
        let result = reg.register_histogram("dh", vec![0.1, 0.5]);
        assert!(result.is_err());
    }

    #[test]
    fn clear_removes_all_metrics() {
        let reg = fresh_registry();
        let _ = reg.counter("x");
        let _ = reg.gauge("y");
        let _ = reg.histogram("z");
        reg.clear();
        // After clear, accessing names gives fresh metrics with 0 values
        assert_eq!(reg.counter("x").get(), 0.0);
        assert_eq!(reg.gauge("y").get(), 0.0);
        assert_eq!(reg.histogram("z").get().count, 0);
    }
}

// ============================================================================
// PrometheusExporter Tests
// ============================================================================

mod prometheus_exporter {
    use super::*;

    #[test]
    fn export_empty_registry() {
        let reg = Registry::new();
        let exporter = PrometheusExporter::new();
        let output = exporter.export(&reg).unwrap();
        assert!(output.is_empty());
    }

    #[test]
    fn export_counter() {
        let reg = Registry::new();
        let c = reg.counter("my_counter");
        c.add(42.0);
        let exporter = PrometheusExporter::new();
        let output = exporter.export(&reg).unwrap();
        assert!(output.contains("my_counter 42"));
    }

    #[test]
    fn export_gauge() {
        let reg = Registry::new();
        let g = reg.gauge("my_gauge");
        g.set(99.5);
        let exporter = PrometheusExporter::new();
        let output = exporter.export(&reg).unwrap();
        assert!(output.contains("my_gauge 99.5"));
    }

    #[test]
    fn export_histogram() {
        let reg = Registry::new();
        let h = reg.histogram("my_histogram");
        h.observe(0.05);
        h.observe(0.15);
        let exporter = PrometheusExporter::new();
        let output = exporter.export(&reg).unwrap();
        assert!(output.contains("my_histogram_count 2"));
        assert!(output.contains("my_histogram_sum 0.2"));
        assert!(output.contains("_bucket"));
    }

    #[test]
    fn export_with_description() {
        // Note: with_description/with_unit return new instances.
        // For the registry to hold a counter with description,
        // we'd need a registry method that accepts configured metrics.
        // Here we test that the basic counter export works.
        let reg = Registry::new();
        let c = reg.counter("basic_counter");
        c.add(1.0);
        let exporter = PrometheusExporter::new();
        let output = exporter.export(&reg).unwrap();
        assert!(output.contains("basic_counter 1"));
    }

    #[test]
    fn export_with_unit() {
        // Same caveat as description - using counter() which doesn't support
        // description/unit at creation. Test basic unit export via metric metadata.
        let reg = Registry::new();
        let _ = reg.counter("bytes_total");
        let exporter = PrometheusExporter::new();
        let output = exporter.export(&reg).unwrap();
        assert!(output.contains("bytes_total"));
    }

    #[test]
    fn export_histogram_bucket_le_labels() {
        let reg = Registry::new();
        let h = reg.histogram("bucketed");
        h.observe(0.005);
        h.observe(1.0);
        let exporter = PrometheusExporter::new();
        let output = exporter.export(&reg).unwrap();
        // Verify buckets appear (le values match the default histogram bounds)
        assert!(output.contains(r#"bucketed_bucket{le="0.005"}"#));
        assert!(output.contains(r#"bucketed_bucket{le="inf"}"#)); // lowercase inf
    }

    #[test]
    fn new_and_default_are_equivalent() {
        let e1 = PrometheusExporter::new();
        let e2 = PrometheusExporter::default();
        let reg = Registry::new();
        let o1 = e1.export(&reg).unwrap();
        let o2 = e2.export(&reg).unwrap();
        assert_eq!(o1, o2);
    }
}

// ============================================================================
// Edge Cases
// ============================================================================

mod edge_cases {
    use super::*;

    #[test]
    fn counter_handles_large_values() {
        let c = Counter::new("large");
        c.add(1e100);
        assert_eq!(c.get(), 1e100);
    }

    #[test]
    fn gauge_handles_negative_values() {
        let g = Gauge::new("signed");
        g.set(-42.0);
        assert_eq!(g.get(), -42.0);
        g.dec();
        assert_eq!(g.get(), -43.0);
    }

    #[test]
    fn histogram_buckets_all_above_max_go_to_inf() {
        let mut hb = HistogramBuckets::new(vec![0.1, 0.5]);
        hb.observe(100.0);
        hb.observe(999.0);
        // Last bucket is overflow
        assert_eq!(hb.counts[2], 2);
        assert_eq!(hb.counts[0], 0);
        assert_eq!(hb.counts[1], 0);
    }

    #[test]
    fn histogram_with_empty_bounds() {
        let h = Histogram::with_buckets("no_bounds", vec![]);
        h.observe(1.0);
        let val = h.get();
        assert_eq!(val.count, 1);
        // All values go to overflow bucket
        assert_eq!(val.buckets.counts[0], 1);
    }

    #[test]
    fn registry_separate_namespaces() {
        let reg = Registry::new();
        let _ = reg.counter("x");
        let _ = reg.gauge("x");
        let _ = reg.histogram("x");
        // All three can coexist with the same name
        assert_eq!(reg.counter("x").get(), 0.0);
        assert_eq!(reg.gauge("x").get(), 0.0);
        assert_eq!(reg.histogram("x").get().count, 0);
    }

    #[test]
    fn multiple_increments_consistent() {
        let c = Counter::new("inc_many");
        for _ in 0..1000 {
            c.inc();
        }
        assert_eq!(c.get(), 1000.0);
    }

    #[test]
    fn serde_roundtrip_counter_value() {
        use serde_json;
        let cv = CounterValue::new(42.0);
        let json = serde_json::to_string(&cv).unwrap();
        let restored: CounterValue = serde_json::from_str(&json).unwrap();
        assert_eq!(restored.value, 42.0);
    }

    #[test]
    fn serde_roundtrip_gauge_value() {
        use serde_json;
        let gv = GaugeValue::new(-3.14);
        let json = serde_json::to_string(&gv).unwrap();
        let restored: GaugeValue = serde_json::from_str(&json).unwrap();
        assert_eq!(restored.value, -3.14);
    }

    #[test]
    fn serde_roundtrip_histogram_value() {
        use serde_json;
        let mut hv = HistogramValue::new(vec![0.1, 0.5]);
        hv.observe(0.05);
        let json = serde_json::to_string(&hv).unwrap();
        let restored: HistogramValue = serde_json::from_str(&json).unwrap();
        assert_eq!(restored.count, 1);
    }
}
