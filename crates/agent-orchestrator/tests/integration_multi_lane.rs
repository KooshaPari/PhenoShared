//! Integration tests: multi-lane task coordination
//!
//! Covers:
//!   1. Coordinating tasks across 3+ parallel lanes (correct distribution, no double-dispatch)
//!   2. State persistence + recovery under rollback (lane fails → state rolls back, others unaffected)
//!   3. Backpressure / lane saturation (more tasks than lanes → queued, drained in order)
//!   4. Deterministic completion accounting (all submitted tasks eventually accounted for)

use agent_orchestrator::{Lane, OrchestrationConfig, TrackerState};
use std::collections::VecDeque;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn make_config(lane_ids: &[&str]) -> OrchestrationConfig {
    OrchestrationConfig {
        project_name: "integration-test".to_string(),
        repo_root: "/tmp".to_string(),
        sweep_cadence_minutes: 1,
        lanes: lane_ids
            .iter()
            .enumerate()
            .map(|(i, id)| Lane {
                id: id.to_string(),
                name: format!("Lane {}", i),
                // Use a glob pattern that will never expand to real files so
                // validate_non_overlapping() can run without filesystem side-effects.
                scope: vec![format!("__non_existent_{}_{}/**/*.rs", id, i)],
                prompt_template: format!("Review {}", id),
                commit_message_prefix: id.to_string(),
            })
            .collect(),
    }
}

// ---------------------------------------------------------------------------
// Test 1 – Three parallel lanes: correct distribution, no double-dispatch
// ---------------------------------------------------------------------------

#[test]
fn test_three_lane_distribution_no_double_dispatch() {
    let config = make_config(&["alpha", "beta", "gamma"]);
    let mut state = TrackerState::new();

    // Dispatch each lane exactly once.
    for lane in &config.lanes {
        // A lane should only be dispatched when it is NOT already in-flight.
        let already_in_flight = state
            .lanes
            .get(&lane.id)
            .map(|t| t.in_flight)
            .unwrap_or(false);

        assert!(
            !already_in_flight,
            "Lane '{}' must not already be in-flight before first dispatch",
            lane.id
        );

        state.update_lane(lane.id.clone(), true);
    }

    // All 3 lanes are now in-flight.
    assert_eq!(state.lanes.len(), 3, "All three lanes must be tracked");
    for lane in &config.lanes {
        assert!(
            state.lanes[&lane.id].in_flight,
            "Lane '{}' must be in-flight after dispatch",
            lane.id
        );
        assert!(
            state.lanes[&lane.id].last_dispatch.is_some(),
            "Lane '{}' must have a last_dispatch timestamp",
            lane.id
        );
    }

    // Double-dispatch guard: attempt to dispatch again; check in_flight is still true
    // and dispatch is idempotent (we just call update_lane(true) a second time and
    // verify the state remains consistent — no extra lane entries appear).
    for lane in &config.lanes {
        state.update_lane(lane.id.clone(), true);
    }
    assert_eq!(
        state.lanes.len(),
        3,
        "No phantom lane entries from repeated dispatch"
    );
}

// ---------------------------------------------------------------------------
// Test 2 – Lane scope non-overlap: config validates cleanly for 3+ lanes
// ---------------------------------------------------------------------------

#[test]
fn test_three_lane_non_overlap_validation() {
    let config = make_config(&["domain", "storage", "connectors"]);
    // Patterns point to non-existent directories so glob expands to nothing,
    // meaning the seen_files map stays empty → no overlap → Ok.
    let result = config.validate_non_overlapping();
    assert!(
        result.is_ok(),
        "Three lanes with non-overlapping (empty) scopes must validate: {:?}",
        result
    );
}

// ---------------------------------------------------------------------------
// Test 3 – Rollback: a failing lane resets to not-in-flight;
//           sibling lanes are completely unaffected.
// ---------------------------------------------------------------------------

