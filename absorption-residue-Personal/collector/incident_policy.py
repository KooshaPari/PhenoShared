"""Pure incident-opening policy. Polls are not collector runs; absence never closes."""
from datetime import date, datetime, timedelta, timezone

STALE_HOURS = 36
SCHEME = "la-day-v1"


def timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return result.astimezone(timezone.utc) if result.tzinfo else None


def normalize(row, now):
    if not isinstance(row, dict):
        return None
    day = row.get("day")
    try:
        if date.fromisoformat(day).isoformat() != day:
            return None
    except (TypeError, ValueError):
        return None
    ok, good, bad = (row.get(key) for key in ("ok", "boards_ok", "boards_failed"))
    finished = timestamp(row.get("finished_at"))
    if (type(ok) is not int or ok not in (0, 1)
            or any(type(n) is not int or n < 0 for n in (good, bad))
            or finished is None or finished > now
            or (ok == 1 and (good == 0 or bad != 0))):
        return None
    empty = good + bad == 0
    if empty and row.get("error") != "no active boards":
        return None
    return {"day": day, "ok": ok, "boards_ok": good, "boards_failed": bad,
            "finished_at": finished.isoformat(),
            "error": "no active boards" if empty else None}


def evaluate(health, previous, now, *, target):
    """Return an opening decision and a bounded checkpoint for the next runner.

    New Workers supply the two newest finalized rows, newest first. Older Workers
    supply one latest row: only adjacent LA days prove a consecutive pair there.
    Malformed rows break a streak, and never refresh the last trusted clock.
    """
    prior = previous.get("incident_checkpoint") if isinstance(previous, dict) else None
    if isinstance(previous, dict) and "incident" in previous and prior is None:
        raise ValueError("incident checkpoint missing from a policy report")
    if prior is not None and (not isinstance(prior, dict) or prior.get("version") != 1
                              or prior.get("target") != target or prior.get("run_identity_scheme") != SCHEME):
        raise ValueError("incident checkpoint version/target mismatch")
    prior = prior or {}
    first = timestamp(prior.get("first_observed_at"))
    if prior and (first is None or first > now):
        raise ValueError("incident checkpoint first observation is invalid")
    if first is None and isinstance(previous, dict):
        first = timestamp(previous.get("checked_at"))  # Legacy artifact migration.
    if first is None or first > now:
        first = now
    anchor = timestamp(prior.get("last_finalized_at"))
    if anchor and anchor > now:
        raise ValueError("incident checkpoint completion clock is in the future")
    cached = prior.get("runs", [])
    if not isinstance(cached, list) or len(cached) > 2:
        raise ValueError("incident checkpoint run history is invalid")
    cached_rows = [normalize(row, now) for row in cached]
    if any(row is None for row in cached_rows):
        raise ValueError("incident checkpoint contains an invalid finalized run")
    conflict_ids = prior.get("conflicts", [])
    if not isinstance(conflict_ids, list) or len(conflict_ids) > 2 or any(not isinstance(day, str) for day in conflict_ids):
        raise ValueError("incident checkpoint conflicts are invalid")
    conflicts = set(conflict_ids)
    diagnostics = []
    complete = "finalized_runs" in health
    scheme = health.get("run_identity_scheme", SCHEME if not complete else None)
    raw = health.get("finalized_runs") if complete else [health.get("latest_run")]
    if (health.get("service") != "job-collector" or scheme != SCHEME
            or not isinstance(raw, list) or len(raw) > 2):
        raw = []
        diagnostics.append("finalized-run identity/history contract unavailable")
    if not raw or raw == [None]:
        diagnostics.append("no finalized collector run available")
    # A legacy error placeholder is not a run and cannot displace cached evidence.
    if not complete and raw and isinstance(raw[0], dict) and raw[0].get("boards_ok") is None:
        raw = []
        diagnostics.append("latest attempt is not finalized")
    known = {row["day"]: row for row in cached_rows}
    rows = []
    seen = set()
    for item in raw:
        row = normalize(item, now)
        if row is None:
            diagnostics.append("unknown or inconsistent finalized-run data")
            rows.append(None)  # Do not join two failures across an unknown run.
            continue
        day = row["day"]
        older = known.get(day)
        if older:
            if any(row[key] != older[key] for key in ("ok", "boards_ok", "boards_failed", "error")):
                conflicts.add(day)
            # A revision/heartbeat for the same immutable ID is not new freshness.
            row["finished_at"] = min(row["finished_at"], older["finished_at"])
        known[day] = row
        if day in conflicts:
            diagnostics.append("conflicting finalized-run revisions: " + day)
            rows.append(None)
        elif day not in seen:
            rows.append(row)
        seen.add(day)
    rows = [None if row and row["day"] in conflicts else row for row in rows]
    ordered = [row["day"] for row in rows if row]
    if ordered != sorted(ordered, reverse=True):
        diagnostics.append("finalized-run history is not newest first")
        rows = [None]
    # A regressed feed cannot turn an earlier failure into the latest run.
    if ordered and cached_rows and max(ordered) < max(row["day"] for row in cached_rows):
        diagnostics.append("finalized-run history regressed")
        rows = [None]
    if not complete and rows and rows[0]:
        latest_day = rows[0]["day"]
        older = [row for row in cached_rows if row["day"] < latest_day and row["day"] not in conflicts]
        if older:
            prior_row = max(older, key=lambda row: row["day"])
            if date.fromisoformat(latest_day) - date.fromisoformat(prior_row["day"]) == timedelta(days=1):
                rows.append(prior_row)
            else:
                diagnostics.append("legacy history gap; consecutive runs unproven")
    # Missing legacy telemetry may use the last trusted observation for staleness,
    # but does not re-count that observation as a newly finalized run.
    trusted = [row for row in rows if row]
    if trusted:
        latest_trusted = max(trusted, key=lambda row: row["day"])
        completed = timestamp(latest_trusted["finished_at"])
        latest_cached = max(cached_rows, key=lambda row: row["day"]) if cached_rows else None
        if latest_cached is None or latest_trusted["day"] > latest_cached["day"]:
            anchor = completed
        elif latest_trusted["day"] == latest_cached["day"]:
            anchor = min(anchor, completed) if anchor else completed
    age = (now - (anchor or first)).total_seconds() / 3600
    stale = age > STALE_HOURS
    streak = 0
    for row in rows:
        if not row or row["ok"] != 0:
            break
        streak += 1
    latest = rows[0] if rows and rows[0] else None
    checked = latest["boards_ok"] + latest["boards_failed"] if latest else None
    excessive = bool(latest and checked and 10 * latest["boards_failed"] > checked)
    if checked == 0:
        diagnostics.append("no active boards; failure percentage undefined")
    reasons = [reason for reason, applies in (
        ("two distinct consecutive degraded finalized runs", streak >= 2),
        ("failed checked boards strictly above 10%", excessive),
        ("latest finalized run stale beyond 36 hours" if anchor else
         "no trusted finalized run for more than 36 hours", stale),
    ) if applies]
    kept = sorted(known.values(), key=lambda row: row["day"], reverse=True)[:2]
    checkpoint = {"version": 1, "target": target, "run_identity_scheme": SCHEME,
                  "first_observed_at": first.isoformat(),
                  "last_finalized_at": anchor.isoformat() if anchor else None,
                  "runs": kept, "conflicts": sorted(conflicts.intersection(row["day"] for row in kept))}
    return {"should_open_or_reopen": bool(reasons), "reasons": reasons,
            "consecutive_degraded": streak, "latest_run_id": SCHEME + ":" + latest["day"] if latest else None,
            "boards_checked": checked, "boards_failed": latest["boards_failed"] if latest else None,
            "finalized_age_hours": age if anchor else None, "stale_after_hours": STALE_HOURS,
            "data_issues": list(dict.fromkeys(diagnostics)), "close_existing_incident": False}, checkpoint
