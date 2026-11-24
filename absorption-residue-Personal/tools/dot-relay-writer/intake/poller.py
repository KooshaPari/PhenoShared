#!/usr/bin/env python3
"""Spool poller: adapters -> spool/pending -> relay writer -> done|rejected.

Poll every 5 minutes, back off on errors, write an hourly heartbeat events row
so silence is visible. Message bodies are untrusted data: only fenced JSON
blocks are read, only Dot record types are accepted, everything else is dropped.
Quarantine and reject events never carry message content.

Env (no secrets in this file):
  INTAKE_DB            sqlite:/path or d1:DATABASE (writer backends)
  INTAKE_SPOOL         spool root dir
  INTAKE_MAIL_ALLOW    comma list of allowed From addresses
  INTAKE_MAIL_ENABLED  must be "1" or the mail leg stays off
  INTAKE_MAIL_CMD      command printing JSON lines {"id","sender","body"}
  INTAKE_DISCORD_ALLOW comma list of "<channel_id>:<author_id>"
  INTAKE_DISCORD_CMD   command printing JSON lines, same shape
"""
import datetime, json, os, shlex, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import writer
from intake.adapters import MailAdapter, DiscordAdapter, command_fetcher
from intake.extract import extract_records
from intake.spool import Spool

POLL_SECONDS = 300
HEARTBEAT_SECONDS = 3600
MAX_BACKOFF = 1800
# Dot may only post these. confirm / flag_stale / note are lane actions: a Dot
# source must never be able to forge a lane's confirmation.
# "actual" is excluded: actuals feed velocity/ETA, which only lane-confirmed data may drive.
DOT_TYPES = frozenset({"status", "digest", "edge", "estimate"})
# Attribution fields are forced to "dot" on every intake-sourced record.
FORCED_ATTRIBUTION = ("recorded_by", "estimated_by", "created_by")
REJECT_CAP_PER_HOUR = 20

def _parse_ts(s):
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=datetime.timezone.utc)
    except (TypeError, ValueError):
        return None

def heartbeat_due(db, now=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    last = _parse_ts(db.one("SELECT MAX(ts) FROM events WHERE action='intake_heartbeat'"))
    return last is None or (now - last).total_seconds() >= HEARTBEAT_SECONDS

def write_heartbeat(db, stats):
    writer.log_event(db, "intake_heartbeat", None, json.dumps(stats, sort_keys=True), "intake")
    db.commit()

def reject(db, spool, stats, source, reason):
    """guard_reject row, capped per source per hour; past the cap only count."""
    if spool.reject_budget(source, REJECT_CAP_PER_HOUR):
        writer.log_reject(db, source, reason)
    else:
        stats["reject_suppressed"] += 1

def process_message(db, spool, adapter, msg, stats):
    if spool.seen_before(msg.source, msg.message_id):
        stats["duplicate"] += 1
        return
    _process(db, spool, adapter, msg, stats)
    # Dedupe row is written only after the message was fully handled, so a
    # crash mid-apply is retried instead of silently dropped.
    spool.mark_seen(msg.source, msg.message_id)

def _process(db, spool, adapter, msg, stats):
    if not adapter.is_allowed(msg):
        # Content-free: only the source name is recorded.
        reject(db, spool, stats, msg.source, "sender-not-allowlisted")
        stats["quarantined"] += 1
        return
    records, malformed = extract_records(msg.body)
    stats["malformed"] += malformed
    if malformed and not records:
        reject(db, spool, stats, msg.source, "malformed-json")
    if not records:
        stats["ignored"] += 1
        return
    for rec in records:
        rtype = rec.get("type", "status")
        if rtype not in DOT_TYPES:
            reject(db, spool, stats, msg.source, "type-not-allowed-from-dot")
            stats["rejected"] += 1
            continue
        rec = dict(rec)
        for k in FORCED_ATTRIBUTION:
            rec[k] = "dot"
        path = spool.put_pending(rec)
        try:
            with open(path) as f:
                res = writer.apply_record(db, json.load(f))
        except (OSError, ValueError):
            res = {"applied": False, "reason": "unparseable"}
        if res.get("applied"):
            spool.move(path, "done"); stats["applied"] += 1
        else:
            spool.move(path, "rejected", res.get("reason")); stats["rejected"] += 1

def new_stats():
    return {"duplicate": 0, "quarantined": 0, "malformed": 0, "ignored": 0, "applied": 0, "rejected": 0, "reject_suppressed": 0}

def run_once(db, spool, adapters, now=None):
    stats = new_stats()
    for adapter in adapters:
        for msg in adapter.messages():
            process_message(db, spool, adapter, msg, stats)
    if heartbeat_due(db, now):
        write_heartbeat(db, stats)
    return stats

def build_adapters(env=os.environ):
    adapters = []
    if env.get("INTAKE_MAIL_CMD") and env.get("INTAKE_MAIL_ENABLED") == "1":
        adapters.append(MailAdapter(command_fetcher(shlex.split(env["INTAKE_MAIL_CMD"])), env.get("INTAKE_MAIL_ALLOW", "").split(",")))
    if env.get("INTAKE_DISCORD_CMD"):
        adapters.append(DiscordAdapter(command_fetcher(shlex.split(env["INTAKE_DISCORD_CMD"])), env.get("INTAKE_DISCORD_ALLOW", "").split(",")))
    return adapters

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    env = os.environ
    db = writer.open_db(env["INTAKE_DB"])
    spool = Spool(env["INTAKE_SPOOL"])
    adapters = build_adapters(env)
    if "--once" in argv:
        print(json.dumps(run_once(db, spool, adapters)))
        return 0
    delay = POLL_SECONDS
    while True:
        try:
            run_once(db, spool, adapters)
            delay = POLL_SECONDS
        except Exception as exc:  # backoff, keep the daemon alive
            print("intake error: " + type(exc).__name__, file=sys.stderr)
            delay = min(delay * 2, MAX_BACKOFF)
        time.sleep(delay)

if __name__ == "__main__":
    sys.exit(main())
