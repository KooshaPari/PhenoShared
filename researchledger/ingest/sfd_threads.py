#!/usr/bin/env python3
"""Reply to / resolve the remaining PR threads with per-thread evidence."""
import json
import subprocess
import sys

QUERY = ('{repository(owner:"KooshaPari",name:"AgilePlus"){pullRequest(number:%d)'
         '{reviewThreads(first:100){nodes{id isResolved path line '
         'comments(first:1){nodes{author{login}}}}}}}}')
REPLY_Q = ("mutation($t:ID!,$b:String!){addPullRequestReviewThreadReply("
           "input:{pullRequestReviewThreadId:$t,body:$b}){comment{id}}}")
RESOLVE_Q = ("mutation($t:ID!){resolveReviewThread(input:{threadId:$t})"
             "{thread{isResolved}}}")


def _run(args):
    p = subprocess.run(args, capture_output=True, text=True)
    return (p.returncode == 0), (p.stderr.strip() or p.stdout.strip())


def threads(n):
    ok, out = _run(["gh", "api", "graphql", "-f", f"query={QUERY % n}"])
    if not ok:
        raise RuntimeError(out)
    d = json.loads(out)["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
    return [x for x in d if not x["isResolved"]]


def find(n, path_frag, line=None):
    for x in threads(n):
        if path_frag in x["path"] and (line is None or x["line"] == line):
            return x
    return None


def reply(tid, body):
    return _run(["gh", "api", "graphql", "-f", f"query={REPLY_Q}",
                 "-f", f"t={tid}", "-f", f"b={body}"])


def resolve(tid):
    return _run(["gh", "api", "graphql", "-f", f"query={RESOLVE_Q}", "-f", f"t={tid}"])


def do(n, path_frag, line, body, label=""):
    t = find(n, path_frag, line)
    if not t:
        print(f"SKIP #{n} {path_frag}:{line}")
        return
    ok, err = reply(t["id"], body)
    print(f"reply  #{n} {path_frag}:{line} {label} -> {'OK' if ok else 'FAIL ' + err[:90]}")
    ok, err = resolve(t["id"])
    print(f"resolve #{n} {path_frag}:{line} -> {'OK' if ok else 'FAIL ' + err[:90]}")
