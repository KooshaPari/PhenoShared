import json, os, sqlite3, sys, time

DEST_DIR = r"G:\20261029T080923Z-restore-bb977ae26cbf4c5f"
DB = os.path.join(DEST_DIR, "corpus-restored.sqlite")
rec = {"phase": 2, "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

def out(k, v):
    rec[k] = v
    print("%s=%s" % (k, v), flush=True)

def done(code, note=""):
    rec["note"] = note
    rec["exit"] = code
    rec["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    print("RECEIPT_JSON=" + json.dumps(rec, sort_keys=True), flush=True)
    try:
        with open(os.path.join(DEST_DIR, "restore-receipt-phase2.json"), "x", encoding="utf-8") as f:
            json.dump(rec, f, indent=2, sort_keys=True)
    except Exception as e:
        print("RECEIPT_WRITE_FAILED=%s" % e, flush=True)
    sys.exit(code)

if not os.path.isfile(DB):
    done(3, "restored db missing")
out("db_bytes", os.path.getsize(DB))

uri = "file:" + DB.replace("\\", "/") + "?mode=ro&immutable=1"
t0 = time.time()
try:
    conn = sqlite3.connect(uri, uri=True, timeout=30)
except sqlite3.Error as e:
    done(4, "open failed: %s" % e)
out("sqlite_version", sqlite3.sqlite_version)

cur = conn.cursor()
try:
    qc = [r[0] for r in cur.execute("PRAGMA quick_check").fetchall()]
except sqlite3.Error as e:
    done(5, "quick_check error: %s" % e)
out("quick_check_rows", len(qc))
out("quick_check_result", qc[:3] if len(qc) <= 3 else qc[0])
qc_ok = (len(qc) == 1 and str(qc[0]).lower() == "ok")
out("quick_check_ok", qc_ok)
out("quick_check_seconds", round(time.time() - t0, 2))

# page geometry + aggregates (metadata only, no content)
try:
    out("page_size", cur.execute("PRAGMA page_size").fetchone()[0])
    out("page_count", cur.execute("PRAGMA page_count").fetchone()[0])
    out("freelist_count", cur.execute("PRAGMA freelist_count").fetchone()[0])
    out("journal_mode", cur.execute("PRAGMA journal_mode").fetchone()[0])
    out("encoding", cur.execute("PRAGMA encoding").fetchone()[0])
    out("schema_version", cur.execute("PRAGMA schema_version").fetchone()[0])
    out("application_id", cur.execute("PRAGMA application_id").fetchone()[0])
except sqlite3.Error as e:
    out("pragma_warn", str(e))

tables = [r[0] for r in cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
out("table_count", len(tables))
out("tables", tables)
views = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")]
out("view_count", len(views))
out("views", views)

counts = {}
for t in tables:
    if t.startswith("items__fts") or "_fts_" in t:
        continue
    try:
        counts[t] = cur.execute('SELECT COUNT(*) FROM "%s"' % t.replace('"', '""')).fetchone()[0]
    except sqlite3.Error:
        counts[t] = None
out("row_counts", counts)
for key in ("items", "sources", "attachments"):
    if key in counts:
        out("count_%s" % key, counts[key])

# representative non-sensitive aggregate
agg = []
try:
    if "sources" in tables:
        cols = [d[1] for d in cur.execute('PRAGMA table_info("sources")')]
        label = next((c for c in ("name", "title", "kind", "source", "id") if c in cols), cols[0])
        if "items" in tables and "source_id" in [d[1] for d in cur.execute('PRAGMA table_info("items")')]:
            for row in cur.execute(
                'SELECT s."%s", COUNT(i.rowid) FROM "sources" s LEFT JOIN "items" i ON i.source_id = s.rowid GROUP BY 1 ORDER BY 2 DESC LIMIT 15' % label):
                agg.append({"source": row[0], "items": row[1]})
        else:
            for row in cur.execute('SELECT "%s", COUNT(*) FROM "sources" GROUP BY 1 ORDER BY 2 DESC LIMIT 15' % label):
                agg.append({"source": row[0], "n": row[1]})
except sqlite3.Error as e:
    out("aggregate_warn", str(e))
out("aggregate_by_source", agg)
out("aggregate_seconds", round(time.time() - t0, 2))

# optional full integrity check under a wall-clock budget
budget = 600
start = time.time()
def guard():
    return 1 if (time.time() - start) > budget else 0
try:
    conn.set_progress_handler(guard, 20000)
    ic = [r[0] for r in cur.execute("PRAGMA integrity_check(20)").fetchall()]
    out("integrity_check_rows", len(ic))
    out("integrity_check_result", ic[:5])
    out("integrity_check_ok", len(ic) == 1 and ic[0] == "ok")
    out("integrity_check_seconds", round(time.time() - start, 2))
except sqlite3.Error as e:
    out("integrity_check", "NOT_COMPLETED: %s" % e)
finally:
    try:
        conn.set_progress_handler(None, 0)
    except sqlite3.Error:
        pass

try:
    conn.close()
except sqlite3.Error:
    pass
out("phase2_total_seconds", round(time.time() - t0, 2))
done(0 if qc_ok else 8, "phase2 ok" if qc_ok else "quick_check reported problems")
