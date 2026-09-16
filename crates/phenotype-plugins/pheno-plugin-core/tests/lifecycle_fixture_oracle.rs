//! Fixture-driven oracle for `pheno_plugin_core::lifecycle::PluginState`.
//!
//! The 5×5 transition table is duplicated as a JSON fixture under
//! `tests/fixtures/lifecycle_state_machine.json` so that downstream plugin
//! authors (and this crate's own consumers) can consume the contract as
//! data — useful for code generation, conformance suites, and static
//! analyzers. This test loads that fixture and asserts that the
//! in-code `PluginState::can_transition_to` / `PluginState::transition`
//! implementation matches every row of the fixture.
//!
//! Why an external fixture, not a hardcoded table?
//!
//! 1. A regression in any of the 25 transition cells breaks at least one
//!    test case here with a precise cell-level error message instead of
//!    a single "25 expected" diff.
//! 2. The fixture can be diffed in code review when the state machine
//!    changes; the rationale strings double as living documentation.
//! 3. Consumers can parse the same fixture to generate their own
//!    state-machine diagrams or migration guides without having to
//!    scrape Rust source.
//!
//! Adding a new `PluginState` variant requires updating both the in-code
//! `matches!` in `can_transition_to` AND this fixture (5 new rows). The
//! fixture loader also asserts the row count matches the state count
//! squared, so a missed row causes a build-time failure.
//!
//! ## Docstring coverage
//!
//! Every public item the fixture depends on is exercised by at least
//! one test below:
//!
//! | Symbol                        | Test                                       |
//! |-------------------------------|--------------------------------------------|
//! | `PluginState` (variants)      | `test_fixture_schema_is_well_formed`       |
//! | `PluginState::as_str`         | `test_fixture_forbidden_transitions_*`     |
//! | `PluginState::can_transition_to` | `test_fixture_predicate_and_method_*`   |
//! | `PluginState::transition`     | `test_fixture_predicate_and_method_*`      |
//! | `PluginError` (Display)       | `test_fixture_forbidden_transitions_*`     |
//! | `PluginError::Validation`     | `test_fixture_forbidden_transitions_*`     |
//! | `PluginError::code`           | `test_fixture_forbidden_transitions_*`     |
//! | `ErrorCode::Validation`       | `test_fixture_forbidden_transitions_*`     |
//! | `serde_json` (deserialize)   | `test_fixture_schema_is_well_formed`       |
//! | `std::fs::read_to_string`     | `load_fixture` (used by every test)        |
//!
//! ## Traceability
//!
//! Traces to: FR-PHENOPLUGINS-007 (lifecycle state-machine contract).
//! See `docs/FUNCTIONAL_REQUIREMENTS.md` for the requirement definition.

use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

use pheno_plugin_core::error::{ErrorCode, PluginError};
use pheno_plugin_core::lifecycle::PluginState;
use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct Fixture {
    schema_version: u32,
    states: Vec<String>,
    transitions: Vec<TransitionRow>,
}

#[derive(Debug, Deserialize)]
struct TransitionRow {
    from: String,
    to: String,
    allowed: bool,
    #[serde(default)]
    rationale: String,
}

fn fixture_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("fixtures")
        .join("lifecycle_state_machine.json")
}

fn parse_state(s: &str) -> Option<PluginState> {
    Some(match s {
        "registered" => PluginState::Registered,
        "initialized" => PluginState::Initialized,
        "running" => PluginState::Running,
        "stopped" => PluginState::Stopped,
        "failed" => PluginState::Failed,
        _ => return None,
    })
}

fn state_label(s: PluginState) -> &'static str {
    s.as_str()
}

fn load_fixture() -> Fixture {
    let path = fixture_path();
    let raw: String = fs::read_to_string(&path)
        .unwrap_or_else(|e| panic!("failed to read {}: {e}", path.display()));
    serde_json::from_str(raw.as_str())
        .unwrap_or_else(|e| panic!("failed to parse {}: {e}", path.display()))
}

