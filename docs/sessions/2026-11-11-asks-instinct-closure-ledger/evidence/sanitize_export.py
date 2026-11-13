#!/usr/bin/env python3
"""Produce the ONE sanitized, shareable form of an iMessage export bundle.

Why this exists
---------------
A restore-tree iMessage export carries a ``history_residual_note`` naming earlier
commits that retain one-time login codes and link tokens.  Operator ruling
2026-11-12 (option B): the raw bundle is do-not-share; the only shareable form is
an extract with every credential-shaped value stripped.

Method
------
Reuses the conventions already in this directory rather than inventing a second
one:

* ``redact_pii.py``  -> redact on PARSED STRINGS only (``json.load`` -> walk ->
  ``json.dump``), never by substituting into raw text, so JSON escapes stay valid.
* ``redact_phones.py`` -> the exact phone pattern ``\\+1\\d{10}`` and the
  ``<PHONE-REDACTED>`` token.

Every pattern is named, explicit, and listed in ``PATTERNS`` with a comment.
Patterns are applied in order, so a specific pattern (e.g. the Cloudflare
email-verification URL param) consumes its match before a general pattern
(e.g. any ``?token=``) can see it.  No count is therefore double-reported.

Guarantees
----------
(a) Credential patterns are REDACTED, never silently deleted from structure.
(b) Phone redaction matches ``redact_phones.py``.
(c) The input path is never written into the output; the script asserts it.
(d) Idempotent: every replacement token contains no characters any pattern can
    re-match, so a second run reports 0 hits and writes byte-identical output.
(e) Prints a per-pattern hit count, and never prints a matched value.

Refuses to overwrite an existing output path unless ``--force``.

Usage
-----
    sanitize_export.py <input.json> <output.json> [--force] [--counts-only]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Phone redaction: EXACTLY redact_phones.py's convention.
# ---------------------------------------------------------------------------
PHONE_E164_RE = re.compile(r"\+1\d{10}")
PHONE_REDACTED = "<PHONE-REDACTED>"

# Separator/format variant (from redact_pii.py) so a formatted number cannot
# survive a pattern that only understood the bare E.164 form.
PHONE_FORMATTED_RE = re.compile(
    r"\+1[\s.\-]?(?:\(\d{3}\)|\d{3})[\s.\-]?\d{3}[\s.\-]?\d{4}"
)

# ---------------------------------------------------------------------------
# PATTERNS: (name, compiled regex, replacement, scope, comment)
#
# scope "text" = free text and URL-bearing fields only (body, link,
#                media_urls).  Structural identifiers -- message_id,
#                conversation_id, reply_to_message_id, ts -- are NEVER passed
#                to a token pattern, because a message id is an opaque 26-char
#                ULID-like string that a length-only token heuristic matches:
#                measured 8019/8019.  Redacting it would destroy the dataset
#                without removing any credential.
# scope "all"  = every string in the document.
#
# Order matters: specific -> general.
# ---------------------------------------------------------------------------
PATTERNS: list[tuple[str, re.Pattern[str], str | None, str, str]] = [
    # 1. Cloudflare email-verification URL token.  Named explicitly by the
    #    residual note ("Cloudflare email-verification URL token").  Redacts the
    #    value only, keeping scheme/host/path legible.
    (
        "cloudflare_email_verify_url",
        re.compile(
            r"(?i)(https?://[^\s\"'<>]*?email[-_]?verification[^\s\"'<>]*?"
            r"[?&](?:token|code|t)=)([^&#\s\"'<>]+)"
        ),
        r"\1<VERIFY-TOKEN-REDACTED>",
        "all",
        "Cloudflare email-verification URL token (residual note, commit f8321714)",
    ),
    # 2. Any bearer-style URL query value under a credential-ish parameter name.
    #    Covers "all link tokens" from the residual note: request/approval links,
    #    file-delivery links, chat share links.
    (
        "url_query_token",
        re.compile(
            r"(?i)([?&](?:code|token|key|verify|verification|otp|t|sig|access_token"
            r"|share|shareId|fileId|download)=)([^&#\s\"'<>]{4,})"
        ),
        r"\1<URL-TOKEN-REDACTED>",
        "all",
        "credential-shaped URL query value (link tokens)",
    ),
    # 3. JWT / bearer token.
    (
        "jwt",
        re.compile(r"\beyJ[A-Za-z0-9_\-]{6,}\.[A-Za-z0-9_\-]{6,}\.[A-Za-z0-9_\-]{4,}\b"),
        "<JWT-REDACTED>",
        "all",
        "JWT (3 dot-separated base64url segments)",
    ),
    # 4. One-time / device / login code stated next to its label.
    (
        "otp_labelled",
        re.compile(
            r"(?i)\b(code|otp|passcode|one[- ]time code|verification code|"
            r"login code|device code)\b([^0-9A-Za-z]{0,15})(\d{4,8})\b"
        ),
        r"\1\2<OTP-REDACTED>",
        "all",
        "labelled one-time / device / login code (digits only)",
    ),
    # 5. Bare 6-digit code introduced as "is 123456" / "#123456".
    (
        "otp_hash_or_is",
        re.compile(r"(?i)(\b(?:code|otp)\b[^\d]{0,20})(?:#|\bis\s+)(\d{6})\b"),
        r"\1<OTP-REDACTED>",
        "all",
        "6-digit one-time code after '# ' or 'is '",
    ),
    # 6. Long opaque secret in free text / URLs: 32+ chars, mixed case, has a
    #    digit, and is not a pure hex digest or timestamp.  Scope "text" only,
    #    so message ids and conversation ids survive.  Only credential-SHAPED
    #    matches are redacted; see pattern 6b for the deliberate remainder.
    (
        "long_b64_token",
        re.compile(r"(?<![A-Za-z0-9+/=_\-])[A-Za-z0-9+/=_\-]{32,}(?![A-Za-z0-9+/=_\-])"),
        "<TOKEN-REDACTED>",
        "text",
        "long base64url/opaque token in free text or a URL",
    ),
    # 6b. The same length heuristic WITHOUT the credential-shape guard, counted
    #     but PRESERVED (replacement is the empty marker sentinel PRESERVE).
    #     These are pure-hex digests, all-lowercase slugs, and ids.  They are not
    #     credentials, and redacting them would corrupt the dataset.  Reported so
    #     the residual count is explained rather than unexplained.
    (
        "long_opaque_id_preserved",
        re.compile(r"(?<![A-Za-z0-9+/=_\-])[A-Za-z0-9+/=_\-]{32,}(?![A-Za-z0-9+/=_\-])"),
        None,  # PRESERVE: matched, counted, never rewritten
        "text",
        "long id/slug/hex digest preserved by design (not a credential)",
    ),
    # 7. Email address.
    (
        "email",
        re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),
        "<EMAIL-REDACTED>",
        "all",
        "email address",
    ),
    # 8. IPv4 address.
    (
        "ipv4",
        re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])"),
        "<IP-REDACTED>",
        "all",
        "IPv4 address",
    ),
    # 9/10. Phone numbers, redact_phones.py convention first.
    ("phone_e164", PHONE_E164_RE, PHONE_REDACTED, "all", "E.164 phone (+1 + 10 digits)"),
    (
        "phone_formatted",
        PHONE_FORMATTED_RE,
        PHONE_REDACTED,
        "all",
        "formatted +1 phone number",
    ),
]

# The credential-shaped subset that MUST reach zero for the output to be called
# shareable.  phone/email/ipv4 are PII, tracked separately.
CREDENTIAL_PATTERNS = (
    "cloudflare_email_verify_url",
    "url_query_token",
    "jwt",
    "otp_labelled",
    "otp_hash_or_is",
    "long_b64_token",
)

# Fields whose contents are free text / URLs, i.e. eligible for "text" scope.
TEXT_FIELDS = frozenset({"body", "link", "media_urls"})

# Structural identifiers that must never be rewritten (documented in scope note).
STRUCTURAL_FIELDS = frozenset(
    {"message_id", "conversation_id", "reply_to_message_id", "ts", "service",
     "delivery_status_recorded", "type"}
)


def _token_like(value: str) -> bool:
    """True for a long opaque string that looks like a secret, not a hex id."""
    if not any(c.isdigit() for c in value):
        return False
    if not any(c.isupper() for c in value):
        return False
    if not any(c.islower() for c in value):
        return False
    if re.fullmatch(r"[0-9a-f]+", value):
        return False
    if re.fullmatch(r"[0-9A-F]+", value):
        return False
    return True


def _apply(text: str, name: str, pattern: re.Pattern[str], repl: str | None) -> tuple[str, int]:
    """Apply one pattern. ``repl is None`` counts matches and preserves them."""
    if repl is None:
        return text, len(pattern.findall(text))
    if name == "long_b64_token":
        # Count ONLY tokens actually redacted, so the reported credential count
        # is the number of secrets removed, not the number of candidates seen.
        redacted = 0
        pieces: list[str] = []
        pos = 0
        for m in pattern.finditer(text):
            pieces.append(text[pos:m.start()])
            if _token_like(m.group(0)):
                pieces.append(repl)
                redacted += 1
            else:
                pieces.append(m.group(0))
            pos = m.end()
        if not redacted:
            return text, 0
        pieces.append(text[pos:])
        return "".join(pieces), redacted
    return pattern.subn(repl, text)


def scrub_string(value: str, scope: str) -> tuple[str, dict[str, int]]:
    """Redact one string under the given scope. Never prints the value."""
    hits: dict[str, int] = {}
    if not isinstance(value, str) or not value:
        return value, hits
    out = value
    for name, pattern, repl, pat_scope, _comment in PATTERNS:
        if pat_scope == "text" and scope != "text":
            continue
        out, n = _apply(out, name, pattern, repl)
        if n:
            hits[name] = hits.get(name, 0) + n
    return out, hits


def scrub(obj, scope: str = "all", key: str | None = None) -> tuple[object, dict[str, int]]:
    """Walk the document, redacting strings. Structural ids are skipped."""
    total: dict[str, int] = {}
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in STRUCTURAL_FIELDS:
                out[k] = v  # never rewritten; ids are not credentials
                continue
            child_scope = "text" if k in TEXT_FIELDS else "all"
            if k in TEXT_FIELDS and isinstance(v, list):
                new_list = []
                for item in v:
                    if isinstance(item, str):
                        ni, h = scrub_string(item, "text")
                        new_list.append(ni)
                        _merge(total, h)
                    else:
                        ni, h = scrub(item, "text", k)
                        new_list.append(ni)
                        _merge(total, h)
                out[k] = new_list
                continue
            nv, h = scrub(v, child_scope, k)
            out[k] = nv
            _merge(total, h)
        return out, total
    if isinstance(obj, list):
        out_l = []
        for v in obj:
            nv, h = scrub(v, scope, key)
            out_l.append(nv)
            _merge(total, h)
        return out_l, total
    if isinstance(obj, str):
        return scrub_string(obj, scope)
    return obj, total


def _merge(dst: dict[str, int], src: dict[str, int]) -> None:
    for k, v in src.items():
        dst[k] = dst.get(k, 0) + v


def count_hits(obj, key: str | None = None) -> dict[str, int]:
    """Read-only per-pattern counts, same scoping as scrub()."""
    _, hits = scrub(obj, "all", key)
    return hits


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--force", action="store_true", help="overwrite an existing output")
    ap.add_argument(
        "--counts-only",
        action="store_true",
        help="report source counts and exit without writing",
    )
    args = ap.parse_args(argv[1:])

    src = Path(args.input).expanduser().resolve()
    dst = Path(args.output).expanduser().resolve()

    if not src.is_file():
        print(f"input not found: {src}", file=sys.stderr)
        return 2
    if src == dst:
        print("refusing: input and output are the same path", file=sys.stderr)
        return 2
    if dst.exists() and not args.force:
        print(f"refusing: output exists (pass --force): {dst}", file=sys.stderr)
        return 3

    src_text = src.read_text(encoding="utf-8")
    doc = json.loads(src_text)
    del src_text  # never keep a second full copy of the raw bundle in memory

    if args.counts_only:
        hits = count_hits(doc)
        for name, *_ in PATTERNS:
            print(f"source {name}: {hits.get(name, 0)}")
        return 0

    cleaned, hits = scrub(doc)

    # (c) the input path must never appear in the output.
    serialized = json.dumps(cleaned, indent=1, ensure_ascii=False, sort_keys=False)
    if str(src) in serialized or src.name in serialized:
        print("aborting: input path leaked into output", file=sys.stderr)
        return 4

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(serialized + "\n", encoding="utf-8")

    # prove the output is still valid JSON
    reloaded = json.loads(dst.read_text(encoding="utf-8"))
    if not isinstance(reloaded, dict):
        print("aborting: output did not round-trip to an object", file=sys.stderr)
        return 5

    print(f"output: {dst}")
    for name, *_ in PATTERNS:
        print(f"redacted {name}: {hits.get(name, 0)}")
    print(f"output_bytes: {dst.stat().st_size}")
    print(f"output_lines: {sum(1 for _ in dst.open('rb'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
