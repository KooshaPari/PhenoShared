"""Network-free negative controls for the ResearchLedger Wave 5 recovery importer."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

HERE = Path(__file__).resolve()
MODULE = HERE.parents[2] / "scripts/researchledger/recover_wave5.py"
spec = importlib.util.spec_from_file_location("recover", MODULE)
recover = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recover)

class RecoveryTests(unittest.TestCase):
    def test_safe_names(self):
        self.assertTrue(recover.safe("docs/corpora/emergent-garden/research/X.md"))
        for name in ("../x", "/tmp/x", "a/../x", "./x", "a\\b", ""):
            self.assertFalse(recover.safe(name), name)

    def test_allowlist_blocks_api_metadata(self):
        self.assertTrue(recover.chosen("docs/corpora/emergent-garden/research/WAVE-5-SOURCE-REVIEW.md"))
        self.assertTrue(recover.chosen("scripts/research/collect_emergent_garden_youtube_v2.py"))
        for name in ("docs/corpora/emergent-garden/data/youtube-channel-inventory-v1.json",
                     "docs/corpora/emergent-garden/private/comment.txt",
                     ".github/workflows/collector.yml", "README.md", "other/file.md"):
            self.assertFalse(recover.chosen(name), name)

    def test_missing_manifest_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "a.zip"
            with zipfile.ZipFile(path, "w") as zipfile_:
                zipfile_.writestr("foo", "bar")
            with zipfile.ZipFile(path) as zipfile_:
                with self.assertRaisesRegex(ValueError, "MISSING_MANIFEST"):
                    recover.verify_zip(zipfile_)

    def test_empty_manifest_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "a.zip"
            with zipfile.ZipFile(path, "w") as zipfile_:
                zipfile_.writestr("BUNDLE-MANIFEST.json", json.dumps({"files": []}))
            with zipfile.ZipFile(path) as zipfile_:
                with self.assertRaisesRegex(ValueError, "INVALID_MANIFEST"):
                    recover.verify_zip(zipfile_)

    def test_symlinked_staging_root_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            real = root / "real"
            real.mkdir()
            link = root / "alias"
            link.symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "DESTINATION_SYMLINK"):
                recover.safe_destination(link, "docs/a.md")

    def test_symlinked_child_directory_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            outside = root / "outside"
            outside.mkdir()
            base = root / "staged"
            base.mkdir()
            (base / "docs").symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "DESTINATION_PATH_SYMLINK"):
                recover.safe_destination(base, "docs/README.md")
            self.assertFalse((outside / "README.md").exists())

    def test_symlinked_final_file_rejected_even_if_content_matches(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = root / "staged"
            base.mkdir()
            outside = root / "sensitive.md"
            outside.write_text("same text")
            (base / "file.md").symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "DESTINATION_PATH_SYMLINK"):
                recover.safe_destination(base, "file.md")

    def test_historical_bundle_optional(self):
        bundle = Path("/mnt/data/emergent-garden-wave5-verified-handoff.zip")
        if not bundle.is_file():
            self.skipTest("Conversation attachment not available on GitHub CI runner")
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp)
            result = recover.stage(bundle, destination)
            self.assertEqual(result["verified_archive_members"], 72)
            self.assertGreaterEqual(result["staged_files"], 40)
            self.assertFalse((destination / "docs/corpora/emergent-garden/data/youtube-channel-inventory-v1.json").exists())
            self.assertTrue((destination / "docs/corpora/emergent-garden/research/WAVE-5-SOURCE-REVIEW.md").exists())
            recover.stage(bundle, destination)

    def test_archive_hash_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "a.zip"
            path.write_bytes(b"definitely not the archive")
            with self.assertRaisesRegex(ValueError, "ARCHIVE_HASH_MISMATCH"):
                recover.stage(path, Path(temp) / "out")

if __name__ == "__main__":
    unittest.main()
