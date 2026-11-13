import tempfile, unittest
from pathlib import Path
from canonicalize import export

class CanonicalSnapshotTest(unittest.TestCase):
 def test_stored_snapshot(self):
  root=Path(__file__).resolve().parents[1]
  db=root/'collector/data/jobs.sqlite3'
  if not db.exists():self.skipTest('No local snapshot')
  with tempfile.TemporaryDirectory() as d:
   x=export(db,root/'collector/data/whatnot.json',Path(d)/'out.json',now='2026-10-12T00:00:00Z')
   print('source audit',x['raw_ats_rows'],x['whatnot_observations'],x['unique_canonical_jobs'],x['la_review_candidates'])
   self.assertIsNone(x['verified_eligible_la'])
