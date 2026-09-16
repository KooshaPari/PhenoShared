"""Validate FUNCTIONAL_REQUIREMENTS.md FR-PH-009 unreadable-file handling."""

import tempfile
import unittest
from pathlib import Path

from legacy_tooling_scanner import scan


class EncodingTests(unittest.TestCase):
    def test_invalid_utf8_is_skipped_while_text_is_scanned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "binary.ts").write_bytes(b"\xffconsole.log('x')")
            (root / "text.ts").write_text("console.log('x')", encoding="utf-8")
            result = scan(
                root,
                {
                    "rules": [
                        {
                            "id": "encoding-probe",
                            "severity": "high",
                            "globs": ["**/*.ts"],
                            "forbid": [r"console\.log"],
                        }
                    ]
                },
            )
            self.assertEqual(result.skipped_files, ["binary.ts"])
            self.assertEqual(result.files_scanned, 1)
            self.assertEqual([finding.file for finding in result.findings], ["text.ts"])


if __name__ == "__main__":
    unittest.main()
