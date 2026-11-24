#!/opt/homebrew/bin/python3
"""
flag.py — Phase F hardening item F13.

Feature flag system for the resume-all crash-recovery toolkit.

Resolution priority (first wins):
  1. Env var RESUME_ALL_FLAG_<UPPER_SNAKE_NAME>
  2. ~/.config/resume-all/flags.toml
  3. Hardcoded defaults below

Usage:
    flag.py list
    flag.py get <name>
    flag.py set <name> <value>
    flag.py unset <name>
    flag.py defaults
    flag.py watch --interval 5
    flag.py snapshot <name> <reason>
    flag.py history <name>
    flag.py test
"""
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HOME = Path.home()
CONFIG_DIR = HOME / ".config" / "resume-all"
FLAGS_FILE = CONFIG_DIR / "flags.toml"
SNAPSHOT_DIR = HOME / ".local" / "share" / "resume-all"
HISTORY_FILE = SNAPSHOT_DIR / "flag-history.jsonl"
IPC_SOCKET = HOME / "Library" / "Application Support" / "sharecli" / "ipc.sock"
VALID_NAME = re.compile(r"^[a-z][a-z0-9_]*$")

DEFAULTS: dict = {
    "auto_resume_after_crash": True,
    "ipc_daemon_enabled": True,
    "snapshot_loop_enabled": True,
    "tray_app_enabled": True,
    "mcp_server_enabled": True,
    "leak_detection_enabled": True,
    "sla_monitoring_enabled": True,
    "new_walker_engine": False,
    "strict_mode": False,
    "verbose_logging": False,
    "snapshot_interval_seconds": 30,
    "ipc_socket_timeout_ms": 5000,
    "canary_cohort_size_pct": 5,
}

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_name(name: str) -> str:
    if not VALID_NAME.match(name):
        raise ValueError(
            f"invalid flag name: {name!r}. "
            "Must match [a-z][a-z0-9_]* (no shell metacharacters)."
        )
    return name


# ---------------------------------------------------------------------------
# Resolution chain
# ---------------------------------------------------------------------------


def _toml_load(path: Path) -> dict:
    """Minimal TOML reader for our flat key=value schema."""
    if not path.exists():
        return {}
    data = {}
    section = None
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1].strip()
            if section == "flags":
                section = "flags"
            else:
                # Treat unknown sections as flags prefix
                section = "flags"
            continue
        if "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip inline comments (only if outside quotes)
        if value.startswith('"') or value.startswith("'"):
            end_quote = value[0]
            if value.endswith(end_quote) and len(value) >= 2:
                pass  # closed
            else:
                # Multi-token quoted string — just take as-is
                pass
        elif "#" in value:
            value = value.split("#", 1)[0].strip()

        # Type coercion
        if value == "true":
            data[key] = True
        elif value == "false":
            data[key] = False
        elif value.startswith('"') and value.endswith('"'):
            data[key] = value[1:-1]
        else:
            try:
                data[key] = int(value)
            except ValueError:
                try:
                    data[key] = float(value)
                except ValueError:
                    data[key] = value
    return data


def _toml_dump(path: Path, data: dict) -> str:
    """Write flags dict to a TOML file under [flags] section."""
    lines = ["[flags]"]
    for k, v in sorted(data.items()):
        if isinstance(v, bool):
            lines.append(f"{k} = {str(v).lower()}")
        elif isinstance(v, (int, float)):
            lines.append(f"{k} = {v}")
        elif isinstance(v, str):
            # Escape backslashes and double quotes
            escaped = v.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{k} = "{escaped}"')
        else:
            lines.append(f"{k} = {json.dumps(v)}")
    return "\n".join(lines) + "\n"


def _atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content)
    tmp.rename(path)


def _load_toml() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return _toml_load(FLAGS_FILE)


def _save_toml(data: dict) -> None:
    _atomic_write(FLAGS_FILE, _toml_dump(FLAGS_FILE, data))


def _env_override(name: str):
    env_key = "RESUME_ALL_FLAG_" + name.upper()
    return os.environ.get(env_key)


def resolve(name: str, toml_data: dict | None = None) -> tuple:
    """Return (value, source) where source is 'env' | 'toml' | 'default'."""
    _validate_name(name)
    if toml_data is None:
        toml_data = _load_toml()
    env_val = _env_override(name)
    if env_val is not None:
        coerced = _coerce(env_val)
        return coerced, "env"
    if name in toml_data:
        return toml_data[name], "toml"
    if name in DEFAULTS:
        return DEFAULTS[name], "default"
    raise KeyError(f"unknown flag: {name}")


