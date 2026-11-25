"""Spool directories plus a message-id dedupe table (sqlite, stdlib)."""
import json, os, sqlite3, uuid
from pathlib import Path

DIRS = ("pending", "done", "rejected", "quarantine")

class Spool:
    def __init__(self, root):
        self.root = Path(root)
        for d in DIRS:
            (self.root / d).mkdir(parents=True, exist_ok=True)
            os.chmod(self.root / d, 0o700)
        self.seen = sqlite3.connect(str(self.root / "dedupe.db"))
        self.seen.execute("CREATE TABLE IF NOT EXISTS seen(source TEXT NOT NULL, message_id TEXT NOT NULL, ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(source, message_id))")
        self.seen.commit()

    def seen_before(self, source, message_id):
        return self.seen.execute("SELECT 1 FROM seen WHERE source=? AND message_id=?", (source, message_id)).fetchone() is not None

    def mark_seen(self, source, message_id):
        self.seen.execute("INSERT OR IGNORE INTO seen(source, message_id) VALUES (?,?)", (source, message_id))
        self.seen.commit()

    def reject_budget(self, source, cap):
        """True while this source is under `cap` guard_reject rows this hour. Always counts."""
        import time
        hour = int(time.time() // 3600)
        self.seen.execute("CREATE TABLE IF NOT EXISTS rejects(source TEXT NOT NULL, hour INTEGER NOT NULL, n INTEGER NOT NULL, PRIMARY KEY(source, hour))")
        self.seen.execute("INSERT OR IGNORE INTO rejects(source,hour,n) VALUES (?,?,0)", (source, hour))
        self.seen.execute("UPDATE rejects SET n=n+1 WHERE source=? AND hour=?", (source, hour))
        n = self.seen.execute("SELECT n FROM rejects WHERE source=? AND hour=?", (source, hour)).fetchone()[0]
        self.seen.commit()
        return n <= cap

    def first_time(self, source, message_id):
        """True the first time a (source, message_id) is seen, False on replay."""
        cur = self.seen.execute("INSERT OR IGNORE INTO seen(source, message_id) VALUES (?,?)", (source, message_id))
        self.seen.commit()
        return cur.rowcount == 1

    def put_pending(self, record):
        path = self.root / "pending" / (uuid.uuid4().hex + ".json")
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(record, f)
        return path

    def move(self, path, dest, reason=None):
        target = self.root / dest / Path(path).name
        os.replace(path, target)
        if reason:
            (self.root / dest / (Path(path).name + ".reason")).write_text(str(reason)[:200])
        return target

    def close(self):
        self.seen.close()
