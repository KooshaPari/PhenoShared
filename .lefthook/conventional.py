#!/usr/bin/env python3
"""Validate commit messages follow Conventional Commits format."""
import re
import sys
import os

def main():
    if len(sys.argv) < 2:
        print("Usage: conventional.py <commit-msg-file>")
        sys.exit(1)

    # Handle both file path and direct message
    arg = sys.argv[1]
    if os.path.isfile(arg):
        with open(arg, "r", encoding="utf-8", errors="replace") as f:
            msg = f.read().strip()
    else:
        msg = arg.strip()

    # Conventional Commits pattern: type(scope): description
    pattern = r"^(feat|fix|docs|style|refactor|test|chore|ci|perf|build)(\(.+\))?: .{1,}"

    if re.match(pattern, msg):
        print(f"OK: {msg[:80]}")
        sys.exit(0)
    else:
        print(f"ERROR: commit message must follow Conventional Commits")
        print(f"  Got: {msg[:80]}")
        print(f"  Expected: type(scope): description")
        print(f"  Types: feat, fix, docs, style, refactor, test, chore, ci, perf, build")
        sys.exit(1)

if __name__ == "__main__":
    main()