def _coerce(raw: str):
    """Coerce env-var string to typed value."""
    low = raw.lower()
    if low in ("true", "yes", "1"):
        return True
    if low in ("false", "no", "0"):
        return False
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


def _log_history(name: str, old: object, new: object, reason: str = "") -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.time(),
        "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "flag": name,
        "old": old,
        "new": new,
        "reason": reason,
    }
    with HISTORY_FILE.open("a") as f:
        f.write(json.dumps(entry, separators=(",", ":")) + "\n")


def _read_history(name: str | None = None, limit: int = 50) -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    out = []
    for line in HISTORY_FILE.read_text().splitlines()[-limit:]:
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if name is None or e.get("flag") == name:
            out.append(e)
    return out


# ---------------------------------------------------------------------------
# IPC broadcast
# ---------------------------------------------------------------------------


def _broadcast_change(name: str, value: object) -> None:
    """Send flag.changed to IPC daemon. Best-effort, never raises."""
    if not IPC_SOCKET.exists():
        return
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(str(IPC_SOCKET))
        msg = {
            "id": int(time.time() * 1000) % 1_000_000,
            "method": "flag.changed",
            "params": {"name": name, "value": value},
        }
        s.sendall((json.dumps(msg) + "\n").encode())
        data = s.recv(4096)
        s.close()
    except (socket.error, OSError):
        pass  # best-effort


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def cmd_list(args: argparse.Namespace) -> int:
    toml_data = _load_toml()
    rows = sorted(set(list(DEFAULTS) + list(toml_data)))
    if not rows:
        print("(no flags defined)")
        return 0
    print(f"{'NAME':40s} {'VALUE':20s} SOURCE")
    print(f"{'-'*40} {'-'*20} ------")
    for name in rows:
        try:
            value, source = resolve(name, toml_data)
            print(f"{name:40s} {str(value)[:20]:20s} {source}")
        except KeyError:
            pass
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    value, source = resolve(args.name)
    print(f"{args.name} = {value!r}  ({source})")
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    _validate_name(args.name)
    new_value = _coerce(args.value)
    toml_data = _load_toml()
    old_value = toml_data.get(args.name, DEFAULTS.get(args.name))
    toml_data[args.name] = new_value
    _save_toml(toml_data)
    _log_history(args.name, old_value, new_value, args.reason or "")
    _broadcast_change(args.name, new_value)
    print(f"Set {args.name} = {new_value!r}")
    return 0


def cmd_unset(args: argparse.Namespace) -> int:
    _validate_name(args.name)
    toml_data = _load_toml()
    if args.name in toml_data:
        old = toml_data.pop(args.name)
        _save_toml(toml_data)
        _log_history(args.name, old, DEFAULTS.get(args.name), "unset")
        print(f"Unset {args.name} (was {old!r})")
    else:
        print(f"{args.name} was not in TOML (nothing to unset)")
    return 0


def cmd_defaults(args: argparse.Namespace) -> int:
    print("[defaults]")
    for k in sorted(DEFAULTS):
        print(f"  {k} = {DEFAULTS[k]!r}")
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    last_state = _load_toml()
    print(f"flag.py: watching {FLAGS_FILE} every {args.interval}s (Ctrl-C to stop)")
    try:
        while True:
            time.sleep(args.interval)
            new_state = _load_toml()
            if new_state != last_state:
                added = set(new_state) - set(last_state)
                removed = set(last_state) - set(new_state)
                changed = {k for k in new_state if k in last_state
                           and new_state[k] != last_state[k]}
                if added:
                    print(f"  +{', '.join(added)}")
                if removed:
                    print(f"  -{', '.join(removed)}")
                if changed:
                    print(f"  ~{', '.join(changed)}")
                last_state = new_state
    except KeyboardInterrupt:
        print("\nflag.py: stopped")
    return 0


def cmd_snapshot(args: argparse.Namespace) -> int:
    """Log the current value with a reason (audit trail only)."""
    value, source = resolve(args.name)
    _log_history(args.name, value, value, args.reason or "snapshot")
    print(f"Snapshotted {args.name}={value!r} (reason: {args.reason})")
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    rows = _read_history(args.name, limit=args.limit)
    if not rows:
        print(f"No history for {args.name}")
        return 0
    print(f"History for {args.name} ({len(rows)} entries):")
    for r in rows:
        ts = r.get("ts_iso", "?")
        old = r.get("old")
        new = r.get("new")
        reason = r.get("reason", "")
        print(f"  {ts}  {old!r:20s} -> {new!r:20s}  {reason}")
    return 0


