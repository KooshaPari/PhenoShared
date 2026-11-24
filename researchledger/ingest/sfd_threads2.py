#!/usr/bin/env python3
"""Resolve remaining PR threads by matching the first line of each body."""
import json
import subprocess

FULL = ('{repository(owner:"KooshaPari",name:"AgilePlus"){pullRequest(number:%d)'
        '{reviewThreads(first:100){nodes{id isResolved isOutdated path line '
        'comments(first:1){nodes{author{login} body}}}}}}}')
REPLY_Q = ("mutation($t:ID!,$b:String!){addPullRequestReviewThreadReply("
           "input:{pullRequestReviewThreadId:$t,body:$b}){comment{id}}}")
RESOLVE_Q = ("mutation($t:ID!){resolveReviewThread(input:{threadId:$t})"
             "{thread{isResolved}}}")


def _run(args):
    p = subprocess.run(args, capture_output=True, text=True)
    return (p.returncode == 0), (p.stderr.strip() or p.stdout.strip())


def load(pr):
    ok, out = _run(["gh", "api", "graphql", "-f", f"query={FULL % pr}"])
    d = json.loads(out)["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
    return [x for x in d if not x["isResolved"]]


def head(t, n=400):
    b = (t["comments"]["nodes"] or [{}])[0].get("body", "")
    import re
    b = re.sub(r"<[^>]+>", " ", b)
    b = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", b)
    b = re.sub(r"\s+", " ", b).strip()
    return b[:n]


def match(pr, needle, body):
    for t in load(pr):
        raw = (t["comments"]["nodes"] or [{}])[0].get("body", "")
        import re as _re
        flat = _re.sub(r"\s+", " ", _re.sub(r"!\[[^\]]*\]\([^)]*\)", " ",
                                            _re.sub(r"<[^>]+>", " ", raw))).strip()
        if needle in flat:
            ok, err = _run(["gh", "api", "graphql", "-f", f"query={REPLY_Q}",
                            "-f", f"t={t['id']}", "-f", f"b={body}"])
            print(f"  reply   -> {'OK' if ok else 'FAIL ' + err[:80]}")
            ok, err = _run(["gh", "api", "graphql", "-f", f"query={RESOLVE_Q}",
                            "-f", f"t={t['id']}"])
            print(f"  resolve -> {'OK' if ok else 'FAIL ' + err[:80]}")
            return True
    print(f"  NO MATCH for {needle!r}")
    return False