#[test]
fn test_rollback_failing_lane_does_not_affect_siblings() {
    let lane_ids = ["lane-a", "lane-b", "lane-c"];
    let config = make_config(&lane_ids);
    let mut state = TrackerState::new();

    // Dispatch all lanes.
    for lane in &config.lanes {
        state.update_lane(lane.id.clone(), true);
        state.mark_coverage_complete(&lane.id);
    }

    // Simulate lane-b failing: mark it not-in-flight (rollback).
    state.update_lane("lane-b".to_string(), false);

    // Verify rollback: lane-b is no longer in-flight.
    assert!(
        !state.lanes["lane-b"].in_flight,
        "Rolled-back lane must not be in-flight"
    );

    // Verify siblings are unaffected.
    assert!(
        state.lanes["lane-a"].in_flight,
        "Sibling lane-a must remain in-flight after lane-b rollback"
    );
    assert!(
        state.lanes["lane-c"].in_flight,
        "Sibling lane-c must remain in-flight after lane-b rollback"
    );

    // Coverage counts on siblings must be preserved.
    assert_eq!(
        state.lanes["lane-a"].coverage_count, 1,
        "lane-a coverage count must be preserved after sibling rollback"
    );
    assert_eq!(
        state.lanes["lane-c"].coverage_count, 1,
        "lane-c coverage count must be preserved after sibling rollback"
    );
}

// ---------------------------------------------------------------------------
// Test 4 – Rollback state persistence round-trip via JSON serialization.
//           Ensures the rolled-back state survives a save/reload cycle.
// ---------------------------------------------------------------------------

#[test]
fn test_rollback_persists_through_serialization() {
    let mut state = TrackerState::new();

    state.update_lane("lane-x".to_string(), true);
    state.update_lane("lane-y".to_string(), true);

    // Rollback lane-x.
    state.update_lane("lane-x".to_string(), false);

    // Round-trip through JSON (simulates writing + reading from disk).
    let json = serde_json::to_string(&state).expect("must serialize");
    let recovered: TrackerState = serde_json::from_str(&json).expect("must deserialize");

    assert!(
        !recovered.lanes["lane-x"].in_flight,
        "Rolled-back lane-x must remain not-in-flight after JSON round-trip"
    );
    assert!(
        recovered.lanes["lane-y"].in_flight,
        "Unaffected lane-y must remain in-flight after JSON round-trip"
    );
}

// ---------------------------------------------------------------------------
// Test 5 – Backpressure / lane saturation:
//           More tasks than lanes → queue, drain in submission order.
// ---------------------------------------------------------------------------

/// A minimal in-process task queue that models backpressure:
/// at most `capacity` tasks run concurrently; the rest wait.
struct TaskQueue {
    capacity: usize,
    in_flight: Vec<String>,
    pending: VecDeque<String>,
    completed: Vec<String>,
}

impl TaskQueue {
    fn new(capacity: usize) -> Self {
        Self {
            capacity,
            in_flight: Vec::new(),
            pending: VecDeque::new(),
            completed: Vec::new(),
        }
    }

    fn submit(&mut self, task_id: String) {
        if self.in_flight.len() < self.capacity {
            self.in_flight.push(task_id);
        } else {
            self.pending.push_back(task_id);
        }
    }

    /// Complete the first in-flight task and promote the next pending one.
    fn complete_next(&mut self) -> Option<String> {
        if self.in_flight.is_empty() {
            return None;
        }
        let done = self.in_flight.remove(0);
        self.completed.push(done.clone());
        // Drain one from pending into in-flight.
        if let Some(next) = self.pending.pop_front() {
            self.in_flight.push(next);
        }
        Some(done)
    }

    fn all_done(&self) -> bool {
        self.in_flight.is_empty() && self.pending.is_empty()
    }
}

#[test]
fn test_backpressure_tasks_queued_and_drained_in_order() {
    // 3 lanes → capacity 3; submit 7 tasks.
    let mut queue = TaskQueue::new(3);
    let task_ids: Vec<String> = (1..=7).map(|i| format!("task-{}", i)).collect();

    for id in &task_ids {
        queue.submit(id.clone());
    }

    // After submitting 7 with capacity 3: 3 in-flight, 4 pending.
    assert_eq!(
        queue.in_flight.len(),
        3,
        "exactly 3 tasks must be in-flight"
    );
    assert_eq!(queue.pending.len(), 4, "remaining 4 tasks must be pending");

    // First three in-flight must be the first three submitted (FIFO within capacity).
    assert_eq!(queue.in_flight[0], "task-1");
    assert_eq!(queue.in_flight[1], "task-2");
    assert_eq!(queue.in_flight[2], "task-3");

    // Drain all tasks and verify completion order.
    while !queue.all_done() {
        queue.complete_next();
    }

    assert_eq!(
        queue.completed.len(),
        7,
        "all 7 tasks must be completed after draining"
    );

    // Tasks must complete in submission order.
    for (i, completed_id) in queue.completed.iter().enumerate() {
        assert_eq!(
            *completed_id,
            format!("task-{}", i + 1),
            "task {} must complete in submission order",
            i + 1
        );
    }
}

