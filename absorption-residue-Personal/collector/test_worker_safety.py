"""Offline safety tests for the existing Cloudflare Worker collector.

The Worker is the system of record; this is a source-contract audit to
prevent unsafe automated promotion of listings into verified opportunities.
"""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKER = (ROOT / "jobs-collector" / "index.js").read_text()

class WorkerSafetyTests(unittest.TestCase):
    def test_collector_does_not_apply_or_message(self):
        self.assertNotIn("api.linkedin.com", WORKER)
        self.assertNotIn("applyToJob(", WORKER)
    def test_aggregated_posts_have_unverified_flag(self):
        self.assertIn("'link_unverified'", WORKER)
    def test_no_false_remote_la_eligibility(self):
        # Remote is a discovery tier only; eligibility is never inferred.
        self.assertIn('Discovery only; never implies LA/California work eligibility', WORKER)
        self.assertIn('location_eligible:null', WORKER)
    def test_closure_requires_direct_confirmation(self):
        # Absence from a board snapshot cannot be treated as confirmed closure.
        self.assertNotIn("UPDATE job SET status='closed' WHERE status='open' AND last_seen", WORKER)
    def test_la_excludes_orange_county(self):
        # Irvine belongs in rest-of-SoCal, not LA.
        self.assertNotIn("pasadena|irvine|long beach", WORKER)
    def test_no_unverified_public_candidates(self):
        # /candidates currently exposes collected open records without official verification.
        self.assertIn("verification_status:'unverified'", WORKER)
    def test_health_endpoint_reports_staleness_and_unverified_count(self):
        self.assertIn("u.pathname === '/health'", WORKER)
        self.assertIn("ageHours > 36", WORKER)
        self.assertIn("strict_verified_la: null", WORKER)
    def test_review_endpoint_is_explicitly_unverified(self):
        self.assertIn("u.pathname === '/review'", WORKER)
        self.assertIn("kind:'unverified_la_review_queue'", WORKER)
        self.assertIn("graduation_eligible:null", WORKER)
    def test_python_collector_does_not_auto_verify(self):
        source=(ROOT / "collector" / "collect.py").read_text()
        self.assertIn("Discovery is NOT verification", source)
    def test_source_registry_valid(self):
        data=json.loads((ROOT / "collector" / "sources.json").read_text())
        self.assertGreaterEqual(len(data["sources"]), 5)
        keys=[(x["provider"],x["slug"]) for x in data["sources"]]
        self.assertEqual(len(keys),len(set(keys)))

if __name__ == "__main__":
    unittest.main()
