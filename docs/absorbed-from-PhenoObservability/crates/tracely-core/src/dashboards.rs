//! Dashboard configuration and wiring stubs.

use serde::{Deserialize, Serialize};

/// Dashboard panel type.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum PanelKind {
    /// Time-series line chart.
    TimeSeries,
    /// Stat/single-value display.
    Stat,
    /// Table of spans.
    Table,
    /// Log stream view.
    Logs,
}

/// A single dashboard panel definition.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Panel {
    pub id: u32,
    pub title: String,
    pub kind: PanelKind,
    pub query: String,
}

/// A full dashboard definition.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Dashboard {
    pub uid: String,
    pub title: String,
    pub panels: Vec<Panel>,
}

impl Dashboard {
    pub fn new(uid: impl Into<String>, title: impl Into<String>) -> Self {
        Self {
            uid: uid.into(),
            title: title.into(),
            panels: Vec::new(),
        }
    }

    pub fn add_panel(&mut self, panel: Panel) -> &mut Self {
        self.panels.push(panel);
        self
    }
}

/// Wire dashboards to a backend (stub — backend integration pending).
///
/// Returns the list of dashboards that would be registered.
pub fn wire(dashboards: Vec<Dashboard>) -> Vec<String> {
    dashboards.iter().map(|d| d.uid.clone()).collect()
}

/// Build the default PhenoObservability dashboard set.
pub fn default_dashboards() -> Vec<Dashboard> {
    let mut spans = Dashboard::new("pheno-spans", "Span Explorer");
    spans.add_panel(Panel {
        id: 1,
        title: "Span Rate".into(),
        kind: PanelKind::TimeSeries,
        query: "rate(spans_total[1m])".into(),
    });
    spans.add_panel(Panel {
        id: 2,
        title: "P99 Latency".into(),
        kind: PanelKind::Stat,
        query: "histogram_quantile(0.99, spans_duration_ms)".into(),
    });

    let mut errors = Dashboard::new("pheno-errors", "Error Overview");
    errors.add_panel(Panel {
        id: 1,
        title: "Error Rate".into(),
        kind: PanelKind::TimeSeries,
        query: "rate(spans_errors_total[5m])".into(),
    });

    vec![spans, errors]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_dashboards_non_empty() {
        let dbs = default_dashboards();
        assert!(!dbs.is_empty());
    }

    #[test]
    fn wire_returns_uids() {
        let dbs = default_dashboards();
        let uids = wire(dbs);
        assert!(uids.contains(&"pheno-spans".to_string()));
        assert!(uids.contains(&"pheno-errors".to_string()));
    }

    #[test]
    fn dashboard_add_panel() {
        let mut d = Dashboard::new("test", "Test");
        d.add_panel(Panel {
            id: 1,
            title: "T".into(),
            kind: PanelKind::Stat,
            query: "q".into(),
        });
        assert_eq!(d.panels.len(), 1);
    }
}
