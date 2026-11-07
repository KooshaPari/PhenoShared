import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[2] / "scripts/researchledger/locate_historical_commit.py"
spec = importlib.util.spec_from_file_location("locator", MODULE)
locator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(locator)


@unittest.skipUnless(shutil.which("git"), "Git executable required")
class LocatorTests(unittest.TestCase):
    @staticmethod
    def git(path, *args):
        return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()

    def test_exact_commit_can_be_found_without_checkout(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "existing-repo"
            repo.mkdir()
            self.git(repo, "init", "-q")
            self.git(repo, "config", "user.email", "test@example.invalid")
            self.git(repo, "config", "user.name", "Fixture")
            (repo / "tracked.txt").write_text("historical")
            self.git(repo, "add", "tracked.txt")
            self.git(repo, "commit", "-qm", "fixture")
            commit = self.git(repo, "rev-parse", "HEAD")
            result = locator.locate([root], commit)
            self.assertEqual(result["state"], "EXACT_COMMIT_FOUND")
            self.assertEqual(result["repositories_checked"], 1)
            self.assertEqual(result["matches"][0]["path"], str(repo))
            self.assertEqual((repo / "tracked.txt").read_text(), "historical")

    def test_missing_commit_not_misreported_as_present(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "existing-repo"
            repo.mkdir()
            self.git(repo, "init", "-q")
            result = locator.locate([root])
            self.assertEqual(result["state"], "NOT_FOUND_IN_INSPECTED_ROOTS")
            self.assertEqual(result["repositories_checked"], 1)

    def test_nonexistent_root_is_bounded_empty(self):
        with tempfile.TemporaryDirectory() as temp:
            result = locator.locate([Path(temp) / "missing"])
            self.assertEqual(result["repositories_checked"], 0)
            self.assertFalse(result["exhaustive"])

    def test_invalid_sha_rejected(self):
        with self.assertRaisesRegex(ValueError, "INVALID_COMMIT_HASH"):
            locator.locate([], "not-a-commit")

    def test_symlink_root_not_traversed(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            (p / "real").mkdir()
            (p / "link").symlink_to(p / "real", target_is_directory=True)
            self.assertEqual(list(locator.repositories(p / "link")), [])

    def test_bare_repo_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            bare = p / "backup.git"
            self.git(p, "init", "--bare", str(bare))
            found = list(locator.repositories(p))
            self.assertEqual(found, [bare])


if __name__ == "__main__":
    unittest.main()
