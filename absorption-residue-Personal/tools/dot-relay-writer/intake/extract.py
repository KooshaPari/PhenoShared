"""Extract candidate records from untrusted message bodies.

Only fenced ```json blocks are read. Every other character of the body is
dropped and never executed, interpreted or logged. Blocks are size-capped and
must parse to a JSON object.
"""
import json, re

FENCE_RE = re.compile(r"```json[ \t]*\r?\n(.*?)\r?\n[ \t]*```", re.S | re.I)
MAX_BLOCK_BYTES = 16 * 1024
MAX_BLOCKS = 5

def extract_records(body):
    """Return (records, malformed_count). Never raises on hostile input."""
    if not isinstance(body, str):
        return [], 0
    records, malformed = [], 0
    for i, m in enumerate(FENCE_RE.finditer(body)):
        if i >= MAX_BLOCKS:
            malformed += 1
            break
        raw = m.group(1)
        if len(raw.encode("utf-8", "ignore")) > MAX_BLOCK_BYTES:
            malformed += 1
            continue
        try:
            obj = json.loads(raw)
        except (ValueError, RecursionError):
            malformed += 1
            continue
        if isinstance(obj, dict):
            records.append(obj)
        else:
            malformed += 1
    return records, malformed
