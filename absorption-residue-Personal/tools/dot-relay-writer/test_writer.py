"""Guard + apply tests for the Dot relay writer against an in-memory sqlite
carrying migrations 0001-0003 + 0007 (the real apply path runs on D1)."""
import importlib.util, json, sqlite3, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("writer", Path(__file__).with_name("writer.py"))
writer = importlib.util.module_from_spec(spec); spec.loader.exec_module(writer)

SCHEMA = "".join((ROOT / "db/migrations" / f).read_text() for f in
                 ["0001_init.sql", "0002_economics.sql", "0003_display_summaries.sql", "0007_dot_relay.sql"])

BASE = {"type": "status", "project_id": "job-cockpit", "status": "in_progress",
        "percent": 40, "text": "writer lane green", "base_updated_at": "2026-10-21T00:00:00Z"}

class WriterTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.executescript(SCHEMA)
        self.conn.execute("INSERT INTO projects(id,name,grp,updated_at,updated_by) VALUES ('job-cockpit','Job Cockpit','ops','2026-10-20T00:00:00Z','test')")
        self.conn.commit()
        self.db = writer.SqliteBackend.__new__(writer.SqliteBackend)
        self.db.conn = self.conn

    def tearDown(self):
        self.conn.close()

    def apply(self, **over):
        rec = dict(BASE); rec.update(over)
        return writer.apply_record(self.db, rec)

    def one(self, sql, p=()): return self.conn.execute(sql, p).fetchone()[0]

    def test_migration_idempotent(self):
        self.conn.executescript((ROOT / "db/migrations/0007_dot_relay.sql").read_text())
        names = {r[0] for r in self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"asks","tasks","agents","escalations","dot_status","dot_digest",
                         "size_classes","estimates","actuals","velocity_log","dependency_edges"} <= names)

    def test_happy_path_applies_atomically(self):
        res = self.apply()
        self.assertTrue(res["applied"])
        self.assertEqual(self.one("SELECT COUNT(*) FROM dot_status"), 1)
        self.assertEqual(self.one("SELECT updated_by FROM dot_status"), "dot")
        self.assertEqual(self.one("SELECT action FROM events ORDER BY id DESC LIMIT 1"), "dot_status")
        self.assertIsNotNone(self.one("SELECT v FROM meta WHERE k='updated'"))

    def test_percent_out_of_range_rejected(self):
        self.assertEqual(self.apply(percent=101)["reason"], "percent-range")
        self.assertEqual(self.apply(percent="40")["reason"], "percent-range")

    def test_unknown_needs_cause_and_start_step(self):
        self.assertEqual(self.apply(percent=None, unknown_cause="no_estimate")["reason"], "unknown-needs-cause-and-start-step")
        res = self.apply(percent=None, unknown_cause="no_estimate", start_step="size the task")
        self.assertTrue(res["applied"])

    def test_project_allowlist(self):
        self.assertEqual(self.apply(project_id="not-a-project")["reason"], "project-not-allowlisted")
        self.assertEqual(self.apply(project_id="BAD ID")["reason"], "bad-project-id")

    def test_status_vocab(self):
        self.assertEqual(self.apply(status="on fire")["reason"], "status-vocab")
        self.assertTrue(self.apply(status="blocked")["applied"])

    def test_length_cap(self):
        self.assertEqual(self.apply(text="x" * 4001)["reason"], "over-length-cap")

    def test_secret_scrub_rejects_without_leaking(self):
        res = self.apply(text="here is the key api_key=ABCDEF1234567890 live")
        self.assertFalse(res["applied"]); self.assertEqual(res["reason"], "secret-pattern")
        event = self.one("SELECT after FROM events WHERE action='guard_reject' ORDER BY id DESC LIMIT 1")
        self.assertNotIn("ABCDEF1234567890", event)
        self.assertEqual(self.one("SELECT COUNT(*) FROM dot_status"), 0)

    def test_stale_clobber(self):
        self.assertEqual(self.apply(base_updated_at="2026-10-19T00:00:00Z")["reason"], "stale-clobber")

    def test_rate_limit(self):
        for i in range(60):
            self.conn.execute("INSERT INTO dot_status(project_id,status,base_updated_at,recorded_at) VALUES ('job-cockpit','in_progress','2026-10-21T00:00:00Z',strftime('%Y-%m-%dT%H:%M:%fZ','now'))")
        self.conn.commit()
        self.assertEqual(self.apply()["reason"], "rate-limit")

    def test_edge_cycle_rejected(self):
        ok = writer.apply_record(self.db, {"type": "edge", "from_task_id": "a", "to_task_id": "b", "kind": "blocks"})
        self.assertTrue(ok["applied"])
        cyc = writer.apply_record(self.db, {"type": "edge", "from_task_id": "b", "to_task_id": "a", "kind": "blocks"})
        self.assertEqual(cyc["reason"], "dependency-cycle")
        self.assertEqual(self.one("SELECT COUNT(*) FROM dependency_edges"), 1)
        dup = writer.apply_record(self.db, {"type": "edge", "from_task_id": "a", "to_task_id": "b", "kind": "blocks"})
        self.assertEqual(dup["reason"], "duplicate-edge")
        self_edge = writer.apply_record(self.db, {"type": "edge", "from_task_id": "a", "to_task_id": "a", "kind": "blocks"})
        self.assertEqual(self_edge["reason"], "dependency-cycle")

    def test_estimate_reestimate_appends(self):
        for h in (4.0, 6.0):
            self.assertTrue(writer.apply_record(self.db, {"type":"estimate","task_id":"t1","est_hours_p50":h,"basis":"past PR open-to-merge"})["applied"])
        self.assertEqual(self.one("SELECT COUNT(*) FROM estimates WHERE task_id='t1'"), 2)

    def test_velocity_derivation(self):
        self.conn.execute("INSERT INTO size_classes(name,base_hours_p50,base_hours_p90) VALUES ('S',2,4)")
        writer.apply_record(self.db, {"type":"estimate","task_id":"t1","size_class_id":1,"est_hours_p50":2.0})
        writer.apply_record(self.db, {"type":"actual","task_id":"t1","started_at":"2026-10-20T10:00:00Z","finished_at":"2026-10-20T13:00:00Z","actual_hours":3.0,"source":"events"})
        res = writer.derive_velocity(self.db, "instinct:main", "2026-10-20", "2026-10-21")
        self.assertEqual(res["tasks_done"], 1)
        self.assertAlmostEqual(res["ratio"], 1.5)
        self.assertFalse(res["eta_samples_ok"])  # N=3 minimum samples

    def test_cli_path_traversal_rejected(self):
        import os, tempfile
        with tempfile.TemporaryDirectory() as td:
            os.environ["WRITER_ALLOWED_ROOTS"] = os.path.join(td, "allowed")
            os.makedirs(os.environ["WRITER_ALLOWED_ROOTS"])
            outside = os.path.join(td, "rec.json")
            Path(outside).write_text(json.dumps(BASE))
            try:
                with self.assertRaises(writer.Reject):
                    writer.cmd_apply(self.db, os.path.join(td, "allowed", "..", "rec.json"))
            finally:
                del os.environ["WRITER_ALLOWED_ROOTS"]

    def test_spool_symlink_escape_rejected(self):
        import os, tempfile
        with tempfile.TemporaryDirectory() as td:
            spool = os.path.join(td, "spool"); os.makedirs(spool)
            secret = os.path.join(td, "secret.json")
            Path(secret).write_text(json.dumps(BASE))
            os.symlink(secret, os.path.join(spool, "link.json"))
            os.environ["WRITER_ALLOWED_ROOTS"] = td
            try:
                results = writer.cmd_spool(self.db, spool)
            finally:
                del os.environ["WRITER_ALLOWED_ROOTS"]
            self.assertEqual(results, [("link.json", {"applied": False, "reason": "symlink escape"})])
            self.assertTrue(Path(secret).exists())  # never opened/moved

    def test_unknown_kind_rejected(self):
        self.assertEqual(writer.apply_record(self.db, {"type":"shell","cmd":"rm -rf /"})["reason"], "unknown-type")

    def _seed_status(self):
        self.apply()
        return self.one("SELECT id FROM dot_status ORDER BY id DESC LIMIT 1")

    def lane(self, rtype, **over):
        rec = {"type": rtype, "actor": "instinct:main", "project_id": "job-cockpit"}; rec.update(over)
        return writer.apply_record(self.db, rec)

    def test_confirm_by_lane_writes_display_shape(self):
        sid = self._seed_status()
        res = self.lane("confirm", confirm_ref=sid)
        self.assertTrue(res["applied"])
        row = self.conn.execute("SELECT actor, project_id, after FROM events WHERE action='dot_status_confirm'").fetchone()
        self.assertEqual(row[0], "instinct:main")
        self.assertEqual(row[1], "job-cockpit")
        self.assertEqual(json.loads(row[2]), {"confirm_ref": sid})

    def test_dot_cannot_confirm_itself(self):
        sid = self._seed_status()
        for actor in ("dot", "dot:relay", None, "", "Dot", "x" * 80):
            res = self.lane("confirm", confirm_ref=sid, actor=actor)
            self.assertFalse(res["applied"], actor)
        self.assertEqual(self.one("SELECT COUNT(*) FROM events WHERE action='dot_status_confirm'"), 0)

    def test_confirm_needs_existing_ref_in_same_project(self):
        sid = self._seed_status()
        self.assertEqual(self.lane("confirm", confirm_ref=sid + 99)["reason"], "unknown-status-ref")
        self.assertEqual(self.lane("confirm", confirm_ref=True)["reason"], "bad-confirm-ref")
        self.assertEqual(self.lane("confirm", confirm_ref="1")["reason"], "bad-confirm-ref")
        self.conn.execute("INSERT INTO projects(id,name,grp,updated_at,updated_by) VALUES ('other','Other','ops','2026-10-20T00:00:00Z','test')")
        self.conn.commit()
        self.assertEqual(self.lane("confirm", confirm_ref=sid, project_id="other")["reason"], "unknown-status-ref")

    def test_flag_stale_and_note(self):
        sid = self._seed_status()
        self.assertTrue(self.lane("flag_stale", confirm_ref=sid, reason="no update in 2h")["applied"])
        self.assertTrue(self.lane("note", text="waiting on review")["applied"])
        self.assertTrue(self.lane("note", text="about this one", confirm_ref=sid)["applied"])
        self.assertEqual(self.one("SELECT COUNT(*) FROM events WHERE action IN ('dot_status_flag_stale','dot_status_note')"), 3)
        self.assertEqual(self.lane("note", text="   ")["reason"], "empty-note")
        self.assertEqual(self.lane("note", text="x" * 1001)["reason"], "over-length-cap")

    def test_lane_actions_scrub_secrets_without_leaking(self):
        sid = self._seed_status()
        res = self.lane("note", text="token=abcd1234efgh5678", confirm_ref=sid)
        self.assertEqual(res["reason"], "secret-pattern")
        leaked = self.conn.execute("SELECT COUNT(*) FROM events WHERE after LIKE '%abcd1234%'").fetchone()[0]
        self.assertEqual(leaked, 0)

    def test_lane_actions_never_modify_dot_status(self):
        sid = self._seed_status()
        before = self.conn.execute("SELECT * FROM dot_status").fetchall()
        self.lane("confirm", confirm_ref=sid); self.lane("flag_stale", confirm_ref=sid); self.lane("note", text="n")
        self.assertEqual(self.conn.execute("SELECT * FROM dot_status").fetchall(), before)

    def test_lane_rate_limit(self):
        sid = self._seed_status()
        for _ in range(writer.MAX_LANE_ACTIONS_PER_HOUR):
            self.assertTrue(self.lane("confirm", confirm_ref=sid)["applied"])
        self.assertEqual(self.lane("confirm", confirm_ref=sid)["reason"], "rate-limit")
        self.assertTrue(self.lane("confirm", confirm_ref=sid, actor="other-lane")["applied"])


    def _seed_ask(self, updated_at="2026-10-16T20:58:10.903628+00:00"):
        self.conn.executescript((ROOT / "db/asks-proposed.sql").read_text())
        cur = self.conn.execute(
            "INSERT INTO ask_display(original_text,interpretation,reported_state,updated_at) VALUES (?,?,?,?)",
            ("orig", "interp", "reported", updated_at))
        self.conn.commit()
        return cur.lastrowid

    def _proof(self, ask_id, **over):
        rec = {"type": "ask_proof", "actor": "instinct:jobs", "ask_id": ask_id,
               "result": "pass", "unit_ref": "verified the thing",
               "evidence": [{"kind": "probe", "ref": "https://example.com/x", "observed_at": "2026-10-22T14:54:47-07:00"}],
               "base_updated_at": "2026-10-16T20:58:10.903628+00:00"}
        rec.update(over)
        return writer.apply_record(self.db, rec)

    def test_ask_proof_happy_path_events_row_only(self):
        aid = self._seed_ask()
        res = self._proof(aid)
        self.assertTrue(res["applied"], res)
        actor, pid, after = self.conn.execute(
            "SELECT actor, project_id, after FROM events WHERE action='ask_proof'").fetchone()
        self.assertEqual(actor, "instinct:jobs")
        self.assertIsNone(pid)
        payload = json.loads(after)
        self.assertEqual(payload["ask_id"], aid)
        self.assertEqual(payload["result"], "pass")
        self.assertEqual(payload["unit_ref"], "verified the thing")
        self.assertEqual(payload["evidence"][0]["kind"], "probe")
        self.assertTrue(payload["dedupe_sha"])
        row = self.conn.execute("SELECT verified_state, reviewed, reconciled_at FROM ask_display WHERE id=?", (aid,)).fetchone()
        self.assertEqual(row[0], "needs_reconciliation")
        self.assertEqual(row[1], 0)
        self.assertIsNone(row[2])

    def test_ask_proof_actor_must_be_lane(self):
        aid = self._seed_ask()
        for actor in ("dot", "dot:relay", None, "", "Dot", "x" * 80):
            res = self._proof(aid, actor=actor)
            self.assertFalse(res["applied"], actor)
            self.assertEqual(res["reason"], "actor-not-a-lane")
        self.assertEqual(self.one("SELECT COUNT(*) FROM events WHERE action='ask_proof'"), 0)

    def test_ask_proof_ask_must_exist(self):
        aid = self._seed_ask()
        self.assertEqual(self._proof(aid + 99)["reason"], "unknown-ask")
        self.assertEqual(self._proof("not-an-int")["reason"], "bad-ask-id")
        self.assertEqual(self._proof(True)["reason"], "bad-ask-id")

    def test_ask_proof_result_vocab(self):
        aid = self._seed_ask()
        self.assertEqual(self._proof(aid, result="green")["reason"], "bad-result")
        for ok in ("pass", "fail", "partial"):
            self.assertTrue(self._proof(aid, result=ok,
                evidence=[{"kind": "probe", "ref": "https://example.com/" + ok, "observed_at": "2026-10-22T14:54:47Z"}])["applied"])

    def test_ask_proof_evidence_validation(self):
        aid = self._seed_ask()
        self.assertEqual(self._proof(aid, evidence=[])["reason"], "empty-evidence")
        self.assertEqual(self._proof(aid, evidence=None)["reason"], "empty-evidence")
        self.assertEqual(self._proof(aid, evidence=["x"])["reason"], "bad-evidence-item")
        self.assertEqual(self._proof(aid, evidence=[{"kind": "tweet", "ref": "https://x", "observed_at": "2026-10-22T14:54:47Z"}])["reason"], "bad-evidence-kind")
        self.assertEqual(self._proof(aid, evidence=[{"kind": "probe", "ref": "", "observed_at": "2026-10-22T14:54:47Z"}])["reason"], "empty-evidence-ref")
        self.assertEqual(self._proof(aid, evidence=[{"kind": "probe", "ref": "https://x", "observed_at": "yesterday"}])["reason"], "bad-timestamp")

    def test_ask_proof_stale_base_rejected(self):
        aid = self._seed_ask()
        res = self._proof(aid, base_updated_at="2026-10-15T00:00:00Z")
        self.assertEqual(res["reason"], "stale-clobber")

    def test_ask_proof_dedupe(self):
        aid = self._seed_ask()
        self.assertTrue(self._proof(aid)["applied"])
        dup = self._proof(aid)
        self.assertFalse(dup["applied"])
        self.assertEqual(dup["reason"], "duplicate-proof")
        changed = self._proof(aid, evidence=[{"kind": "probe", "ref": "https://example.com/other", "observed_at": "2026-10-22T15:00:00-07:00"}])
        self.assertTrue(changed["applied"])

    def test_ask_proof_offset_timestamps_accepted(self):
        aid = self._seed_ask()
        res = self._proof(aid, base_updated_at="2026-10-16T20:58:10.903628+00:00",
                          evidence=[{"kind": "screenshot", "ref": "shot.png", "observed_at": "2026-10-22T14:54:53-07:00"}])
        self.assertTrue(res["applied"], res)


if __name__ == "__main__":
    unittest.main()
