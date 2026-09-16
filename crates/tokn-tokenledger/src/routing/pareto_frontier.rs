//! Pareto frontier computation — Rust port of `helios_router/pareto/engine.py`.
//!
//! Provides a generalized O(N²) Pareto mask with arbitrary minimize / maximize
//! objectives. Replaces the simpler weighted-sum scoring in [`super::pareto_router`]
//! with a proper non-dominated sort suitable for multi-objective model selection.
//!
//! Origin: `KooshaPari/helios-cli/src/helios_router_ui/pareto/engine.py`
//! Migration date: 2026-06-20 (T35).
//!
//! # Algorithm
//!
//! An offer A **dominates** B if:
//! - A is no worse than B on every objective, AND
//! - A is strictly better than B on at least one objective.
//!
//! The Pareto frontier is the set of offers that are not dominated by any
//! other offer. Used for selecting the optimal set of (cost, quality, speed)
//! offers without requiring the operator to pre-specify weights.
//!
//! # Example
//!
//! ```rust
//! use tokenledger::routing::pareto_frontier::{
//!     compute_pareto, ParetoOffer, ParetoObjective,
//! };
//!
//! let offers = vec![
//!     ParetoOffer::new("openai/gpt-4o", 0.95, 5.0, 120.0),
//!     ParetoOffer::new("anthropic/claude-sonnet", 0.93, 3.0, 100.0),
//!     ParetoOffer::new("google/gemini-flash", 0.85, 0.5, 200.0),
//! ];
//! let result = compute_pareto(&offers, true, true, true);
//! assert!(result.frontier_count >= 2);
//! ```

use serde::{Deserialize, Serialize};

/// Objective direction for a single attribute.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ParetoObjective {
    /// Lower attribute values are better (e.g. cost, latency).
    Minimize,
    /// Higher attribute values are better (e.g. quality, throughput).
    Maximize,
}

/// A single candidate offer with arbitrary numeric attributes.
///
/// Attributes are stored as (name, value) pairs so the frontier algorithm
/// is decoupled from any specific schema. Callers convert their domain
/// types (e.g. `BenchmarkData`) into `ParetoOffer` at the adapter boundary.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ParetoOffer {
    /// Stable identifier (e.g. `"openai/gpt-4o"`).
    pub offer_id: String,
    /// Provider slug (optional but recommended for downstream consumers).
    pub provider: Option<String>,
    /// Model id (optional).
    pub model_id: Option<String>,
    /// Named numeric attributes (e.g. `("cost_usd", 0.005)`).
    pub attributes: Vec<(String, f64)>,
}

impl ParetoOffer {
    /// Convenience constructor with the three canonical router attributes:
    /// `quality`, `cost_usd`, `speed_score`.
    ///
    /// This matches the `compute_pareto` defaults used in the Python source.
    pub fn new(offer_id: &str, quality: f64, cost_usd: f64, speed_score: f64) -> Self {
        Self {
            offer_id: offer_id.to_string(),
            provider: None,
            model_id: None,
            attributes: vec![
                ("quality".to_string(), quality),
                ("cost_usd".to_string(), cost_usd),
                ("speed_score".to_string(), speed_score),
            ],
        }
    }

    /// Look up an attribute value by name.
    pub fn attribute(&self, name: &str) -> Option<f64> {
        self.attributes
            .iter()
            .find(|(n, _)| n == name)
            .map(|(_, v)| *v)
    }
}

/// Result of a Pareto computation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParetoResult {
    /// Indices of offers on the Pareto frontier (zero-based, in input order).
    pub frontier_indices: Vec<usize>,
    /// Total number of offers considered.
    pub total_count: usize,
    /// Number of offers on the frontier.
    pub frontier_count: usize,
    /// Objective set used for the computation.
    pub objectives: Vec<(String, ParetoObjective)>,
}

/// Aggregate metrics for a k-sized combination of offers.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ParetoCombo {
    /// `offer_id` of each member of the combo.
    pub combo: Vec<String>,
    /// Mean of `quality` across members (if all members have the attribute).
    pub quality: Option<f64>,
    /// Sum of `cost_usd` across members (if all members have the attribute).
    pub cost_usd: Option<f64>,
    /// Min of `speed_score` across members (slowest member is the bottleneck).
    pub speed_score: Option<f64>,
    /// Distinct providers in the combo.
    pub providers: Vec<String>,
    /// Distinct models in the combo.
    pub models: Vec<String>,
}

