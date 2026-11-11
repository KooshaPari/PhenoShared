#!/usr/bin/env python3
"""Goal 2 addendum (LOCAL): F6 device/login elaboration.

Clusters the 73 login events by device signature + network, and correlates each
cluster with Claude chat activity (message timestamps within +/-3h of logins).
Output: goal2/F6-devices.md (full IPs included on purpose — Koosha needs them to
identify his own devices; file stays local).
"""
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone

RAW = "/Users/kooshapari/Exports/claude-20261010/raw"
OUT = "/Users/kooshapari/Exports/analysis/goal2/F6-devices.md"
DELTA = timedelta(hours=3)


def net(ip):
    if ":" in ip:  # ipv6 -> /32-ish (first 2 hextets)
        return ":".join(ip.split(":")[:2]) + ":…"
    parts = ip.split(".")
    return ".".join(parts[:2]) + ".x.x"


def parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def main():
    ev = json.load(open(os.path.join(RAW, "light_metadata-000", "login_history.json")))["login_events"]
    ev.sort(key=lambda e: e["timestamp"])

    # message activity windows
    msg_ts = []
    with open("/Users/kooshapari/Exports/analysis/goal1/messages.jsonl", encoding="utf-8") as f:
        for line in f:
            m = json.loads(line)
            if m.get("role") == "human" and m.get("created_at"):
                msg_ts.append(parse(m["created_at"]))
    msg_ts.sort()

    clusters = defaultdict(list)
    for e in ev:
        ua = e["user_agent"]
        key = (ua["os_family"], ua["browser_family"], ua["device_family"], net(e["ip_address"]))
        clusters[key].append(e)

    lines = [
        "# F6 — Device/login elaboration (from login_history.json)",
        "",
        f"{len(ev)} login events, all method=google, all country=US, city/region null.",
        "Clusters = same OS + browser + device family + network prefix. 'chat overlap' = human-message activity within ±3h of a login in that cluster (circumstantial, not proof of identity).",
        "Full IPs included deliberately — this file is for you to match against your own devices/networks; keep it local.",
        "",
    ]
    order = sorted(clusters.items(), key=lambda kv: -len(kv[1]))
    for (osf, brw, dev, nw), evs in order:
        first, last = evs[0]["timestamp"][:10], evs[-1]["timestamp"][:10]
        ips = sorted({e["ip_address"] for e in evs})
        overlap = 0
        for e in evs:
            t = parse(e["timestamp"])
            lo, hi = t - DELTA, t + DELTA
            # binary search overlap
            import bisect
            i = bisect.bisect_left(msg_ts, lo)
            if i < len(msg_ts) and msg_ts[i] <= hi:
                overlap += 1
        lines += [
            f"## {osf} / {brw} / {dev} — {len(evs)} logins ({first} → {last})",
            f"- networks: {', '.join(sorted({net(i) for i in ips}))}",
            f"- full IPs: {', '.join(ips)}",
            f"- browser/OS versions: {sorted({e['user_agent']['browser_version'] or '?' for e in evs})} on {sorted({str(e['user_agent']['os_version']) for e in evs})}",
            f"- logins with overlapping chat activity: {overlap}/{len(evs)}",
            f"- timestamps: {', '.join(e['timestamp'][:16] for e in evs[:12])}{' …' if len(evs) > 12 else ''}",
            "",
        ]

    lines += [
        "## How to use this",
        "- Match each cluster to a device you own (home Mac, work Windows box, iPhone, family members' devices, VMs/sandboxes, school lab machines).",
        "- The recurring `2603:8001:…` Windows/Edge cluster spanning 2024-04→2026-08 looks like ONE persistent machine, not random compromise.",
        "- Anything you cannot place → check Google account activity (myaccount.google.com → Security → Your devices) and Anthropic settings → connected apps/sessions; revoke there.",
        "- Timestamps are UTC.",
    ]
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(json.dumps({"clusters": len(clusters), "events": len(ev),
                      "cluster_sizes": [len(e) for _, e in order]}))


if __name__ == "__main__":
    main()