/// Validate the fixture schema itself so a malformed fixture fails with
/// a clear message before any state-machine assertions run.
///
/// This pins the **public surface** of the contract: 5 states, a 5×5
/// matrix, exactly one row per (from, to) cell, with both endpoints
/// referencing declared states. Traces to: FR-PHENOPLUGINS-007.
#[test]
fn test_fixture_schema_is_well_formed() {
    let fixture = load_fixture();

    assert_eq!(fixture.schema_version, 1, "schema_version must be 1");

    // Every string in `states` must map to a real PluginState variant.
    let parsed: Vec<PluginState> = fixture
        .states
        .iter()
        .map(|s| parse_state(s).unwrap_or_else(|| panic!("unknown state in fixture: {s}")))
        .collect();
    assert_eq!(parsed.len(), 5, "fixture must declare exactly 5 states");

    // The transition matrix must be states.len() * states.len() rows.
    let expected_rows = fixture.states.len() * fixture.states.len();
    assert_eq!(
        fixture.transitions.len(),
        expected_rows,
        "fixture must have {expected_rows} rows (states^2), got {}",
        fixture.transitions.len()
    );

    // Each (from, to) pair must appear exactly once.
    let mut seen: HashMap<(String, String), usize> = HashMap::new();
    for row in &fixture.transitions {
        if !fixture.states.contains(&row.from) {
            panic!("transition from unknown state: {}", row.from);
        }
        if !fixture.states.contains(&row.to) {
            panic!("transition to unknown state: {}", row.to);
        }
        *seen.entry((row.from.clone(), row.to.clone())).or_default() += 1;
    }
    let duplicates: Vec<_> = seen.iter().filter(|(_, count)| **count > 1).collect();
    assert!(
        duplicates.is_empty(),
        "fixture has duplicate (from, to) rows: {duplicates:?}"
    );
    // Compute the missing (from, to) pairs directly so we don't have to
    // thread a `seen` HashMap through nested closures.
    let mut missing: Vec<(String, String)> = Vec::new();
    for from in &fixture.states {
        for to in &fixture.states {
            let key = (from.clone(), to.clone());
            if !seen.contains_key(&key) {
                missing.push(key);
            }
        }
    }
    assert!(
        missing.is_empty(),
        "fixture is missing transitions for: {missing:?}"
    );
}

/// Positive oracle: every row where `allowed: true` must succeed in
/// `can_transition_to` AND `transition`, and `transition` must return
/// the target state.
///
/// Traces to: FR-PHENOPLUGINS-007 (positive half).
#[test]
fn test_fixture_allowed_transitions_pass_in_code() {
    let fixture = load_fixture();

    let mut allowed_count = 0;
    for row in &fixture.transitions {
        if !row.allowed {
            continue;
        }
        allowed_count += 1;
        let from =
            parse_state(&row.from).unwrap_or_else(|| panic!("unknown from-state: {}", row.from));
        let to = parse_state(&row.to).unwrap_or_else(|| panic!("unknown to-state: {}", row.to));

        assert!(
            from.can_transition_to(to),
            "fixture marks {from_label} -> {to_label} as ALLOWED but can_transition_to returns false (rationale: {rationale})",
            from_label = state_label(from),
            to_label = state_label(to),
            rationale = row.rationale,
        );

        let result = from.transition(to);
        assert!(
            result.is_ok(),
            "fixture marks {} -> {} as ALLOWED but transition() returned {:?} (rationale: {})",
            state_label(from),
            state_label(to),
            result.err(),
            row.rationale,
        );
        assert_eq!(
            result.unwrap(),
            to,
            "fixture marks {} -> {} as ALLOWED but transition() returned a different state",
            state_label(from),
            state_label(to),
        );
    }

    // Sanity check: the fixture must contain a non-empty set of allowed
    // rows. If this fails, someone probably emptied the matrix by
    // accident.
    assert!(
        allowed_count >= 8,
        "expected at least 8 allowed transitions, got {allowed_count}"
    );
}

