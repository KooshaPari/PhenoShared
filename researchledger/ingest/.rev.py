import json, subprocess, sys
for n in (976, 977):
    print("=== PR #%d reviews ===" % n)
    r = subprocess.run(["gh","api","repos/KooshaPari/ShareCLI/pulls/%d/reviews?per_page=100" % n],
                       capture_output=True, text=True)
    try: d = json.loads(r.stdout)
    except Exception:
        print("  parse fail"); continue
    if not d: print("  none"); continue
    # keep latest review per user
    latest = {}
    for x in d:
        u = (x.get("user") or {}).get("login","?")
        t = x.get("submitted_at") or ""
        if u not in latest or t > (latest[u].get("submitted_at") or ""):
            latest[u] = x
    for u, x in sorted(latest.items(), key=lambda kv: kv[1].get("submitted_at") or ""):
        print("  %-34s %-18s %s" % (u, x.get("state"), (x.get("submitted_at") or "")[:19]))
    # what does GitHub consider the decision
    pr = subprocess.run(["gh","pr","view",str(n),"--json","reviewDecision"],capture_output=True,text=True)
    try: print("  reviewDecision =", json.loads(pr.stdout).get("reviewDecision"))
    except Exception: pass
