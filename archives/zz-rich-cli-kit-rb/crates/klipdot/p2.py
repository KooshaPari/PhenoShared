import json, re, sys
n = 0
with open('clippy.json', 'rb') as f:
    data = f.read().decode('utf-8', errors='replace')
for line in data.splitlines():
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
    rendered = re.sub(r'\x1b\[[0-9;]*m', '', m.get('rendered', '') or '')
    spans = m.get('spans', [])
    loc = ''
    if spans:
        sp = spans[0]
        loc = sp.get('file_name', '') + ':' + str(sp.get('line_start', '')) + ':' + str(sp.get('column_start', ''))
    code = m.get('code', {}) or {}
    code_id = code.get('code', '')
    sys.stdout.write('--- ' + lvl + ' ' + code_id + ' @ ' + loc + '\n')
    sys.stdout.write(rendered + '\n\n')
    n += 1
sys.stdout.write('TOTAL=' + str(n) + '\n')
