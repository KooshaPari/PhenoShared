import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class SourceAcquisitionTests(unittest.TestCase):
    def test_default_is_plan_only_and_refuses_c_drive(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(root / "scripts" / "acquire_local_source.py"),
                    "--model",
                    "local/qwen35-08b",
                    "--target-root",
                    directory,
                    "--output",
                    str(output),
                ],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
