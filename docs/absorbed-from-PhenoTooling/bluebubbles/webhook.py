"""BlueBubbles webhook receiver.

Listens for inbound iMessage events (messages, tapbacks, stickers, reactions)
from a local BlueBubbles Server and appends each event as a JSONL record to
`~/.phenotype/imessage-inbound.jsonl` for agent consumption.

Run:
    python3 webhook.py               # binds 127.0.0.1:8787
    BB_WEBHOOK_HOST=0.0.0.0 BB_WEBHOOK_PORT=8787 python3 webhook.py

Configure BlueBubbles Server -> Settings -> Webhooks:
    URL: http://<host>:<port>/bluebubbles

Wraps: aiohttp 3.x (stdlib HTTP would also work; aiohttp chosen for async
parity with the rest of the phenotype tooling).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from aiohttp import web

INBOUND_PATH = Path(os.path.expanduser("~/.phenotype/imessage-inbound.jsonl"))
INBOUND_PATH.parent.mkdir(parents=True, exist_ok=True)


async def handle(request: web.Request) -> web.Response:
    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        return web.json_response({"error": f"invalid json: {exc}"}, status=400)

    record = {
        "received_at": datetime.now(timezone.utc).isoformat(),
        "type": payload.get("type"),
        "data": payload.get("data", payload),
    }
    with INBOUND_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"[{record['received_at']}] {record['type']}", file=sys.stderr)
    return web.json_response({"ok": True})


async def health(_: web.Request) -> web.Response:
    return web.json_response({"ok": True, "sink": str(INBOUND_PATH)})


def main() -> None:
    app = web.Application()
    app.router.add_post("/bluebubbles", handle)
    app.router.add_post("/", handle)
    app.router.add_get("/health", health)
    host = os.environ.get("BB_WEBHOOK_HOST", "127.0.0.1")
    port = int(os.environ.get("BB_WEBHOOK_PORT", "8787"))
    print(f"bluebubbles-webhook listening on {host}:{port}, sink={INBOUND_PATH}", file=sys.stderr)
    web.run_app(app, host=host, port=port)


if __name__ == "__main__":
    main()
