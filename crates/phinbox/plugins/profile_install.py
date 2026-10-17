#!/usr/bin/env python3
"""Scoped MCP profile installer. Dry-run by default; never edits canonical profiles/hooks."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

NAME = 'phinbox_mcp'
ROOTS = ('codex', 'jcode', 'forge', 'kcode')


def atomic(path, value):
    fd, name = tempfile.mkstemp(prefix='.phinbox-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, indent=2)
            stream.write('\n')
        os.chmod(name, path.stat().st_mode & 0o777 if path.exists() else 0o600)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def codex(args, profile):
    env = dict(os.environ, CODEX_HOME=str(profile))
    result = subprocess.run([args.codex_cli, 'mcp', *args.native_args], env=env,
                            cwd=str(profile), capture_output=True, text=True, timeout=20)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('harness', choices=ROOTS)
    parser.add_argument('--profile-dir', required=True, type=Path)
    parser.add_argument('--inbox-dir', required=True, type=Path)
    parser.add_argument('--binary', default='phinbox-mcp')
    parser.add_argument('--codex-cli', default='codex')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--uninstall', action='store_true')
    args = parser.parse_args()
    if not args.profile_dir.is_absolute() or not args.inbox_dir.is_absolute():
        parser.error('profile and inbox paths must be absolute')
    profile = args.profile_dir.resolve()
    canonical = [Path.home() / ('.' + h) for h in (*ROOTS, 'helioslite')]
    if any(profile == p.resolve() or p.resolve() in profile.parents or profile in p.resolve().parents for p in canonical):
        parser.error('canonical harness profiles are outside this isolated installer scope')
    filename = 'config.toml' if args.harness == 'codex' else ('.mcp.json' if args.harness == 'forge' else 'mcp.json')
    target = profile / filename
    receipt = profile / '.phinbox-install-receipt.json'
    for path in (target, receipt):
        if path.is_symlink():
            parser.error('managed files may not be symlinks')
    entry = {'command': args.binary, 'args': [], 'env': {'PHINBOX_INBOX_DIR': str(args.inbox_dir.resolve())}}
    plan = {'harness': args.harness, 'operation': 'uninstall' if args.uninstall else 'install',
            'profile': str(profile), 'configuration': str(target), 'server': NAME,
            'entry': entry, 'applied': args.apply, 'hooks_modified': False}
    if not args.apply:
        print(json.dumps(plan, indent=2))
        return
    profile.mkdir(parents=True, exist_ok=True)
    with (profile / '.phinbox-install.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        old = json.loads(receipt.read_text()) if receipt.exists() else None
        if old and (old.get('harness') != args.harness or old.get('configuration') != str(target)):
            raise ValueError('another harness owns this installation receipt')
        if args.harness == 'codex':
            args.native_args = ['get', NAME, '--json']
            result = codex(args, profile)
            current = json.loads(result.stdout) if result.returncode == 0 else None
            if result.returncode and target.exists() and NAME in target.read_text():
                raise ValueError('native Codex could not inspect existing registration; refusing mutation')
            if args.uninstall:
                if not old or current != old.get('native_registration'):
                    raise ValueError('registration not owned or changed; refusing uninstall')
                args.native_args = ['remove', NAME]
            else:
                if current is not None:
                    if old and current == old.get('native_registration') and entry == old.get('entry'):
                        print(json.dumps(dict(plan, unchanged=True)));return
                    raise ValueError('existing server registration is not this exact owned installation')
                args.native_args = ['add', NAME, '--env', 'PHINBOX_INBOX_DIR=' + entry['env']['PHINBOX_INBOX_DIR'], '--', args.binary]
            result = codex(args, profile)
            if result.returncode:
                raise ValueError('native Codex MCP operation failed; hook/config details withheld')
            if not args.uninstall:
                args.native_args = ['get', NAME, '--json']
                result = codex(args, profile)
                if result.returncode:
                    raise ValueError('native Codex registration verification failed')
                plan['native_registration'] = json.loads(result.stdout)
        else:
            data = json.loads(target.read_text()) if target.exists() else {}
            if not isinstance(data, dict):
                raise ValueError('MCP configuration must be an object')
            key = 'mcpServers' if args.harness == 'forge' else 'servers'
            servers = data.setdefault(key, {})
            if not isinstance(servers, dict):
                raise ValueError('MCP server map must be an object')
            if args.uninstall:
                if not old or servers.get(NAME) != old.get('entry'):
                    raise ValueError('registration not owned or changed; refusing uninstall')
                del servers[NAME]
            else:
                if NAME in servers:
                    if old and servers[NAME] == old.get('entry') == entry:
                        print(json.dumps(dict(plan, unchanged=True)));return
                    raise ValueError('existing server registration is not this exact owned installation')
                servers[NAME] = entry
            atomic(target, data)
        if args.uninstall:
            receipt.unlink()
        else:
            atomic(receipt, plan)
    print(json.dumps(plan, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        print('phinbox isolated MCP operation refused: ' + str(exc), file=sys.stderr)
        raise SystemExit(2)
