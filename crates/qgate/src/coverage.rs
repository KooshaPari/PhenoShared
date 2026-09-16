// @trace QG-COV-001: granular-recursive coverage gate
//
// Tree-walk enforcement: a node passes only if its own line_rate ≥ threshold
// AND every child passes recursively. The overall average is never used to
// mask a low-coverage module — a single weak file sinks the whole gate.
//
// CoverageTree::all_pass() = all top-level nodes pass recursively.

use anyhow::Result;
use serde::{Deserialize, Serialize};

/// One node in the coverage tree — a file, package, or directory.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoverageNode {
    pub path: String,
    pub line_rate: f64,
    pub branch_rate: f64,
    pub lines_covered: u64,
    pub lines_valid: u64,
    pub children: Vec<CoverageNode>,
}

impl CoverageNode {
    /// True iff this node meets the threshold; children are not consulted.
    pub fn passes(&self, threshold: f64) -> bool {
        // line_rate is 0.0–1.0 in standard cobertura/lcov; threshold is 0–100.
        self.line_rate * 100.0 >= threshold
    }
}

/// Root coverage tree — threshold + top-level nodes.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoverageTree {
    pub threshold: f64,
    pub nodes: Vec<CoverageNode>,
}

impl CoverageTree {
    /// Recursive pass check — every node at every depth must meet threshold.
    pub fn all_pass(&self) -> bool {
        fn walk(node: &CoverageNode, threshold: f64) -> bool {
            if !node.passes(threshold) {
                return false;
            }
            node.children.iter().all(|c| walk(c, threshold))
        }
        self.nodes.iter().all(|n| walk(n, self.threshold))
    }

    /// Aggregate overall rate (weighted by lines_valid) — informational only.
    pub fn overall_rate(&self) -> f64 {
        fn sum(node: &CoverageNode, cov: &mut u64, valid: &mut u64) {
            *cov += node.lines_covered;
            *valid += node.lines_valid;
            for c in &node.children {
                sum(c, cov, valid);
            }
        }
        let mut cov = 0u64;
        let mut valid = 0u64;
        for n in &self.nodes {
            sum(n, &mut cov, &mut valid);
        }
        if valid == 0 {
            0.0
        } else {
            cov as f64 / valid as f64
        }
    }

    /// Render the tree as a human-readable ASCII summary.
    pub fn render_tree(&self) -> String {
        let mut out = String::new();
        out.push_str(&format!(
            "Coverage Tree (threshold {:.1}%)\n",
            self.threshold
        ));
        out.push_str(&format!("  Overall: {:.1}%\n", self.overall_rate() * 100.0));
        for n in &self.nodes {
            render_node(n, &mut out, 1);
        }
        out
    }
}

fn render_node(node: &CoverageNode, out: &mut String, depth: usize) {
    let pad = "  ".repeat(depth);
    let mark = if node.passes(node.lines_valid_pseudo_threshold()) {
        "PASS"
    } else {
        "FAIL"
    };
    // Use a generous marker — the node's own passes check uses the tree
    // threshold. For per-node rendering, use a simple >= 80% heuristic so
    // the rendered marker reflects "ok looking" vs "weak".
    out.push_str(&format!(
        "{pad}[{mark}] {}  {:.1}%  ({}/{})\n",
        node.path,
        node.line_rate * 100.0,
        node.lines_covered,
        node.lines_valid,
    ));
    for c in &node.children {
        render_node(c, out, depth + 1);
    }
}

// Helper used in render_node — kept private, not part of the public API.
trait NodeThreshold {
    fn lines_valid_pseudo_threshold(&self) -> f64;
}
impl NodeThreshold for CoverageNode {
    fn lines_valid_pseudo_threshold(&self) -> f64 {
        // We don't have a tree-threshold handle on the node, so use 80% as
        // a neutral visual marker — exact pass/fail is computed by
        // CoverageTree::all_pass at the gate.
        80.0
    }
}

// ─── Parsers ───────────────────────────────────────────────────────────────

