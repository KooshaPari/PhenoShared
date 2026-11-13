"""Incident decisions use completed-run evidence, without live requests."""
import copy
import unittest
from datetime import datetime, timedelta, timezone
from incident_policy import evaluate

NOW = datetime(2026, 10, 14, 18, tzinfo=timezone.utc)
TARGET = "offline-collector"


def run(day="2026-10-14", good=24, bad=1, *, age=2, ok=None, **fields):
    return {"day": day, "ok": int(bad == 0 and good > 0) if ok is None else ok,
            "boards_ok": good, "boards_failed": bad,
            "finished_at": (NOW - timedelta(hours=age)).isoformat(), **fields}


def health(*runs):
    return {"service": "job-collector", "health": "degraded", "run_identity_scheme": "la-day-v1",
            "finalized_runs": list(runs), "latest_run": runs[0] if runs else None}


class IncidentPolicyTests(unittest.TestCase):
    def evaluate(self, h, previous=None, now=NOW):
        return evaluate(h, previous, now, target=TARGET)

    def report(self, h, previous=None, now=NOW):
        decision, checkpoint = self.evaluate(h, previous, now)
        return {"incident": decision, "incident_checkpoint": checkpoint, "checked_at": now.isoformat()}

    def test_strict_percentage_boundaries(self):
        for good, bad, opens in [(8, 1, True), (9, 1, False), (18, 2, False),
                                 (22, 3, True), (90, 10, False), (0, 1, True), (99, 1, False)]:
            with self.subTest(good=good, bad=bad):
                d, _ = self.evaluate(health(run(good=good, bad=bad)))
                self.assertEqual(d["should_open_or_reopen"], opens)
                self.assertEqual(d["boards_checked"], good + bad)
                self.assertEqual(d["boards_failed"], bad)

    def test_active_inventory_is_not_percentage_denominator(self):
        h = health(run(good=8, bad=1))
        h["boards"] = {"total": 500, "last_failure": 0}
        self.assertTrue(self.evaluate(h)[0]["should_open_or_reopen"])

    def test_two_authoritative_failures_need_no_previous_poll(self):
        d, _ = self.evaluate(health(run(), run("2026-10-13", age=26)))
        self.assertEqual(d["consecutive_degraded"], 2)
        self.assertTrue(d["should_open_or_reopen"])

    def test_duplicate_probes_and_duplicate_history_ids_are_one_run(self):
        h = health(run())
        previous = self.report(h)
        for _ in range(4):
            previous = self.report(h, previous)
            self.assertEqual(previous["incident"]["consecutive_degraded"], 1)
            self.assertFalse(previous["incident"]["should_open_or_reopen"])
        self.assertEqual(self.evaluate(health(run(), run()))[0]["consecutive_degraded"], 1)

    def test_healthy_finalization_resets_streak(self):
        previous = self.report(health(run("2026-10-13"), run("2026-10-12", age=26)))
        recovered = self.report(health(run(bad=0), run("2026-10-13", age=26)), previous)
        self.assertEqual(recovered["incident"]["consecutive_degraded"], 0)
        self.assertFalse(recovered["incident"]["should_open_or_reopen"])
        next_run = run("2026-10-15", age=0)
        d, _ = self.evaluate(health(next_run, run(bad=0)), recovered)
        self.assertEqual(d["consecutive_degraded"], 1)

    def test_healthy_intervening_run_breaks_two_observed_failures(self):
        prior = self.report(health(run("2026-10-12", age=26)))
        d, _ = self.evaluate(health(run(), run("2026-10-13", bad=0, age=26)), prior)
        self.assertEqual(d["consecutive_degraded"], 1)
        self.assertFalse(d["should_open_or_reopen"])

    def test_staleness_uses_raw_timestamp_at_exact_boundary(self):
        for seconds, opens in [(36 * 3600, False), (36 * 3600 + 1, True)]:
            row = run(bad=0)
            row["finished_at"] = (NOW - timedelta(seconds=seconds)).isoformat()
            d, _ = self.evaluate(health(row))
            self.assertEqual(d["should_open_or_reopen"], opens)

    def test_fresh_error_placeholder_does_not_refresh_completion(self):
        old = run("2026-10-12", bad=0, age=37)
        h = health(old)
        h.update(latest_run=run(good=None, bad=None, age=0, ok=0), age_hours=0, health="degraded")
        d, _ = self.evaluate(h)
        self.assertTrue(d["should_open_or_reopen"])
        self.assertEqual(d["finalized_age_hours"], 37)

    def test_same_run_timestamp_revision_cannot_refresh_clock(self):
        old = run(bad=0, age=35)
        previous = self.report(health(old))
        fresh = {**old, "finished_at": (NOW + timedelta(hours=2)).isoformat()}
        d, _ = self.evaluate(health(fresh), previous, NOW + timedelta(hours=2))
        self.assertEqual(d["finalized_age_hours"], 37)
        self.assertTrue(d["should_open_or_reopen"])

    def test_conflicting_same_id_is_quarantined_across_probes(self):
        previous = self.report(health(run(bad=0)))
        bad = run(good=0, bad=1)
        previous = self.report(health(bad), previous)
        self.assertFalse(previous["incident"]["should_open_or_reopen"])
        self.assertIsNone(previous["incident"]["boards_checked"])
        self.assertFalse(self.evaluate(health(bad), previous)[0]["should_open_or_reopen"])
        duplicate = self.evaluate(health(run(bad=0), bad))[0]
        self.assertEqual(duplicate["consecutive_degraded"], 0)

    def test_unknown_rows_do_not_join_failures(self):
        invalid = run("2026-10-13", good=None, age=26)
        d, _ = self.evaluate(health(run(), invalid))
        self.assertEqual(d["consecutive_degraded"], 1)
        self.assertFalse(d["should_open_or_reopen"])

    def test_missing_malformed_counts_and_times_are_unknown(self):
        for changes in ({"boards_ok": None}, {"boards_ok": True}, {"boards_failed": -1},
                        {"boards_failed": 0.5}, {"ok": True}, {"ok": 1},
                        {"finished_at": "invalid"}, {"finished_at": "2026-10-14T17:00:00"},
                        {"finished_at": (NOW + timedelta(seconds=1)).isoformat()}, {"day": None}):
            with self.subTest(changes=changes):
                d, _ = self.evaluate(health({**run(), **changes}))
                self.assertFalse(d["should_open_or_reopen"])
                self.assertIsNone(d["boards_checked"])
                self.assertTrue(d["data_issues"])

    def test_known_empty_is_degraded_and_never_divides_by_zero(self):
        empty = run(good=0, bad=0, ok=0, error="no active boards")
        d, _ = self.evaluate(health(empty))
        self.assertEqual(d["consecutive_degraded"], 1)
        self.assertEqual(d["boards_checked"], 0)
        self.assertFalse(d["should_open_or_reopen"])
        second = {**empty, "day": "2026-10-13"}
        self.assertTrue(self.evaluate(health(empty, second))[0]["should_open_or_reopen"])
        self.assertIsNone(self.evaluate(health(run(good=0, bad=0, ok=0)))[0]["boards_checked"])

    def test_no_history_absence_clock_survives_runner_restart(self):
        previous = self.report(health())
        exact = self.report(health(), previous, NOW + timedelta(hours=36))
        self.assertFalse(exact["incident"]["should_open_or_reopen"])
        later = self.report(health(), exact, NOW + timedelta(hours=36, seconds=1))
        self.assertTrue(later["incident"]["should_open_or_reopen"])
        self.assertIsNone(later["incident"]["finalized_age_hours"])
        self.assertIsNone(later["incident"]["boards_failed"])

    def test_corrupt_new_row_keeps_previous_stale_clock(self):
        previous = self.report(health(run("2026-10-12", bad=0, age=35)))
        corrupt = run(boards_failed=None)
        d, _ = self.evaluate(health(corrupt), previous, NOW + timedelta(hours=2))
        self.assertTrue(d["should_open_or_reopen"])
        self.assertEqual(d["consecutive_degraded"], 0)

    def test_legacy_worker_counts_only_adjacent_distinct_days(self):
        def legacy(row):
            return {"service": "job-collector", "latest_run": row}
        previous = self.report(legacy(run("2026-10-13")))
        self.assertEqual(self.evaluate(legacy(run()), previous)[0]["consecutive_degraded"], 2)
        previous = self.report(legacy(run("2026-10-12")))
        self.assertEqual(self.evaluate(legacy(run()), previous)[0]["consecutive_degraded"], 1)
        placeholder = {"day": "2026-10-14", "ok": 0, "boards_ok": None, "finished_at": NOW.isoformat()}
        self.assertEqual(self.evaluate(legacy(placeholder), previous)[0]["consecutive_degraded"], 0)

    def test_wrong_service_scheme_or_history_order_is_unknown(self):
        for changes in ({"service": "other"}, {"run_identity_scheme": "slot-v2"},
                        {"finalized_runs": "bad"}, {"finalized_runs": [run("2026-10-13"), run()]}):
            with self.subTest(changes=changes):
                d, _ = self.evaluate({**health(run()), **changes})
                self.assertFalse(d["should_open_or_reopen"])
                self.assertEqual(d["consecutive_degraded"], 0)

    def test_regressed_history_and_checkpoint_identity_fail_safely(self):
        previous = self.report(health(run(bad=0)))
        d, _ = self.evaluate(health(run("2026-10-13", good=0, bad=1)), previous)
        self.assertFalse(d["should_open_or_reopen"])
        broken = copy.deepcopy(previous)
        broken["incident_checkpoint"]["target"] = "different-worker"
        with self.assertRaisesRegex(ValueError, "mismatch"):
            self.evaluate(health(), broken)

    def test_no_decision_authorizes_automatic_closure(self):
        for h in (health(run(bad=0)), health(run()), health(), health(run(good=0, bad=1))):
            self.assertIs(self.evaluate(h)[0]["close_existing_incident"], False)

    def test_corrupt_checkpoint_cannot_restart_absence_clock(self):
        original = self.report(health())
        for key, value in (("first_observed_at", None), ("first_observed_at", "2999-01-01T00:00:00Z"),
                           ("conflicts", "bad"), ("runs", [None])):
            with self.subTest(key=key, value=value):
                previous = copy.deepcopy(original)
                previous["incident_checkpoint"][key] = value
                with self.assertRaises(ValueError):
                    self.evaluate(health(), previous)
        with self.assertRaises(ValueError):
            self.evaluate(health(), {"incident": {}, "checked_at": NOW.isoformat()})


if __name__ == "__main__":
    unittest.main()
