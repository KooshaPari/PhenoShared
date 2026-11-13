"""Offline D1/SQLite migration tests for canonical requisition provenance."""
from pathlib import Path
import sqlite3
import unittest

SQL=Path(__file__).resolve().parents[1].joinpath('jobs-collector/migrations/0002-verification.sql').read_text()

class SchemaContractTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.executescript(SQL)
    def tearDown(self): self.db.close()

    def test_repeatable_migration(self):
        self.db.executescript(SQL)
        rows=self.db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        names={x[0] for x in rows}
        self.assertTrue({'canonical_job','canonical_source','job_verification','source_checkpoint'} <= names)

    def test_same_job_multiple_sources(self):
        canonical='ashby:whatnot:00000000-0000-4000-8000-000000000000'
        self.db.execute("INSERT INTO canonical_job(canonical_id,company,title,official_url,geography,first_seen,last_seen) VALUES (?,?,?,?,?,?,?)",
          (canonical,'Whatnot','Software Engineer, 2027 New Grad','https://www.whatnot.com/careers/roles/00000000-0000-4000-8000-000000000000','la_metro','2026-10-12','2026-10-12'))
        for source,ref in [('whatnot-official','00000000-0000-4000-8000-000000000000'),('github-list','index-42')]:
            self.db.execute("INSERT INTO canonical_source(source_kind,source_id,canonical_id,source_url,first_seen,last_seen) VALUES (?,?,?,?,?,?)",
               (source,ref,canonical,'https://www.whatnot.com/careers/discover','2026-10-12','2026-10-12'))
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM canonical_job').fetchone()[0],1)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM canonical_source').fetchone()[0],2)

    def test_verification_not_inferred_by_discovery(self):
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM job_verification').fetchone()[0],0)

if __name__=='__main__': unittest.main()
