import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from harness.self_improvement.promotion import promotion_decision
from harness.self_improvement.retention import retention_preview


class GardenRetentionPromotionTests(unittest.TestCase):
    def test_retention_is_non_destructive_and_counts_malformed_rows(self):
        now = datetime(2026, 7, 14, tzinfo=UTC)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {"timestamp_utc": (now - timedelta(days=31)).isoformat()}
                        ),
                        json.dumps(
                            {"timestamp_utc": (now - timedelta(days=1)).isoformat()}
                        ),
                        "not-json",
                    ]
                ),
                encoding="utf-8",
            )
            before = path.read_text(encoding="utf-8")
            result = retention_preview(path, now=now)
            self.assertEqual(result["archiveable"], 1)
            self.assertEqual(result["fresh"], 1)
            self.assertEqual(result["malformed"], 1)
            self.assertEqual(path.read_text(encoding="utf-8"), before)

    def test_promotion_requires_two_green_windows_and_human_approval(self):
        windows = [{"status": "green"}, {"status": "green"}]
        self.assertFalse(promotion_decision(windows)["eligible"])
        result = promotion_decision(windows, human_approved=True)
        self.assertTrue(result["eligible"])
        self.assertFalse(result["mutated"])
        self.assertFalse(
            promotion_decision([{"status": "green"}, {"status": "red"}], True)[
                "eligible"
            ]
        )


if __name__ == "__main__":
    unittest.main()
