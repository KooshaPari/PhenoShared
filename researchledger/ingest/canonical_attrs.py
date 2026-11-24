"""Single source of truth for canonical-attribute conversion helpers.

Four builders (jcode, kcode, codex, cursor) used to each carry a private copy
of the same migrator TEXT -> JSON-array conversion. A single defect (tool-name
values serialized as JSON strings instead of JSON arrays) appeared
simultaneously in all four, because each one was its own copy. This module is
the consolidation point.

The function is intentionally generic over the field name; it operates on the
JSON-vs-CSV boundary, not on a specific table column. The four builders all
call into it.
"""

from __future__ import annotations

import json


def _tool_names_to_array(value):
    """Convert the migrator's comma-separated TEXT into a real JSON array.

    The migrators populate migrated_*_messages.tool_use_names (and
    migrated_cursor_messages.tool_call_names) as TEXT columns with values like
    'bash,bash,read' or '' or None or '?'. attrs_json.tool_use_names must be a
    JSON array so json_each() works, so we convert at the boundary.

    Behaviour matrix (covered by tests/test_canonical_attrs_12case.py):

        None                       -> None
        ''                         -> []
        '   '                      -> []
        '?'                        -> []
        'bash'                     -> ['bash']
        'bash,bash,read'           -> ['bash', 'bash', 'read']
        ' bash , bash ,read '      -> ['bash', 'bash', 'read']   (trim ws)
        ['bash', 'read']           -> ['bash', 'read']            (pass-through)
        '["bash","read"]'          -> ['bash', 'read']            (parse JSON)
        '["bash", "read"]'         -> ['bash', 'read']            (parse JSON)
        '[1,2]'                    -> ['[1', '2]']                (fall through)
        'not-json['                -> ['not-json[']               (fall through)

    Returns None when value is None (preserves "no data" semantics), [] when
    the input is empty or '?', and a list of trimmed strings otherwise. If a
    future migrator ever stores a real list, it passes through unchanged.
    """
    if value is None:
        return None
    if isinstance(value, list):
        return value
    s = value.strip() if isinstance(value, str) else ""
    if not s or s == "?":
        return []
    if s.startswith("["):
        try:
            parsed = json.loads(s)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
            return [x.strip() for x in parsed if x.strip()]
    return [p.strip() for p in s.split(",") if p.strip()]