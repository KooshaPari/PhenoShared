"""Command-line interface for cr_router (SP2 dry-run).

Three subcommands:

    python -m cr_router pick    [--state-root PATH] [--dry-run]
    python -m cr_router status  [--state-root PATH]
    python -m cr_router list    (shows the D3 queue without any state)

No HTTP calls. The CLI is the operator-facing surface for verifying the
rotation logic without touching any provider's API.

Exit codes:
    0 — success (a provider was picked, or status/list rendered)
    1 — every provider is exhausted (pick only)
    2 — internal error (bad args, missing files)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cr_router.router import Router, RouterError


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m cr_router", description="cr_router: code-review provider rotation (dry-run)")
    p.add_argument("--state-root", type=Path, default=Path("./var/cr_router"),
                   help="Directory for QuotaStore JSON files (default: ./var/cr_router)")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_pick = sub.add_parser("pick", help="Pick the next provider (records consumption unless --dry-run)")
    p_pick.add_argument("--dry-run", action="store_true", help="Do not record consumption")

    sub.add_parser("status", help="Show per-provider usage/remaining state")
    sub.add_parser("list", help="Show the D3 provider queue (no state read)")

    return p


def _cmd_pick(args: argparse.Namespace) -> int:
    try:
        router = Router(state_root=args.state_root, dry_run=args.dry_run)
    except RouterError as exc:
        print(f"cr_router: {exc}", file=sys.stderr)
        return 2
    chosen = router.pick()
    if chosen is None:
        print("cr_router: every provider exhausted", file=sys.stderr)
        return 1
    payload = {
        "picked": chosen["id"],
        "name": chosen.get("name", chosen["id"]),
        "priority": chosen.get("priority"),
        "dry_run": router.dry_run,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    try:
        router = Router(state_root=args.state_root, dry_run=True)
    except RouterError as exc:
        print(f"cr_router: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(router.status(), indent=2, sort_keys=True))
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    router = Router(state_root=args.state_root, dry_run=True)
    ids = router.queue.all_ids()
    print(json.dumps({"queue": ids, "primary": ids[0] if ids else None}, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.cmd == "pick":
        return _cmd_pick(args)
    if args.cmd == "status":
        return _cmd_status(args)
    if args.cmd == "list":
        return _cmd_list(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
