from __future__ import annotations

import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from scripts import doctor


class DoctorTests(unittest.TestCase):
    def test_report_is_json_safe_and_declares_no_execution(self) -> None:
        report = doctor.build_report()
        self.assertEqual(report["schema_version"], doctor.SCHEMA_VERSION)
        self.assertIn(report["state"], {"ready", "blocked"})
        self.assertFalse(any(report["execution"].values()))
        self.assertEqual(set(report["required_configs"]), set(doctor.REQUIRED_CONFIGS))
        json.dumps(report, sort_keys=True)

    def test_main_emits_deterministic_report_shape(self) -> None:
        first = StringIO()
        second = StringIO()
        with redirect_stdout(first), patch.object(doctor, "_git", return_value="value"):
            doctor.main([])
        with (
            redirect_stdout(second),
            patch.object(doctor, "_git", return_value="value"),
        ):
            doctor.main([])
        self.assertEqual(json.loads(first.getvalue()), json.loads(second.getvalue()))

    def test_strict_reports_blocked_without_changing_state(self) -> None:
        with patch.object(doctor, "_git", return_value=None):
            output = StringIO()
            with redirect_stdout(output):
                result = doctor.main(["--strict"])
        self.assertEqual(result, 1)
        report = json.loads(output.getvalue())
        self.assertEqual(report["state"], "blocked")
        self.assertFalse(report["execution"]["model_launched"])


if __name__ == "__main__":
    unittest.main()