/// Parse a Cobertura XML report into a coverage tree.
pub fn parse_cobertura(content: &str, threshold: f64) -> Result<CoverageTree> {
    use serde::Deserialize;
    #[derive(Debug, Deserialize)]
    struct CoberturaClass {
        #[serde(rename = "@filename")]
        filename: String,
        #[serde(rename = "@line-rate")]
        line_rate: Option<f64>,
        #[serde(rename = "@branch-rate")]
        branch_rate: Option<f64>,
    }
    #[derive(Debug, Deserialize)]
    struct CoberturaPackage {
        #[serde(rename = "@name")]
        name: String,
        #[serde(rename = "@line-rate")]
        line_rate: Option<f64>,
        #[serde(rename = "@branch-rate")]
        branch_rate: Option<f64>,
        classes: Option<CoberturaClasses>,
    }
    #[derive(Debug, Deserialize)]
    #[serde(rename_all = "lowercase")]
    struct CoberturaClasses {
        #[serde(default)]
        class: Vec<CoberturaClass>,
    }
    #[derive(Debug, Deserialize)]
    struct CoberturaPackages {
        #[serde(default)]
        package: Vec<CoberturaPackage>,
    }
    #[derive(Debug, Deserialize)]
    #[serde(rename_all = "lowercase")]
    struct CoberturaRoot {
        #[serde(rename = "@line-rate")]
        line_rate: f64,
        #[serde(rename = "@branch-rate")]
        branch_rate: f64,
        #[serde(rename = "@lines-covered", default)]
        lines_covered: u64,
        #[serde(rename = "@lines-valid", default)]
        lines_valid: u64,
        #[serde(default)]
        packages: Option<CoberturaPackages>,
    }

    let root: CoberturaRoot = quick_xml::de::from_str(content)
        .map_err(|e| anyhow::anyhow!("cobertura parse error: {e}"))?;

    let mut nodes: Vec<CoverageNode> = Vec::new();
    if let Some(pkgs) = root.packages {
        for pkg in pkgs.package {
            let mut children = Vec::new();
            if let Some(cls) = pkg.classes {
                for c in cls.class {
                    children.push(CoverageNode {
                        path: c.filename,
                        line_rate: c.line_rate.unwrap_or(0.0),
                        branch_rate: c.branch_rate.unwrap_or(0.0),
                        lines_covered: 0,
                        lines_valid: 0,
                        children: vec![],
                    });
                }
            }
            nodes.push(CoverageNode {
                path: pkg.name,
                line_rate: pkg.line_rate.unwrap_or(root.line_rate),
                branch_rate: pkg.branch_rate.unwrap_or(root.branch_rate),
                lines_covered: root.lines_covered,
                lines_valid: root.lines_valid,
                children,
            });
        }
    } else {
        // No packages — synthesize a single root node so the tree isn't empty.
        nodes.push(CoverageNode {
            path: ".".into(),
            line_rate: root.line_rate,
            branch_rate: root.branch_rate,
            lines_covered: root.lines_covered,
            lines_valid: root.lines_valid,
            children: vec![],
        });
    }

    Ok(CoverageTree { threshold, nodes })
}

/// Parse an lcov tracefile into a coverage tree.
pub fn parse_lcov(content: &str, threshold: f64) -> Result<CoverageTree> {
    let mut nodes: Vec<CoverageNode> = Vec::new();
    let mut current_path: Option<String> = None;
    let mut lines_covered: u64 = 0;
    let mut lines_valid: u64 = 0;
    let mut branch_rate_sum: f64 = 0.0;
    let mut branch_rate_n: u64 = 0;

    for line in content.lines() {
        let line = line.trim();
        if let Some(p) = line.strip_prefix("SF:") {
            // New source file — flush the previous one.
            if let Some(path) = current_path.take() {
                let line_rate = if lines_valid == 0 {
                    0.0
                } else {
                    lines_covered as f64 / lines_valid as f64
                };
                let branch_rate = if branch_rate_n == 0 {
                    0.0
                } else {
                    branch_rate_sum / branch_rate_n as f64
                };
                nodes.push(CoverageNode {
                    path,
                    line_rate,
                    branch_rate,
                    lines_covered,
                    lines_valid,
                    children: vec![],
                });
            }
            current_path = Some(p.to_string());
            lines_covered = 0;
            lines_valid = 0;
            branch_rate_sum = 0.0;
            branch_rate_n = 0;
        } else if let Some(rest) = line.strip_prefix("DA:") {
            // DA:<line>,<count>[,<checksum>]
            let mut parts = rest.split(',');
            let _lineno = parts.next();
            let count_str = parts.next().unwrap_or("0");
            let count: u64 = count_str.parse().unwrap_or(0);
            lines_valid += 1;
            if count > 0 {
                lines_covered += 1;
            }
        } else if let Some(rest) = line.strip_prefix("BRDA:") {
            // BRDA:<line>,<block>,<branch>,<count>
            let mut parts = rest.split(',');
            let _lineno = parts.next();
            let _block = parts.next();
            let _branch = parts.next();
            let count_str = parts.next().unwrap_or("-");
            branch_rate_n += 1;
            if count_str != "-" && count_str.parse::<u64>().unwrap_or(0) > 0 {
                branch_rate_sum += 1.0;
            }
        }
    }
    if let Some(path) = current_path.take() {
        let line_rate = if lines_valid == 0 {
            0.0
        } else {
            lines_covered as f64 / lines_valid as f64
        };
        let branch_rate = if branch_rate_n == 0 {
            0.0
        } else {
            branch_rate_sum / branch_rate_n as f64
        };
        nodes.push(CoverageNode {
            path,
            line_rate,
            branch_rate,
            lines_covered,
            lines_valid,
            children: vec![],
        });
    }

    Ok(CoverageTree { threshold, nodes })
}

