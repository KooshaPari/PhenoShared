"""Source adapters. Each yields Message objects from an injected fetcher.

A fetcher is a callable returning an iterable of dicts:
  {"id": str, "sender": str, "body": str}
The real fetchers live in the deployment (a command that prints JSON lines);
adapters never open the network themselves, so tests and the writer stay
offline and hold no secrets.
"""
import json, subprocess
from dataclasses import dataclass

@dataclass(frozen=True)
class Message:
    source: str
    message_id: str
    sender: str
    body: str

class Adapter:
    source = "unknown"
    def __init__(self, fetch, allowed_senders):
        self.fetch = fetch
        self.allowed = frozenset(s.strip().lower() for s in allowed_senders if s and s.strip())
    def messages(self):
        for raw in self.fetch():
            if not isinstance(raw, dict):
                continue
            mid, sender, body = raw.get("id"), raw.get("sender"), raw.get("body")
            if not isinstance(mid, str) or not mid or not isinstance(sender, str):
                continue
            yield Message(self.source, mid[:200], sender[:200], body if isinstance(body, str) else "")
    def is_allowed(self, msg):
        return msg.sender.strip().lower() in self.allowed

class MailAdapter(Adapter):
    """Dot mail line. Sender = the Dot mail identity (From address)."""
    source = "mail"

class DiscordAdapter(Adapter):
    """Discord wake. Sender = '<channel_id>:<author_id>' - both must be allowlisted
    as one entry, so another author in the right channel is quarantined."""
    source = "discord"

def command_fetcher(argv, timeout=60):
    """Run a configured command that prints one JSON object per line."""
    def fetch():
        out = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=True).stdout
        for line in out.splitlines():
            try:
                yield json.loads(line)
            except ValueError:
                continue
    return fetch