/// Compute the Pareto frontier mask.
///
/// Returns a `Vec<bool>` parallel to `offers`: `true` means the offer at that
/// index is non-dominated (on the frontier); `false` means it is dominated.
///
/// `objectives` is a list of `(attribute_name, direction)` pairs. Missing
/// attributes are treated as `f64::INFINITY` for `Minimize` and
/// `-f64::INFINITY` for `Maximize`, so they never cause an offer to dominate
/// over one that has the attribute set.
///
/// # Complexity
///
/// O(N²) where N is `offers.len()`. Suitable for N up to ~10,000 in-process;
/// beyond that, use a sweepline or NSGA-II algorithm.
pub fn pareto_front_mask(
    offers: &[ParetoOffer],
    objectives: &[(String, ParetoObjective)],
) -> Vec<bool> {
    let n = offers.len();
    let mut keep = vec![true; n];

    if n == 0 || objectives.is_empty() {
        return keep;
    }

    // Extract attribute values once, with sentinel handling.
    let values: Vec<Vec<f64>> = offers
        .iter()
        .map(|o| {
            objectives
                .iter()
                .map(|(name, dir)| match (o.attribute(name), dir) {
                    (Some(v), _) if v.is_finite() => v,
                    (None, ParetoObjective::Minimize) => f64::INFINITY,
                    (None, ParetoObjective::Maximize) => f64::NEG_INFINITY,
                    // Non-finite (NaN/inf) values are treated as missing.
                    (_, ParetoObjective::Minimize) => f64::INFINITY,
                    (_, ParetoObjective::Maximize) => f64::NEG_INFINITY,
                })
                .collect()
        })
        .collect();

    for i in 0..n {
        if !keep[i] {
            continue;
        }
        for j in 0..n {
            if i == j || !keep[i] {
                continue;
            }
            let mut no_worse = true;
            let mut strict_better = false;
            for (k, (_name, dir)) in objectives.iter().enumerate() {
                let vi = values[i][k];
                let vj = values[j][k];
                match dir {
                    ParetoObjective::Minimize => {
                        if vj > vi {
                            no_worse = false;
                            break;
                        }
                        if vj < vi {
                            strict_better = true;
                        }
                    }
                    ParetoObjective::Maximize => {
                        if vj < vi {
                            no_worse = false;
                            break;
                        }
                        if vj > vi {
                            strict_better = true;
                        }
                    }
                }
            }
            if no_worse && strict_better {
                keep[i] = false;
            }
        }
    }
    keep
}

/// Compute the Pareto frontier using the canonical router defaults.
///
/// Defaults (matching `compute_pareto` in the Python source):
/// - `minimize_cost=true` → objective `cost_usd` (Minimize)
/// - `minimize_speed=true` → objective `speed_score` (Minimize, lower = faster latency proxy)
/// - `maximize_quality=true` → objective `quality` (Maximize)
///
/// Any flag set to `false` removes that attribute from the objective set.
pub fn compute_pareto(
    offers: &[ParetoOffer],
    minimize_cost: bool,
    minimize_speed: bool,
    maximize_quality: bool,
) -> ParetoResult {
    let mut objectives: Vec<(String, ParetoObjective)> = Vec::with_capacity(3);
    if minimize_cost {
        objectives.push(("cost_usd".to_string(), ParetoObjective::Minimize));
    }
    if minimize_speed {
        objectives.push(("speed_score".to_string(), ParetoObjective::Minimize));
    }
    if maximize_quality {
        objectives.push(("quality".to_string(), ParetoObjective::Maximize));
    }

    let mask = pareto_front_mask(offers, &objectives);
    let frontier_indices: Vec<usize> = mask
        .iter()
        .enumerate()
        .filter_map(|(i, &k)| if k { Some(i) } else { None })
        .collect();
    let frontier_count = frontier_indices.len();

    ParetoResult {
        frontier_indices,
        total_count: offers.len(),
        frontier_count,
        objectives,
    }
}

/// Compute combination indices (pairs / trios / k-tuples) with aggregate metrics.
///
/// Each combo reports:
/// - `quality` — mean across members (if all members have the attribute)
/// - `cost_usd` — sum across members
/// - `speed_score` — min across members (slowest member is the bottleneck)
/// - `providers`, `models` — distinct values across members
///
/// Returns an empty `Vec` if `offers.len() < size`.
pub fn compute_combos(offers: &[ParetoOffer], size: usize) -> Vec<ParetoCombo> {
    if size == 0 || offers.len() < size {
        return Vec::new();
    }

    // Iterative k-combination generator (avoids pulling in itertools as a
    // workspace dependency for one helper).
    let mut indices: Vec<usize> = (0..size).collect();
    let mut combos: Vec<ParetoCombo> = Vec::new();

    loop {
        combos.push(combo_from_indices(offers, &indices));

        // Advance to next combination (lexicographic).
        let mut i = size;
        loop {
            if i == 0 {
                return combos;
            }
            i -= 1;
            if indices[i] != i + offers.len() - size {
                break;
            }
        }
        indices[i] += 1;
        for j in (i + 1)..size {
            indices[j] = indices[j - 1] + 1;
        }
    }
}

