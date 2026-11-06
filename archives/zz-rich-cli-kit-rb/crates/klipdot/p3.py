import json
seen = set()
for line in open('clippy.json', 'rb').read().decode('utf-8', errors='replace').splitlines():
    line = line.strip()
    if not line:
        continue
    try:
        d = json.loads(line)
    except Exception:
        continue
    r = d.get('reason', '?')
    if r not in seen:
        seen.add(r)
        print('REASON:', r)
    if len(seen) > 30:
        break
