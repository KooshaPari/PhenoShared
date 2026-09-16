import unittest

import pytest

pytest.importorskip(
    "huggingface_hub", reason="huggingface_hub not installed in test venv"
)

from scripts.probe_local_artifacts import _file_record


class ArtifactProbeTests(unittest.TestCase):
    def test_file_classification_is_metadata_only(self):
        class Item:
            path = "model-q4_k_m.gguf"
            size = 123

        row = _file_record(Item())
        self.assertEqual(row["size_bytes"], 123)
        self.assertIn("gguf", row["formats"])
        self.assertIn("q4", row["quant_markers"])


if __name__ == "__main__":
    unittest.main()