fn combo_from_indices(offers: &[ParetoOffer], indices: &[usize]) -> ParetoCombo {
    let members: Vec<&ParetoOffer> = indices.iter().map(|&i| &offers[i]).collect();

    let quality_values: Vec<f64> = members
        .iter()
        .filter_map(|o| o.attribute("quality"))
        .collect();
    let quality = if quality_values.len() == members.len() {
        Some(quality_values.iter().sum::<f64>() / members.len() as f64)
    } else {
        None
    };

    let cost_values: Vec<f64> = members
        .iter()
        .filter_map(|o| o.attribute("cost_usd"))
        .collect();
    let cost_usd = if cost_values.len() == members.len() {
        Some(cost_values.iter().sum())
    } else {
        None
    };

    let speed_values: Vec<f64> = members
        .iter()
        .filter_map(|o| o.attribute("speed_score"))
        .collect();
    let speed_score = if !speed_values.is_empty() {
        speed_values.iter().copied().reduce(f64::min)
    } else {
        None
    };

    let mut providers: Vec<String> = members
        .iter()
        .filter_map(|o| o.provider.clone())
        .collect::<std::collections::BTreeSet<_>>()
        .into_iter()
        .collect();
    providers.sort();

    let mut models: Vec<String> = members
        .iter()
        .filter_map(|o| o.model_id.clone())
        .collect::<std::collections::BTreeSet<_>>()
        .into_iter()
        .collect();
    models.sort();

    ParetoCombo {
        combo: members.iter().map(|o| o.offer_id.clone()).collect(),
        quality,
        cost_usd,
        speed_score,
        providers,
        models,
    }
}

