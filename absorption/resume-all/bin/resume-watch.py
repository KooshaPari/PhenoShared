#!/usr/bin/env python3
"""resume-watch — auto-restore daemon (E04). Polls snapshot.jsonl every 10s
and on harness-PID death fires `trigger` + `notify` through the IPC daemon.
"""
import json, os, socket, struct, subprocess, sys, time, logging
from pathlib import Path

SNAPSHOT = Path.home() / '.local/share/resume-all/snapshot.jsonl'
IPC = Path.home() / 'Library/Application Support/sharecli/ipc.sock'
LOG = Path.home() / '.local/share/resume-all/watch.log'
INTERVAL = 10

logging.basicConfig(filename=str(LOG), level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

def rpc(method, params=None):
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect(str(IPC))
        req = {'jsonrpc': '2.0', 'method': method, 'params': params or {}, 'id': int(time.time())}
        data = json.dumps(req).encode()
        s.sendall(struct.pack('>I', len(data)) + data)
        lb = s.recv(4); rl = struct.unpack('>I', lb)[0]; rd = s.recv(rl)
        s.close()
        return json.loads(rd)
    except Exception as e:
        logging.error(f"IPC {method} failed: {e}")
        return {}

def alive(pid):
    try: os.kill(pid, 0); return True
    except OSError: return False

def restore(harness, sid, cwd):
    logging.info(f"RESTORE {harness} sid={(sid or '')[:16]} cwd={(cwd or '/')[:40]}")
    rpc('trigger', {'harness': harness, 'session_id': sid, 'cwd': cwd})
    rpc('notify', {'harness': harness, 'session_id': sid, 'cwd': cwd})

def main():
    logging.info("resume-watch started")
    last = {}
    while True:
        try:
            text = SNAPSHOT.read_text()
        except Exception as e:
            logging.error(f"read snapshot: {e}")
            time.sleep(INTERVAL); continue

        for line in text.strip().splitlines():
            if not line.strip(): continue
            try: row = json.loads(line)
            except json.JSONDecodeError: continue
            if row.get('dead'): continue
            h = row.get('harness', '')
            if h in ('shell', 'unknown', ''): continue
            pid = row.get('pid')
            sid = row.get('session_id', '') or ''
            cwd = row.get('cwd', '') or '/'
            if not pid: continue
            key = f"{h}:{pid}"
            is_alive = alive(pid)
            if not is_alive and last.get(key, True):
                logging.warning(f"DEAD {h} pid={pid} — auto-restoring")
                restore(h, sid, cwd)
            last[key] = is_alive

        # Clean stale keys
        seen = {f"{r.get('harness','')}:{r.get('pid','')}"
                for line in text.strip().splitlines() if line.strip()
                for r in [json.loads(line)]
                if not r.get('dead') and r.get('harness','') not in ('shell','unknown','')}
        for k in list(last.keys()):
            if k not in seen: del last[k]

        time.sleep(INTERVAL)

if __name__ == '__main__':
    main()
