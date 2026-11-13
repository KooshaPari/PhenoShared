#!/usr/bin/env python3
"""Redact PII from parsed JSON/TSV corpus text.

Redaction happens on PARSED STRINGS only (json.load -> walk -> json.dump),
never by substituting into raw text, so escapes stay valid.

Usage: redact_pii.py <path> [path ...]
Prints "path: <n> substitutions" per file, writes in place, then re-parses
to prove the result is valid JSON. Exits non-zero on any re-parse failure.
"""

from __future__ import annotations

import json
import re
import sys

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
IPV4_RE = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
TOKEN_RE = re.compile(r"(?<![A-Za-z0-9+=_\-])[A-Za-z0-9+=_\-]{32,}(?![A-Za-z0-9+=_\-])")
# DELIBERATELY EXCLUDES '/'. An earlier class included it, so an absolute path
# with at least 32 characters in one unbroken run was matched as a single token
# and replaced wholesale. That destroyed provenance fields (source_location,
# output_path) in sanitized_export_manifest.json while redacting no secret at
# all. Paths are not secrets; keep them out of the token pattern.
HEX_DIGEST_RE = re.compile(r"^[0-9a-fA-F]{32,64}$")
URL_PARAM_RE = re.compile(
    r"([?&])(code|token|key)=([^&#\s\"']*)", re.IGNORECASE
)
PHONE_RE = re.compile(
    r"\+1[\s.\-]?(?:\(\d{3}\)|\d{3})[\s.\-]?\d{3}[\s.\-]?\d{4}"
)

PROTECTED_SUBSTRINGS = ("/Users/kooshapari/CodeProjects",)


def _has_digit(s: str) -> bool:
    return any(c.isdigit() for c in s)


DATE_SLUG_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def _scrub_token_string(s: str) -> tuple[str, int]:
    hits = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal hits
        tok = m.group(0)
        if not _has_digit(tok):
            return tok
        # a hex digest (sha256, commit sha) is provenance, not a secret
        if HEX_DIGEST_RE.match(tok):
            return tok
        # never touch path components or date-led directory slugs
        before = s[m.start() - 1] if m.start() > 0 else ""
        after = s[m.end()] if m.end() < len(s) else ""
        if before == "/" or after == "/":
            return tok
        if DATE_SLUG_RE.match(tok):
            return tok
        hits += 1
        return "<TOKEN-REDACTED>"

    return TOKEN_RE.sub(repl, s), hits


def scrub_string(value: str) -> tuple[str, int]:
    """Redact one string. Returns (new_value, substitution_count)."""
    if not isinstance(value, str) or not value:
        return value, 0

    total = 0

    # email addresses
    value, n = EMAIL_RE.subn("<EMAIL-REDACTED>", value)
    total += n

    # IPv4 addresses
    value, n = IPV4_RE.subn("<IP-REDACTED>", value)
    total += n

    # long hex/base64-ish tokens that contain at least one digit.
    # Do not touch protected path prefixes: split them out first.
    protected_spans = [
        (m.start(), m.end())
        for p in PROTECTED_SUBSTRINGS
        for m in re.finditer(re.escape(p), value)
    ]
    value, n = _scrub_token_string(value)
    total += n
    if protected_spans:
        pass  # token pattern cannot span '/', so paths are already safe

    # URL query params named code/token/key
    def _url_repl(m: re.Match[str]) -> str:
        return f"{m.group(1)}{m.group(2)}=<REDACTED>"

    value, n = URL_PARAM_RE.subn(_url_repl, value)
    total += n

    # +1 phone numbers
    value, n = PHONE_RE.subn("<PHONE-REDACTED>", value)
    total += n

    return value, total


def scrub(obj) -> tuple[object, int]:
    """Walk dicts/lists/strings, scrubbing every string. Returns (obj, count)."""
    if isinstance(obj, dict):
        total = 0
        out = {}
        for k, v in obj.items():
            nk, kn = scrub_string(k) if isinstance(k, str) else (k, 0)
            nv, vn = scrub(v)
            out[nk] = nv
            total += kn + vn
        return out, total
    if isinstance(obj, list):
        total = 0
        out = []
        for v in obj:
            nv, vn = scrub(v)
            out.append(nv)
            total += vn
        return out, total
    if isinstance(obj, str):
        return scrub_string(obj)
    return obj, 0


def _process_json(path: str) -> tuple[int, bool]:
    with open(path, "r", encoding="utf-8") as fh:
        obj = json.load(fh)
    new_obj, count = scrub(obj)
    if count:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(new_obj, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
    # prove it still parses
    try:
        with open(path, "r", encoding="utf-8") as fh:
            json.load(fh)
    except Exception as exc:  # noqa: BLE001
        print(f"{path}: RE-PARSE FAILED: {exc}", file=sys.stderr)
        return count, False
    return count, True


def _process_tsv(path: str) -> tuple[int, bool]:
    with open(path, "r", encoding="utf-8", newline="") as fh:
        raw = fh.read()
    trailing_newline = raw.endswith("\n")
    lines = raw.split("\n")
    if trailing_newline:
        lines = lines[:-1]
    total = 0
    out_lines = []
    for line in lines:
        fields = line.split("\t")
        new_fields = []
        for field in fields:
            nf, n = scrub_string(field)
            new_fields.append(nf)
            total += n
        out_lines.append("\t".join(new_fields))
    if total:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write("\n".join(out_lines))
            if trailing_newline:
                fh.write("\n")
    return total, True


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: redact_pii.py <path> [path ...]", file=sys.stderr)
        return 2
    ok = True
    for path in argv:
        lowered = path.lower()
        if lowered.endswith(".json"):
            count, good = _process_json(path)
        elif lowered.endswith(".tsv"):
            count, good = _process_tsv(path)
        else:
            print(f"{path}: skipped (not .json/.tsv)")
            continue
        print(f"{path}: {count} substitutions")
        if not good:
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
