"""Regression tests for append-only dashboard artifact retention."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("cockpit_dashboard", ROOT / "cockpit-dashboard.py")
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DashboardRetentionTests(unittest.TestCase):
    def test_writing_dashboard_retains_existing_artifacts_and_latest_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            dashboard_dir = Path(temporary_directory)
            old_dashboard = dashboard_dir / "cockpit-old.html"
            old_dashboard.write_text("old dashboard", encoding="utf-8")
            latest = dashboard_dir / "cockpit-latest.html"
            latest.symlink_to(old_dashboard.name)

            with patch.object(MODULE, "DASHBOARD_DIR", dashboard_dir):
                new_dashboard, data_snapshot, content_hash = MODULE.write_dashboard_artifacts(
                    {"generated_at": "2026-08-20T00:00:00+00:00", "status": "HEALTHY"},
                    "new dashboard",
                )

            self.assertTrue(old_dashboard.exists())
            self.assertTrue(latest.is_symlink())
            self.assertTrue(latest.samefile(old_dashboard))
            self.assertEqual(new_dashboard.read_text(encoding="utf-8"), "new dashboard")
            self.assertEqual(new_dashboard.name, f"cockpit-{content_hash}.html")
            self.assertIn("cockpit-data-", data_snapshot.name)
            self.assertTrue(data_snapshot.exists())


if __name__ == "__main__":
    unittest.main()
