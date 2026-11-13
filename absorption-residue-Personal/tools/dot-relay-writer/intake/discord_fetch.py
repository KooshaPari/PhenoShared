#!/usr/bin/env python3
"""Read-only Discord fetcher: prints JSON lines {"id","sender","body"}.

GET only (no send, no reactions). Token comes from the environment of this
process (injected by `infisical run`), never from a file. sender is
"<channel_id>:<author_id>"; the poller does the allowlisting. A cursor file
keeps the last message id so each message is emitted once.

Env: DISCORD_BOT_TOKEN_HERMES, INTAKE_DISCORD_CHANNEL, INTAKE_DISCORD_CURSOR
"""
import json, os, sys, urllib.request

def main():
    token = os.environ["DISCORD_BOT_TOKEN_HERMES"]
    chan = os.environ["INTAKE_DISCORD_CHANNEL"]
    cur_path = os.environ["INTAKE_DISCORD_CURSOR"]
    after = open(cur_path).read().strip() if os.path.exists(cur_path) else ""
    url = "https://discord.com/api/v10/channels/%s/messages?limit=50" % chan
    if after:
        url += "&after=" + after
    req = urllib.request.Request(url, headers={"Authorization": "Bot " + token, "User-Agent": "dot-intake (read-only)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        msgs = json.load(r)
    msgs.sort(key=lambda m: int(m["id"]))
    for m in msgs:
        print(json.dumps({"id": m["id"], "sender": "%s:%s" % (chan, m["author"]["id"]), "body": m.get("content", "")}))
    if msgs:
        open(cur_path, "w").write(msgs[-1]["id"])

if __name__ == "__main__":
    main()
