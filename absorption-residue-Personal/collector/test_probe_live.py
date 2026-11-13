"""Offline contract checks for unattended job-collector monitoring."""
import unittest
import json
import tempfile
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from unittest.mock import patch
import probe_live

class LiveProbeTests(unittest.TestCase):
    def healthy(self):
        return {
            "service": "job-collector", "health": "ok", "age_hours": 3,
            "boards": {"total": 25, "last_failure": 0, "never_checked": 0},
            "strict_verified_la": None
        }
    def review(self):
        return {"kind":"unverified_la_review_queue", "count":1,
                "truncated":False,
                "candidates":[{"verification_status":"unverified","graduation_eligible":None}]}
    def test_healthy_contract(self):
        self.assertEqual(probe_live.evaluate(self.healthy(), self.review()), [])
    def test_failing_board_is_degraded(self):
        h=self.healthy()
        h["health"]="degraded"
        h["boards"]["last_failure"]=1
        self.assertTrue(any("failing employer" in p for p in probe_live.evaluate(h,self.review())))
    def test_failure_cannot_be_hidden_by_ok_health(self):
        for total in (1, 2, 9, 10, 25, 100):
            with self.subTest(total=total):
                h=self.healthy()
                h["boards"].update(total=total,last_failure=1)
                self.assertTrue(any("failing employer" in p for p in probe_live.evaluate(h,self.review())))
    def test_zero_or_invalid_board_count_is_not_healthy(self):
        for total in (0, -1, None, True):
            with self.subTest(total=total):
                h=self.healthy()
                h["boards"]["total"]=total
                self.assertTrue(any("board count" in p for p in probe_live.evaluate(h,self.review())))
    def test_invalid_age_is_stale(self):
        for age in (float('nan'), float('inf'), -1, True, None):
            with self.subTest(age=age):
                h=self.healthy()
                h["age_hours"]=age
                self.assertTrue(any("stale" in p for p in probe_live.evaluate(h,self.review())))
    def test_stale_run(self):
        h=self.healthy()
        h["age_hours"]=49
        self.assertTrue(any("stale" in p for p in probe_live.evaluate(h,self.review())))
    def test_reject_auto_verified_jobs(self):
        r=self.review()
        r["candidates"][0]["verification_status"]="active_verified"
        self.assertTrue(any("unsafe" in p for p in probe_live.evaluate(self.healthy(),r)))
    def test_requires_verification_not_fake_count(self):
        h=self.healthy()
        h["strict_verified_la"]=32
        self.assertTrue(any("evidence" in p for p in probe_live.evaluate(h,self.review())))

    def completed(self, *, bad=1, age=2):
        h = self.healthy()
        row = {"day": "2026-10-14", "ok": int(bad == 0), "boards_ok": 25 - bad,
               "boards_failed": bad, "finished_at": (datetime.now(timezone.utc) - timedelta(hours=age)).isoformat()}
        h.update(latest_run=row, finalized_runs=[row], run_identity_scheme="la-day-v1")
        if bad:
            h["health"] = "degraded"
            h["boards"]["last_failure"] = bad
        return h

    def probe(self, responses, *, previous=None):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            args = ["--output", str(output)]
            if previous:
                old = Path(directory) / "previous.json"
                old.write_text(json.dumps(previous), encoding="utf-8")
                args += ["--previous-report", str(old)]
            with patch.object(probe_live, "load", side_effect=responses) as mocked, redirect_stdout(StringIO()):
                self.assertEqual(probe_live.main(args), 0)
                mocked.assert_any_call("/health")
            return json.loads(output.read_text(encoding="utf-8"))

    def test_probe_keeps_one_failed_board_degraded_while_opening_is_pending(self):
        report = self.probe([self.completed(), self.review()])
        self.assertEqual(report["status"], "degraded")
        self.assertFalse(report["incident"]["should_open_or_reopen"])
        self.assertEqual(report["incident"]["boards_failed"], 1)
        self.assertEqual(report["incident"]["boards_checked"], 25)
        duplicate = self.probe([self.completed(), self.review()], previous=report)
        self.assertEqual(duplicate["incident"]["consecutive_degraded"], 1)

    def test_probe_healthy_finalized_metadata_preserves_healthy_status(self):
        report = self.probe([self.completed(bad=0), self.review()])
        self.assertEqual(report["status"], "healthy")
        self.assertFalse(report["incident"]["should_open_or_reopen"])

    def test_probe_rounded_age_cannot_hide_stale_finalization(self):
        h = self.completed(bad=0, age=36.001)
        h["age_hours"] = 36
        report = self.probe([h, self.review()])
        self.assertEqual(report["status"], "degraded")
        self.assertTrue(report["incident"]["should_open_or_reopen"])

    def test_probe_failure_and_nonobject_response_preserve_checkpoint(self):
        old = self.probe([self.completed(bad=0, age=37), self.review()])
        for responses in ([RuntimeError("network failed")], [RuntimeError("invalid JSON")], [[]]):
            with self.subTest(responses=responses):
                report = self.probe(responses, previous=old)
                self.assertEqual(report["status"], "degraded")
                self.assertTrue(report["incident"]["should_open_or_reopen"])
                self.assertIsNone(report["incident"]["boards_failed"])

    def test_probe_malformed_restored_checkpoint_stops_before_network(self):
        with tempfile.TemporaryDirectory() as directory:
            old = Path(directory) / "previous.json"
            old.write_text("{invalid", encoding="utf-8")
            with patch.object(probe_live, "load") as mocked:
                with self.assertRaises(json.JSONDecodeError):
                    probe_live.main(["--previous-report", str(old), "--output", str(Path(directory) / "out.json")])
                mocked.assert_not_called()

    def test_probe_nonobject_review_is_persisted_as_degraded(self):
        report = self.probe([self.completed(bad=0), []])
        self.assertEqual(report["status"], "degraded")
        self.assertIsNone(report["review_count"])

if __name__ == "__main__":
    unittest.main()