/// Negative oracle: every row where `allowed: false` must FAIL in both
/// `can_transition_to` and `transition`. This is the core of the
/// negative fixture oracle: an agent that relaxes the state machine
/// (e.g. by adding a backward transition) breaks this test with a
/// precise cell-level message.
///
/// Pins `PluginError::Validation(String)` as the variant returned for
/// every illegal transition, and `ErrorCode::Validation` as the
/// machine-readable code consumers can branch on. Traces to:
/// FR-PHENOPLUGINS-007 (negative half).
#[test]
fn test_fixture_forbidden_transitions_rejected_in_code() {
    let fixture = load_fixture();

    let mut forbidden_count = 0;
    for row in &fixture.transitions {
        if row.allowed {
            continue;
        }
        forbidden_count += 1;
        let from =
            parse_state(&row.from).unwrap_or_else(|| panic!("unknown from-state: {}", row.from));
        let to = parse_state(&row.to).unwrap_or_else(|| panic!("unknown to-state: {}", row.to));

        assert!(
            !from.can_transition_to(to),
            "fixture marks {from} -> {to} as FORBIDDEN but can_transition_to returns true",
            from = state_label(from),
            to = state_label(to),
        );

        let result = from.transition(to);
        assert!(
            result.is_err(),
            "fixture marks {} -> {} as FORBIDDEN but transition() succeeded (rationale: {})",
            state_label(from),
            state_label(to),
            row.rationale,
        );

        // Type-narrow the error: must be the `Validation` variant (not
        // `Operation`, `Config`, etc.), with the documented machine-
        // readable code. This guards against an agent whose
        // "regression fix" silently changes the error variant.
        let err: PluginError = result.unwrap_err();
        assert!(
            matches!(err, PluginError::Validation(_)),
            "illegal transition must surface as PluginError::Validation, got {err:?}",
        );
        assert_eq!(
            err.code(),
            ErrorCode::Validation,
            "illegal transition must carry ErrorCode::Validation, got {:?}",
            err.code(),
        );

        let displayed = err.to_string();
        assert!(
            displayed.contains(state_label(from)) && displayed.contains(state_label(to)),
            "error message for {} -> {} must mention both states, got: {displayed}",
            state_label(from),
            state_label(to),
        );
    }

    // Sanity check: the fixture must contain a non-empty set of
    // forbidden rows. Without them, the oracle would not be a
    // negative test.
    assert!(
        forbidden_count >= 15,
        "expected at least 15 forbidden transitions, got {forbidden_count}"
    );
}
/// Coherence oracle: the in-code `transition` method must agree with the
/// `can_transition_to` predicate for every (from, to) pair, regardless
/// of what the fixture says. This catches the class of bug where the
/// predicate and the method diverge (e.g. a refactor that updates one
/// but not the other).
///
/// Traces to: FR-PHENOPLUGINS-007 (coherence half).
#[test]
fn test_fixture_predicate_and_method_agree_for_every_cell() {
    let fixture = load_fixture();

    for row in &fixture.transitions {
        let from =
            parse_state(&row.from).unwrap_or_else(|| panic!("unknown from-state: {}", row.from));
        let to = parse_state(&row.to).unwrap_or_else(|| panic!("unknown to-state: {}", row.to));

        let predicate = from.can_transition_to(to);
        let method = from.transition(to).is_ok();
        assert_eq!(
            predicate, method,
            "predicate/method divergence for {} -> {}: can_transition_to={}, transition().is_ok()={}",
            state_label(from),
            state_label(to),
            predicate,
            method,
        );
        assert_eq!(
            predicate,
            row.allowed,
            "fixture/in-code divergence for {} -> {}: fixture.allowed={}, can_transition_to={}",
            state_label(from),
            state_label(to),
            row.allowed,
            predicate,
        );
    }
}
