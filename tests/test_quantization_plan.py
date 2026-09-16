import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class QuantizationPlanTests(unittest.TestCase):
    def test_plan_is_no_download_no_conversion(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "plan.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(root / "scripts" / "plan_quantization.py"),
                    "--source-root",
                    directory,
                    "--minimum-free-gb",
                    "0",
                    "--variant",
                    "gguf_q4",
                    "--output",
                    str(output),
                ],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertFalse(report["download_performed"])
            self.assertFalse(report["conversion_performed"])
            self.assertEqual(report["variants"][0]["id"], "gguf_q4")


if __name__ == "__main__":
    unittest.main()
