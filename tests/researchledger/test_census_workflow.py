"""Verify source refresh is manual, credential-isolated, and ephemeral.

These are static controls only; they cannot prove credentials are configured or
that the live API is accessible. GitHub's default-branch workflow restrictions
remain the authoritative execution gate.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github/workflows"

class WorkflowGuards(unittest.TestCase):
    def test_fresh_census_manual_only(self):
        content = (WORKFLOWS / "researchledger-youtube-census-manual.yml").read_text()
        self.assertIn("workflow_dispatch:", content)
        self.assertNotIn("pull_request:", content)
        self.assertNotIn("push:", content)
        self.assertNotIn("schedule:", content)

    def test_destination_secret_not_embedded(self):
        content = (WORKFLOWS / "researchledger-youtube-census-manual.yml").read_text()
        self.assertIn("secrets.YOUTUBE_API_KEY", content)
        self.assertNotIn("AIza", content)
        self.assertIn('ref: main', content)
        self.assertIn('persist-credentials: false', content)

    def test_no_automatic_false_success_or_permanent_storage(self):
        content = (WORKFLOWS / "researchledger-youtube-census-manual.yml").read_text()
        self.assertIn('PUBLIC_UPLOAD_RECONCILIATION_INCOMPLETE', content)
        self.assertIn('retention-days: 1', content)
        self.assertNotIn('git push', content)
        self.assertNotIn('contents: write', content)

    def test_historical_verification_no_secrets(self):
        content = (WORKFLOWS / "researchledger-corpus-offline.yml").read_text()
        self.assertIn('PRESERVATION-MANIFEST.json', content)
        self.assertNotIn('secrets.', content)
        self.assertIn('test_*.py', content)

if __name__ == "__main__":
    unittest.main()
