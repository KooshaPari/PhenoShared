import json, re
seen = set()
with open('clippy.json', 'r', encoding='utf-8', errors='replace') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get('reason') != 'compiler-message':
            continue
        m = d.get('message', {})
        lvl = m.get('level', '')
        rendered = m.get('rendered', '') or ''
        # strip ANSI
        rendered = re.sub(r'\x1b\[[0-9;]*m', '', rendered)
        spans = m.get('spans', [])
        loc = ''
        if spans:
            sp = spans[0]
            loc = f"{sp.get('file_name','')}:{sp.get('line_start','')}:{sp.get('column_start','')}"
        code = m.get('code', {}) or {}
        code_id = code.get('code', '')
        # dedupe by (code, loc, first line of message)
        head = rendered.splitlines()[0:3]
        key = (code_id, loc, tuple(head))
        if key in seen:
            continue
        seen.add(key)
        print(f"--- {lvl} {code_id} @ {loc}")
        print(rendered)
        print()
