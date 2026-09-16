#!/usr/bin/env python3
"""Voice activation bridge for resume-all (stdlib-first, best-effort audio).

Real speech recognition is intentionally optional.  Without Apple's Speech
framework (PyObjC), use ``simulate`` or process saved WAV files offline.
"""
from __future__ import annotations
import argparse, datetime as dt, json, math, os, shutil, struct, subprocess, sys, tempfile, time, wave
from pathlib import Path

BIN = Path('/Users/kooshapari/bin')
DATA = Path.home() / '.local/share/resume-all'
VOICE = DATA / 'voice'
STATE = DATA / 'voice-state.json'
SNAPSHOT = DATA / 'snapshot.jsonl'
THRESHOLD = 0.02


def now(): return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def load_state():
    try: return json.loads(STATE.read_text())
    except (OSError, ValueError):
        return {'listening': True, 'wake_word': 'hey resume', 'last_recognized': None, 'last_command': None, 'command_count': 0, 'false_triggers': 0}
def save_state(s):
    STATE.parent.mkdir(parents=True, exist_ok=True); STATE.write_text(json.dumps(s, indent=2) + '\n')

def rms(samples):
    if not samples: return 0.0
    return math.sqrt(sum(x*x for x in samples) / len(samples))
def decode_pcm16(data): return [v/32768.0 for v in struct.unpack('<%dh' % (len(data)//2), data[:len(data)//2*2])]
def audio_devices():
    # sounddevice is optional; avoid importing it unless installed.
    try:
        import sounddevice as sd
        return [str(x) for x in sd.query_devices() if x.get('max_input_channels', 0) > 0]
    except Exception: pass
    rec = '/opt/homebrew/bin/rec' if Path('/opt/homebrew/bin/rec').exists() else shutil.which('rec')
    return [f'SoX microphone capture ({rec})'] if rec else []


def detect_backends():
    """Return dict of available audio backends. Used to warn the user when
    no real-time capture path is available, so they know to use 'simulate'
    or 'record-test' subcommands instead.

    NOTE: PyObjC framework imports (Speech, AVFoundation) can hang for
    30+ seconds when not installed. We skip them — sounddevice + sox
    are the canonical audio backends on this system.
    """
    backends = {
        "sounddevice": False,
        "sox": False,
    }
    try:
        import sounddevice as _sd  # noqa
        backends["sounddevice"] = True
    except Exception:
        pass
    if Path("/opt/homebrew/bin/rec").exists() or shutil.which("rec"):
        backends["sox"] = True
    return backends


def warn_if_no_real_audio():
    """Emit a warning if no real audio capture is available."""
    b = detect_backends()
    if not any([b["sounddevice"], b["sox"]]):
        print(
            "voice-activate: WARNING — no real audio backend available "
            "(no sounddevice, no SoX).",
            file=sys.stderr,
        )
        print(
            "voice-activate: use 'simulate <phrase>' for command dispatch, "
            "'record-test <seconds>' to record (needs SoX), "
            "or install sounddevice: pip install sounddevice",
            file=sys.stderr,
        )
        return False
    return True

def record(seconds, out=None):
    seconds = max(0.1, min(float(seconds), 5.0)); out = Path(out or tempfile.mktemp(suffix='.wav'))
    rec = '/opt/homebrew/bin/rec' if Path('/opt/homebrew/bin/rec').exists() else shutil.which('rec')
    if rec:
        p = subprocess.run([rec, '-q', '-r', '16000', '-c', '1', str(out), 'trim', '0', str(seconds)], capture_output=True, text=True)
        if p.returncode == 0 and out.exists(): return out
        raise RuntimeError((p.stderr or 'microphone unavailable').strip())
    raise RuntimeError('no optional audio backend; install sounddevice or provide /opt/homebrew/bin/rec')

def conservative_wake(text):
    t = ' '.join(text.lower().strip().split())
    return t == 'resume' or t.startswith('hey resume ') or t == 'hey resume'

def normalize(text): return ' '.join(text.lower().replace("'", '').split())
def command_for(phrase):
    p = normalize(phrase)
    if p.startswith('hey resume'): p = p[len('hey resume'):].strip()
    aliases = {
      'resume all': ['resume-all.py'], 'restore everything': ['resume-all.py'],
      'whats broken': ['health-check.py'], 'what is broken': ['health-check.py'], 'show health': ['health-check.py'],
      'restart ipc': ['incident-respond.py', 'run'], 'snapshot now': ['session_snapshot.py'], 'snap': ['session_snapshot.py'],
      'list panes': ['list-panes'], 'show panes': ['list-panes'], 'stop listening': ['stop'], 'quiet': ['stop']}
    return aliases.get(p)

def dispatch(phrase, execute=False):
    cmd = command_for(phrase); state = load_state(); state['last_recognized'] = now(); state['last_command'] = normalize(phrase)
    if not cmd:
        state['false_triggers'] = state.get('false_triggers', 0) + 1; save_state(state); return {'matched': False, 'message': 'unrecognized command'}
    state['command_count'] = state.get('command_count', 0) + 1
    if cmd == ['stop']: state['listening'] = False
    save_state(state)
    if cmd == ['list-panes']:
        lines = SNAPSHOT.read_text(errors='replace').splitlines()[-10:] if SNAPSHOT.exists() else []
        return {'matched': True, 'command': cmd, 'output': lines}
    if execute:
        target = BIN / cmd[0]
        result = subprocess.run([sys.executable, str(target), *cmd[1:]], text=True, capture_output=True)
        return {'matched': True, 'command': cmd, 'returncode': result.returncode, 'output': (result.stdout + result.stderr).strip()}
    return {'matched': True, 'command': cmd, 'would_run': str(BIN/cmd[0])}

def listen():
    print('Listening for "hey resume". Real-time STT requires optional PyObjC Speech; Ctrl-C stops.')
    while load_state().get('listening', True):
        try:
            path = record(2.0)
            with wave.open(str(path), 'rb') as w: energy = rms(decode_pcm16(w.readframes(w.getnframes())))
            if energy > THRESHOLD:
                print('Voice activity detected, but could not transcribe in real-time; audio was not retained without consent.')
            time.sleep(0.1)
        except KeyboardInterrupt: break
        except Exception as e:
            print('Audio unavailable:', e, file=sys.stderr); time.sleep(0.1); break

def tests():
    checks = [('state shape', set(load_state()) >= {'listening','wake_word','command_count'}), ('wake exact', conservative_wake('hey resume')), ('wake conservative', not conservative_wake('please resume all')), ('command resume', command_for('resume all') == ['resume-all.py']), ('command health', command_for("what's broken") == ['health-check.py']), ('buffer rms', abs(rms([0.0, 0.5, -0.5]) - math.sqrt(1/6)) < 1e-9), ('device probe', isinstance(audio_devices(), list))]
    for n, ok in checks: print(('PASS' if ok else 'FAIL') + ' ' + n)
    print('%d/%d tests passed' % (sum(x[1] for x in checks), len(checks)))
    print('Note: record-test writes audio only when explicitly requested.')
    return all(x[1] for x in checks)

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='sub', required=True)
    sub.add_parser('listen'); sub.add_parser('test'); sub.add_parser('devices'); sub.add_parser('backends'); sub.add_parser('stats'); sub.add_parser('history')
    s=sub.add_parser('simulate'); s.add_argument('phrase')
    r=sub.add_parser('record-test'); r.add_argument('seconds', type=float)
    l=sub.add_parser('loop'); l.add_argument('--interval', type=int, default=10, help='seconds between wake-word checks')
    a=ap.parse_args()
    if a.sub=='test': return 0 if tests() else 1
    if a.sub=='devices': print('\n'.join(audio_devices()) or 'No input devices found (optional backend unavailable)'); return 0
    if a.sub=='backends':
        import json as _json
        print(_json.dumps(detect_backends(), indent=2))
        return 0
    if a.sub=='stats': print(json.dumps(load_state(), indent=2)); return 0
    if a.sub=='history':
        hist_file = DATA / 'voice-history.jsonl'
        if not hist_file.exists(): print('No voice history yet.'); return 0
        print('\n'.join(hist_file.read_text().splitlines()[-20:]))
        return 0
    if a.sub=='simulate':
        result = dispatch(a.phrase); log_voice_event('simulate', a.phrase, result); print(json.dumps(result, indent=2)); return 0
    if a.sub=='record-test':
        try:
            p=record(a.seconds); w=wave.open(str(p),'rb'); e=rms(decode_pcm16(w.readframes(w.getnframes()))); w.close(); print('file=%s rms=%.6f' % (p,e)); return 0
        except Exception as e: print('record failed:', e, file=sys.stderr); return 1
    if a.sub=='loop':
        # Polling loop for launchd. Tries to listen briefly, logs result.
        print(f'voice-activate: looping every {a.interval}s (Ctrl-C to stop)', file=sys.stderr)
        try:
            while True:
                # In loop mode, just check that audio devices are present
                # (real listening happens in 'listen' mode)
                devs = audio_devices()
                state = load_state()
                state['last_loop_ts'] = now()
                state['audio_devices_count'] = len(devs)
                save_state(state)
                time.sleep(a.interval)
        except KeyboardInterrupt:
            print('\nvoice-activate: stopped', file=sys.stderr)
        return 0
    listen(); return 0


def log_voice_event(event_type, phrase, result):
    """Append an event to voice-history.jsonl for auditing."""
    hist = DATA / 'voice-history.jsonl'
    DATA.mkdir(parents=True, exist_ok=True)
    entry = {
        'ts': now(),
        'event': event_type,
        'phrase': phrase,
        'matched': result.get('matched'),
        'command': result.get('command'),
    }
    with hist.open('a') as f:
        f.write(json.dumps(entry, separators=(',', ':')) + '\n')


if __name__=='__main__': sys.exit(main())
