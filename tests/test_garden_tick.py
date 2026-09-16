import json
import subprocess
import sys
import unittest
from pathlib import Path


class GardenTickTests(unittest.TestCase):
    def test_empty_ledger_dry_run_is_non_mutating(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [
                sys.executable,
                str(root / "scripts" / "run_self_improvement_tick.py"),
                "--dry-run",
            ],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertTrue(report["dry_run"])


if __name__ == "__main__":
    unittest.main()