def _self_test() -> tuple[int, int]:
    passed = 0
    total = 0

    def check(name: str, cond: bool) -> None:
        nonlocal passed, total
        total += 1
        marker = "ok" if cond else "FAIL"
        if cond:
            passed += 1
        print(f"  [{marker}] {name}")

    print("=== flag.py self-tests ===")

    # Test 1: validate name
    try:
        _validate_name("ok_name_123")
        check("valid name passes", True)
    except ValueError:
        check("valid name passes", False)

    try:
        _validate_name(";rm -rf")
        check("invalid name rejected", False)
    except ValueError:
        check("invalid name rejected", True)

    # Test 2: TOML round-trip
    tmp = SNAPSHOT_DIR / ".flag-test.toml"
    try:
        content = _toml_dump(tmp, {"foo": True, "bar": 42, "baz": "hello"})
        tmp.write_text(content)
        loaded = _toml_load(tmp)
        check("TOML bool round-trip", loaded.get("foo") is True)
        check("TOML int round-trip", loaded.get("bar") == 42)
        check("TOML str round-trip", loaded.get("baz") == "hello")
    finally:
        if tmp.exists():
            tmp.unlink()

    # Test 3: env var override
    os.environ["RESUME_ALL_FLAG_NEW_FLAG"] = "true"
    try:
        # Patch DEFAULTS to include this for the test
        DEFAULTS["new_flag"] = False
        value, source = resolve("new_flag")
        check("env var overrides default", source == "env" and value is True)
    finally:
        del os.environ["RESUME_ALL_FLAG_NEW_FLAG"]
        DEFAULTS.pop("new_flag", None)

    # Test 4: default fallback
    value, source = resolve("auto_resume_after_crash")
    check("default returns from DEFAULTS", source == "default")

    # Test 5: coercion
    check("coerce 'true' -> True", _coerce("true") is True)
    check("coerce '42' -> 42", _coerce("42") == 42)
    check("coerce '3.14' -> 3.14", _coerce("3.14") == 3.14)
    check("coerce 'hello' -> 'hello'", _coerce("hello") == "hello")

    # Test 6: set/get/unset cycle (with backup)
    backup = FLAGS_FILE.read_text() if FLAGS_FILE.exists() else None
    try:
        if FLAGS_FILE.exists():
            FLAGS_FILE.unlink()
        cmd_set(argparse.Namespace(
            name="self_test_flag", value="123", reason="unit test"))
        value, source = resolve("self_test_flag")
        check("set then get returns value", value == 123 and source == "toml")

        cmd_unset(argparse.Namespace(name="self_test_flag"))
        if "self_test_flag" in _load_toml():
            check("unset removes from TOML", False)
        else:
            check("unset removes from TOML", True)
    finally:
        if backup is not None:
            FLAGS_FILE.write_text(backup)
        elif FLAGS_FILE.exists():
            FLAGS_FILE.unlink()

    # Test 7: history recording
    before = len(_read_history("self_test_flag"))
    _log_history("self_test_flag", 1, 2, "test")
    after = len(_read_history("self_test_flag"))
    check("history records new entry", after > before)

    print(f"\n{passed}/{total} passed")
    return passed, total


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("list").set_defaults(func=cmd_list)
    sub.add_parser("defaults").set_defaults(func=cmd_defaults)

    p_get = sub.add_parser("get")
    p_get.add_argument("name")
    p_get.set_defaults(func=cmd_get)

    p_set = sub.add_parser("set")
    p_set.add_argument("name")
    p_set.add_argument("value")
    p_set.add_argument("--reason", default="")
    p_set.set_defaults(func=cmd_set)

    p_unset = sub.add_parser("unset")
    p_unset.add_argument("name")
    p_unset.set_defaults(func=cmd_unset)

    p_watch = sub.add_parser("watch")
    p_watch.add_argument("--interval", type=int, default=5)
    p_watch.set_defaults(func=cmd_watch)

    p_snap = sub.add_parser("snapshot")
    p_snap.add_argument("name")
    p_snap.add_argument("reason")
    p_snap.set_defaults(func=cmd_snapshot)

    p_hist = sub.add_parser("history")
    p_hist.add_argument("name")
    p_hist.add_argument("--limit", type=int, default=20)
    p_hist.set_defaults(func=cmd_history)

    sub.add_parser("test").set_defaults(func=lambda a: _self_test())

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
