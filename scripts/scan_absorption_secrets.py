#!/usr/bin/env python3
"""Scan absorbed trees for credentials before publishing.

Written after a push was blocked by GitHub Push Protection: an earlier ad-hoc
scan checked AWS, GitHub, Slack, tailnet and PEM patterns but *not* the
OpenAI/Anthropic/HF/Google/Stripe formats, so real keys from an absorbed repo
reached a candidate commit. Nothing leaked (the push was rejected), but the
lesson is that an allow-list of "the providers I thought of" is not a scanner.

Run this over every path before committing an absorption:

    python scripts/scan_absorption_secrets.py absorption/
    python scripts/scan_absorption_secrets.py absorption/<repo>/ --verbose

Exit code 1 when findings exist, so it can gate a pre-commit hook or CI step.
"""

from __future__ import annotations

import argparse
import os
import re
import sys

PATTERNS = [
    ("openai", re.compile(r"\bsk-(?:proj-|ant-)?[A-Za-z0-9_\-]{20,}")),
    ("anthropic", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}")),
    ("huggingface", re.compile(r"\bhf_[A-Za-z0-9]{30,}")),
    ("google-api", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}")),
    ("stripe", re.compile(r"\b(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{20,}")),
    ("aws-key", re.compile(r"\b(?:AKIA|ASIA)(?!IOSFODNN7EXAMPLE)[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("slack", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("tailnet-ip", re.compile(r"\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b")),
    ("tailnet-host", re.compile(r"\b[a-z0-9][a-z0-9-]{1,40}\.ts\.net\b", re.I)),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.")),
]

# Canonical example values that appear in documentation and test vectors.
BENIGN_VALUES = {
    "100.64.0.0",           # CGNAT range base
    "100.64.0.1",           # CGNAT range start
    "100.96.0.0",           # CGNAT /12 boundary used in docs
    "100.100.100.100",      # Tailscale magic DNS
    "AKIAIOSFODNN7EXAMPLE",  # AWS documentation example
    "AKIAABCDEFGHIJKLMNOP",  # obvious placeholder
    "4bf92f3577b34da6a3ce929d0e0e4736",  # W3C traceparent example
    "ghp_abcdefghijklmnopqrstuvwxyz0123456789",  # fake
}

# Placeholder wording anywhere in the matched value marks it non-sensitive.
PLACEHOLDER = re.compile(
    r"(REDACTED|DO-NOT|your[-_]|example|placeholder|changeme|invalid|"
    r"ZYXWVUTSRQ|sk-abcdefg|sk-legacy|xxxx|0000)",
    re.I,
)

SKIP_DIRS = {".git", "node_modules", "target", ".venv", "dist", "build",
             "__pycache__", ".pytest_cache", ".mypy_cache"}


def scan(root: str, max_bytes: int = 2_000_000):
    findings = []
    scanned = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            path = os.path.join(dirpath, name)
            scanned += 1
            try:
                if os.path.getsize(path) > max_bytes:
                    continue
                text = open(path, "rb").read().decode("utf-8", "ignore")
            except OSError:
                continue
            for label, rx in PATTERNS:
                for match in rx.finditer(text):
                    value = match.group(0)
                    if value in BENIGN_VALUES:
                        continue
                    if any(b in value for b in BENIGN_VALUES):
                        continue
                    if PLACEHOLDER.search(value):
                        continue
                    line = text.count("\n", 0, match.start()) + 1
                    findings.append((os.path.relpath(path, root), line, label, value[:60]))
                    break
    return scanned, findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", nargs="?", default="absorption")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        print("not a directory: %s" % args.root, file=sys.stderr)
        return 2

    scanned, findings = scan(args.root)
    print("scanned %d files, %d finding(s)" % (scanned, len(findings)))
    for rel, line, label, value in findings:
        if args.verbose:
            print("  %-14s %s:%d  %s" % (label, rel, line, value))
        else:
            print("  %-14s %s:%d" % (label, rel, line))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