// =============================================================================
// UNIT TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    fn offers_simple() -> Vec<ParetoOffer> {
        vec![
            ParetoOffer::new("a", 0.9, 5.0, 100.0),
            ParetoOffer::new("b", 0.8, 4.0, 120.0),
            ParetoOffer::new("c", 0.7, 6.0, 80.0),
        ]
    }

    #[test]
    fn test_pareto_front_mask_empty() {
        let offers: Vec<ParetoOffer> = Vec::new();
        let mask = pareto_front_mask(
            &offers,
            &[("cost_usd".to_string(), ParetoObjective::Minimize)],
        );
        assert!(mask.is_empty());
    }

    #[test]
    fn test_pareto_front_mask_no_objectives() {
        let mask = pareto_front_mask(&offers_simple(), &[]);
        assert_eq!(mask, vec![true, true, true]);
    }

    #[test]
    fn test_pareto_front_mask_three_classic() {
        // a: high quality, high cost
        // b: medium quality, medium cost, faster speed (lower speed_score = faster)
        // c: low quality, high cost, slowest
        // All three should be on the frontier for (quality↑, cost↓, speed↓)
        let mask = pareto_front_mask(
            &offers_simple(),
            &[
                ("quality".to_string(), ParetoObjective::Maximize),
                ("cost_usd".to_string(), ParetoObjective::Minimize),
                ("speed_score".to_string(), ParetoObjective::Minimize),
            ],
        );
        assert_eq!(mask, vec![true, true, true]);
    }

    #[test]
    fn test_pareto_front_mask_dominated() {
        // d is dominated by a on every axis (lower quality, higher cost, slower)
        let offers = vec![
            ParetoOffer::new("a", 0.9, 5.0, 100.0),
            ParetoOffer::new("d", 0.6, 7.0, 150.0),
        ];
        let mask = pareto_front_mask(
            &offers,
            &[
                ("quality".to_string(), ParetoObjective::Maximize),
                ("cost_usd".to_string(), ParetoObjective::Minimize),
                ("speed_score".to_string(), ParetoObjective::Minimize),
            ],
        );
        assert_eq!(mask, vec![true, false]);
    }

    #[test]
    fn test_pareto_front_mask_missing_attribute_treated_as_worst() {
        // Offer with missing "quality" should never dominate a peer that has it.
        let mut a = ParetoOffer::new("a", 0.9, 5.0, 100.0);
        let b = ParetoOffer {
            offer_id: "b".to_string(),
            provider: None,
            model_id: None,
            attributes: vec![
                ("cost_usd".to_string(), 6.0),
                ("speed_score".to_string(), 120.0),
            ],
        };
        let _ = &mut a;
        let offers = vec![a, b];

        let mask = pareto_front_mask(
            &offers,
            &[
                ("quality".to_string(), ParetoObjective::Maximize),
                ("cost_usd".to_string(), ParetoObjective::Minimize),
                ("speed_score".to_string(), ParetoObjective::Minimize),
            ],
        );
        // a has quality=0.9 (best); b has missing quality -> -inf for Maximize
        // so b is dominated by a on quality alone -> a stays, b is removed.
        assert_eq!(mask, vec![true, false]);
    }

    #[test]
    fn test_compute_pareto_default() {
        let offers = vec![
            ParetoOffer::new("openai/gpt-4o", 0.95, 5.0, 100.0),
            ParetoOffer::new("anthropic/claude-sonnet", 0.93, 3.0, 90.0),
            ParetoOffer::new("google/gemini-flash", 0.85, 0.5, 200.0),
            // dominated: worse quality AND higher cost than gpt-4o
            ParetoOffer::new("dominated/x", 0.50, 8.0, 150.0),
        ];
        let result = compute_pareto(&offers, true, true, true);
        assert_eq!(result.total_count, 4);
        assert_eq!(result.frontier_count, 3);
        assert_eq!(result.frontier_indices, vec![0, 1, 2]);
        assert_eq!(result.objectives.len(), 3);
    }

    #[test]
    fn test_compute_pareto_quality_only() {
        let offers = vec![
            ParetoOffer::new("a", 0.9, 5.0, 100.0),
            ParetoOffer::new("b", 0.8, 4.0, 120.0),
        ];
        let result = compute_pareto(&offers, false, false, true);
        // Only quality matters: a dominates b on quality alone.
        assert_eq!(result.frontier_indices, vec![0]);
        assert_eq!(result.objectives.len(), 1);
    }

    #[test]
    fn test_compute_combos_pairs() {
        let offers = vec![
            ParetoOffer::new("a", 0.9, 1.0, 100.0),
            ParetoOffer::new("b", 0.8, 2.0, 80.0),
            ParetoOffer::new("c", 0.7, 3.0, 60.0),
        ];
        let combos = compute_combos(&offers, 2);
        assert_eq!(combos.len(), 3); // C(3,2) = 3

        let first = &combos[0];
        assert_eq!(first.combo, vec!["a".to_string(), "b".to_string()]);
        assert!((first.quality.unwrap() - 0.85).abs() < 1e-9);
        assert!((first.cost_usd.unwrap() - 3.0).abs() < 1e-9);
        assert_eq!(first.speed_score, Some(80.0));
    }

    #[test]
    fn test_compute_combos_trios() {
        let offers = vec![
            ParetoOffer::new("a", 0.9, 1.0, 100.0),
            ParetoOffer::new("b", 0.8, 2.0, 80.0),
            ParetoOffer::new("c", 0.7, 3.0, 60.0),
        ];
        let combos = compute_combos(&offers, 3);
        assert_eq!(combos.len(), 1);
        assert!((combos[0].quality.unwrap() - 0.8).abs() < 1e-9);
        assert!((combos[0].cost_usd.unwrap() - 6.0).abs() < 1e-9);
        assert_eq!(combos[0].speed_score, Some(60.0));
    }

    #[test]
    fn test_compute_combos_too_small() {
        let offers = vec![ParetoOffer::new("a", 0.9, 1.0, 100.0)];
        assert!(compute_combos(&offers, 2).is_empty());
        assert!(compute_combos(&offers, 0).is_empty());
    }

    #[test]
    fn test_pareto_offer_attribute_lookup() {
        let o = ParetoOffer::new("test", 0.5, 1.0, 100.0);
        assert_eq!(o.attribute("quality"), Some(0.5));
        assert_eq!(o.attribute("missing"), None);
    }

    #[test]
    fn test_pareto_frontier_known_scenario() {
        // Canonical 5-offer scenario with consistent speed_score semantics
        // (lower speed_score = faster, matching the Python source's
        // `minimize_speed=True` convention).
        //
        // premium: high quality, high cost, moderate latency
        // balanced: medium quality, medium cost, low latency
        // fast-cheap: low quality, low cost, high latency
        // dominated-by-balanced: lower quality, higher cost, higher latency than balanced
        //   -> strictly dominated by balanced on every axis
        // dominated-by-fast-cheap: lower quality, higher cost, higher latency than fast-cheap
        //   -> strictly dominated by fast-cheap on every axis
        let offers = vec![
            ParetoOffer::new("premium", 0.95, 10.0, 100.0),
            ParetoOffer::new("balanced", 0.85, 5.0, 80.0),
            ParetoOffer::new("fast-cheap", 0.70, 1.0, 200.0),
            ParetoOffer::new("dominated-by-balanced", 0.75, 6.0, 90.0),
            ParetoOffer::new("dominated-by-fast-cheap", 0.50, 2.0, 210.0),
        ];
        let result = compute_pareto(&offers, true, true, true);
        assert_eq!(result.frontier_count, 3);
        assert_eq!(result.frontier_indices, vec![0, 1, 2]);
    }
}
