import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class GgufConversionTests(unittest.TestCase):
    def test_plan_does_not_modify_source_or_claim_eval_artifact(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            source.mkdir()
            (source / "config.json").write_text("{}", encoding="utf-8")
            output = Path(directory) / "out.gguf"
            manifest = Path(directory) / "manifest.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(root / "scripts" / "convert_gguf_artifact.py"),
                    "--source",
                    str(source),
                    "--output",
                    str(output),
                    "--convert-script",
                    str(Path(directory) / "convert.py"),
                    "--quantize-bin",
                    str(Path(directory) / "quantize.exe"),
                    "--output-manifest",
                    str(manifest),
                ],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(manifest.exists())

    def test_runtime_promotion_requires_evidence_file(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            source.mkdir()
            (source / "config.json").write_text("{}", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(root / "scripts" / "convert_gguf_artifact.py"),
                    "--source",
                    str(source),
                    "--output",
                    "D:/artifact.gguf",
                    "--convert-script",
                    str(Path(directory) / "convert.py"),
                    "--quantize-bin",
                    str(Path(directory) / "quantize.exe"),
                    "--runtime-validated",
                    "--output-manifest",
                    str(Path(directory) / "manifest.json"),
                ],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("runtime-evidence", result.stderr)


if __name__ == "__main__":
    unittest.main()
