"""The credentialed collector must never run on PRs or expose secrets to setup actions."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/researchledger-youtube-census-manual.yml"

class ManualAcquisitionPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_operator_only_trigger(self):
        self.assertIn("on:\n  workflow_dispatch:", self.workflow)
        self.assertNotIn("\n  pull_request:", self.workflow)
        self.assertNotIn("\n  push:", self.workflow)
        self.assertNotIn("\n  schedule:", self.workflow)

    def test_secret_only_in_capture_step(self):
        text = self.workflow
        start = text.index("      - name: Collect fresh public API inventory")
        end = text.index("      - name: Upload short-lived", start)
        self.assertNotIn("secrets.YOUTUBE_API_KEY", text[:start])
        self.assertEqual(text[start:end].count("secrets.YOUTUBE_API_KEY"), 1)
        self.assertNotIn("secrets.YOUTUBE_API_KEY", text[end:])

    def test_read_only_and_ephemeral(self):
        self.assertIn("permissions:\n  contents: read", self.workflow)
        self.assertIn("persist-credentials: false", self.workflow)
        self.assertIn("retention-days: 1", self.workflow)
        self.assertIn("PUBLIC_UPLOAD_RECONCILIATION_INCOMPLETE", self.workflow)

    def test_no_direct_git_publication(self):
        self.assertNotIn("git push", self.workflow)
        self.assertNotIn("git commit", self.workflow)
        self.assertNotIn("actions/create-github-app-token", self.workflow)

if __name__ == "__main__":
    unittest.main()