/// Parse a JSON coverage report. Supports two common shapes:
///   1) `{ "files": [ { "path": "...", "line_rate": 0.9, ... } ] }`
///   2) istanbul-style: `{ "src/lib.rs": { "s": {...}, "b": {...}, ... } }`
pub fn parse_json_coverage(content: &str, threshold: f64) -> Result<CoverageTree> {
    let v: serde_json::Value = serde_json::from_str(content)
        .map_err(|e| anyhow::anyhow!("json coverage parse error: {e}"))?;

    if let Some(files) = v.get("files").and_then(|f| f.as_array()) {
        let mut nodes: Vec<CoverageNode> = Vec::new();
        for f in files {
            let path = f
                .get("path")
                .and_then(|p| p.as_str())
                .unwrap_or("?")
                .to_string();
            let line_rate = f.get("line_rate").and_then(|x| x.as_f64()).unwrap_or(0.0);
            let branch_rate = f.get("branch_rate").and_then(|x| x.as_f64()).unwrap_or(0.0);
            let lines_covered = f.get("lines_covered").and_then(|x| x.as_u64()).unwrap_or(0);
            let lines_valid = f.get("lines_valid").and_then(|x| x.as_u64()).unwrap_or(0);
            nodes.push(CoverageNode {
                path,
                line_rate,
                branch_rate,
                lines_covered,
                lines_valid,
                children: vec![],
            });
        }
        return Ok(CoverageTree { threshold, nodes });
    }

    // Istanbul fallback — { "<file>": { "s": { "<line>": <count> }, ... } }
    if let Some(obj) = v.as_object() {
        let mut nodes: Vec<CoverageNode> = Vec::new();
        for (path, body) in obj {
            let stmt_map = body.get("s").and_then(|s| s.as_object());
            let (lines_covered, lines_valid) = if let Some(s) = stmt_map {
                let mut cov = 0u64;
                let mut valid = 0u64;
                for (_, count) in s {
                    valid += 1;
                    if count.as_u64().unwrap_or(0) > 0 {
                        cov += 1;
                    }
                }
                (cov, valid)
            } else {
                (0, 0)
            };
            let line_rate = if lines_valid == 0 {
                0.0
            } else {
                lines_covered as f64 / lines_valid as f64
            };
            nodes.push(CoverageNode {
                path: path.clone(),
                line_rate,
                branch_rate: 0.0,
                lines_covered,
                lines_valid,
                children: vec![],
            });
        }
        return Ok(CoverageTree { threshold, nodes });
    }

    Ok(CoverageTree {
        threshold,
        nodes: vec![],
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_tree_passes() {
        let tree = CoverageTree {
            threshold: 85.0,
            nodes: vec![],
        };
        assert!(tree.all_pass());
    }

    #[test]
    fn parse_lcov_basic() {
        let lcov = "TN:\nSF:src/lib.rs\nDA:1,1\nDA:2,0\nLH:1\nLF:2\nend_of_record\n";
        let tree = parse_lcov(lcov, 85.0).expect("parse should succeed");
        assert_eq!(tree.nodes.len(), 1);
        assert!(!tree.all_pass()); // 50% below threshold
    }

    #[test]
    fn parse_cobertura_basic() {
        let xml = r#"<?xml version="1.0"?>
<coverage line-rate="0.90" branch-rate="0.88" lines-covered="90" lines-valid="100">
  <packages>
    <package name="src" line-rate="0.90" branch-rate="0.88">
      <classes>
        <class name="lib" filename="src/lib.rs" line-rate="0.90" branch-rate="0.88"/>
      </classes>
    </package>
  </packages>
</coverage>"#;
        let tree = parse_cobertura(xml, 85.0).expect("parse should succeed");
        assert!(tree.all_pass()); // 90% >= 85%
    }
}