#[test]
fn test_backpressure_no_task_skipped_under_saturation() {
    let mut queue = TaskQueue::new(3);
    let n = 10usize;
    for i in 1..=n {
        queue.submit(format!("t{}", i));
    }

    let mut completion_count = 0;
    while !queue.all_done() {
        if queue.complete_next().is_some() {
            completion_count += 1;
        }
    }

    assert_eq!(completion_count, n, "every submitted task must complete");
}

// ---------------------------------------------------------------------------
// Test 6 – Deterministic completion accounting:
//           all submitted tasks eventually accounted for via coverage_count.
// ---------------------------------------------------------------------------

#[test]
fn test_deterministic_completion_accounting_all_tasks_counted() {
    let lane_ids = ["lane-1", "lane-2", "lane-3", "lane-4"];
    let dispatches_per_lane = 5usize;

    let mut state = TrackerState::new();

    // Simulate multiple dispatch/complete cycles.
    for _ in 0..dispatches_per_lane {
        for id in &lane_ids {
            state.update_lane(id.to_string(), true);
            // Simulate completion.
            state.update_lane(id.to_string(), false);
            state.mark_coverage_complete(id);
        }
    }

    // Every lane must have exactly `dispatches_per_lane` coverage completions.
    for id in &lane_ids {
        let count = state.lanes.get(*id).map(|t| t.coverage_count).unwrap_or(0);
        assert_eq!(
            count, dispatches_per_lane as u64,
            "lane '{}' must have exactly {} completions",
            id, dispatches_per_lane
        );
    }

    // Total completions across all lanes.
    let total: u64 = state.lanes.values().map(|t| t.coverage_count).sum();
    assert_eq!(
        total,
        (lane_ids.len() * dispatches_per_lane) as u64,
        "total completion count must equal lanes × dispatches_per_lane"
    );
}

#[test]
fn test_deterministic_completion_no_lane_left_in_flight() {
    let lane_ids = ["x", "y", "z"];
    let mut state = TrackerState::new();

    for id in &lane_ids {
        state.update_lane(id.to_string(), true);
    }

    // Complete every lane.
    for id in &lane_ids {
        state.update_lane(id.to_string(), false);
        state.mark_coverage_complete(id);
    }

    for id in &lane_ids {
        assert!(
            !state.lanes[*id].in_flight,
            "lane '{}' must not be in-flight after completion",
            id
        );
        assert_eq!(
            state.lanes[*id].coverage_count, 1,
            "lane '{}' must have exactly 1 coverage completion",
            id
        );
    }
}

// ---------------------------------------------------------------------------
// Test 7 – State file persistence round-trip (uses temp directory).
// ---------------------------------------------------------------------------

#[test]
fn test_state_file_round_trip_via_temp_file() {
    use std::fs;

    let tmp_dir = std::env::temp_dir();
    // Use a unique file name to avoid cross-test interference.
    let state_path = tmp_dir.join(format!(
        "agent_orchestrator_test_{}.json",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .subsec_nanos()
    ));

    let mut original = TrackerState::new();
    original.update_lane("p".to_string(), true);
    original.update_lane("q".to_string(), false);
    original.mark_coverage_complete("p");

    original.to_file(&state_path).expect("write must succeed");

    let loaded = TrackerState::from_file(&state_path).expect("read must succeed");

    assert_eq!(loaded.lanes.len(), 2);
    assert!(loaded.lanes["p"].in_flight);
    assert!(!loaded.lanes["q"].in_flight);
    assert_eq!(loaded.lanes["p"].coverage_count, 1);
    assert_eq!(loaded.lanes["q"].coverage_count, 0);

    // Clean up.
    let _ = fs::remove_file(&state_path);
}

// ---------------------------------------------------------------------------
// Test 8 – Config file round-trip (uses temp directory).
// ---------------------------------------------------------------------------

#[test]
fn test_config_file_round_trip_via_temp_file() {
    use std::fs;

    let tmp_dir = std::env::temp_dir();
    let config_path = tmp_dir.join(format!(
        "agent_orchestrator_config_test_{}.toml",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .subsec_nanos()
    ));

    let original = make_config(&["lane-a", "lane-b", "lane-c"]);
    original.to_file(&config_path).expect("write must succeed");

    let loaded = OrchestrationConfig::from_file(&config_path).expect("read must succeed");

    assert_eq!(loaded.project_name, original.project_name);
    assert_eq!(loaded.lanes.len(), 3);
    assert_eq!(loaded.lanes[0].id, "lane-a");
    assert_eq!(loaded.lanes[2].id, "lane-c");

    let _ = fs::remove_file(&config_path);
}
