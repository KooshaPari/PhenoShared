import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from verify_research_bundle import MANIFEST, REQUIRED, verify


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.required = frozenset({"README.md", "data/record.json"})
        self.root.joinpath("data").mkdir()
        self.root.joinpath("README.md").write_text("Derived research, not a reproduction.\n")
        self.root.joinpath("data/record.json").write_text('{"state":"partial"}\n')
        self.rows = []
        for name in sorted(self.required):
            raw = (self.root / name).read_bytes()
            self.rows.append({"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
        self.save()

    def tearDown(self):
        self.tmp.cleanup()

    def save(self):
        (self.root / MANIFEST).write_text(json.dumps({"files": self.rows}))

    def result(self):
        return verify(self.root, self.required)

    def test_valid_bundle(self):
        self.assertTrue(self.result()["passed"])

    def test_content_tamper(self):
        (self.root / "README.md").write_text("Altered.\n")
        self.assertFalse(self.result()["passed"])

    def test_missing_file(self):
        (self.root / "data/record.json").unlink()
        self.assertFalse(self.result()["passed"])

    def test_unlisted_file(self):
        (self.root / "extra.txt").write_text("untracked")
        self.assertFalse(self.result()["passed"])

    def test_missing_required_role(self):
        self.rows = [r for r in self.rows if r["path"] == "README.md"]
        self.save()
        self.assertFalse(self.result()["passed"])

    def test_duplicate_entry(self):
        self.rows.append(dict(self.rows[0]))
        self.save()
        self.assertFalse(self.result()["passed"])

    def test_path_traversal(self):
        self.rows[0]["path"] = "../README.md"
        self.save()
        self.assertFalse(self.result()["passed"])

    def test_symlink(self):
        p = self.root / "README.md"
        p.unlink()
        p.symlink_to(self.root / "data/record.json")
        self.assertFalse(self.result()["passed"])

    def test_manifest_without_files(self):
        (self.root / MANIFEST).write_text('{"status":"passed"}')
        self.assertFalse(self.result()["passed"])

    def test_three_file_status_stub(self):
        for p in sorted(self.root.rglob("*"), reverse=True):
            if p.is_file():
                p.unlink()
        for name in ("README.md", "VALIDATION.json", "SHA256SUMS"):
            (self.root / name).write_text("{}")
        self.assertFalse(verify(self.root)["passed"])

    def test_matching_hash_but_invalid_json(self):
        raw = b"not valid JSON"
        (self.root / "data/record.json").write_bytes(raw)
        row = next(r for r in self.rows if r["path"] == "data/record.json")
        row.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        self.save()
        self.assertFalse(self.result()["passed"])

    def test_default_requires_research_payload(self):
        self.assertFalse(verify(self.root, REQUIRED)["passed"])


if __name__ == "__main__":
    unittest.main()
