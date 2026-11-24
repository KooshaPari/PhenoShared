#!/usr/bin/env python3
"""Goal 2 addendum (LOCAL): credential/secret scan over attachment extractions.

Scans every attachments[].extracted_content in conversations-000/conversations.json
for credential-shaped strings. Outputs only COUNTS + MASKED examples (prefix only)
to goal2/attachment_scan.json. Nothing sensitive is written to disk.
"""
import json
import os
import re

RAW = "/Users/kooshapari/Exports/claude-20261010/raw/conversations-000/conversations.json"
OUT = "/Users/kooshapari/Exports/analysis/goal2/attachment_scan.json"

PATTERNS = {
    "aws_access_key": r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b",
    "github_token": r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b",
    "openai_style_key": r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b",
    "anthropic_key": r"\bsk-ant-[A-Za-z0-9_-]{20,}\b",
    "slack_token": r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b",
    "google_api_key": r"\bAIza[0-9A-Za-z_-]{35}\b",
    "jwt": r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b",
    "private_key_block": r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY",
    "password_assignment": r"(?i)\b(?:password|passwd|pwd|secret|api[_-]?key|auth[_-]?token)\s*[:=]\s*[\"']?([^\s\"']{6,})",
    "bearer_header": r"(?i)\bBearer\s+[A-Za-z0-9._-]{20,}",
}


def mask(s):
    s = str(s)
    return (s[:8] + "…[REDACTED]") if len(s) > 8 else "[REDACTED]"


def main():
    data = json.load(open(RAW, encoding="utf-8"))
    hits = {k: [] for k in PATTERNS}
    n_att = 0
    n_with_content = 0
    total_bytes = 0
    for conv in data:
        for msg in conv.get("chat_messages", []):
            for att in (msg.get("attachments") or []):
                content = att.get("extracted_content")
                if not content:
                    continue
                n_att += 1
                n_with_content += 1
                total_bytes += len(content)
                fname = att.get("file_name") or att.get("name") or ""
                # redact filename to a length+ext shape only
                fname_r = f"[len={len(fname)}]{os.path.splitext(fname)[1][:8]}"
                for pat_name, pat in PATTERNS.items():
                    for m in re.finditer(pat, content):
                        snippet = m.group(0)
                        # don't keep password-assignment values verbatim beyond mask
                        hits[pat_name].append({
                            "attachment": fname_r,
                            "match_masked": mask(snippet),
                            "at_byte": m.start(),
                        })
                        if len(hits[pat_name]) >= 200:  # cap per pattern
                            break
                    if len(hits[pat_name]) >= 200:
                        break

    out = {
        "attachments_scanned": n_with_content,
        "total_bytes_scanned": total_bytes,
        "pattern_counts": {k: len(v) for k, v in hits.items()},
        "examples_masked": {k: v[:5] for k, v in hits.items() if v},
        "note": "Counts may include duplicates of the same secret across mirrored attachments; masked examples keep only an 8-char prefix.",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(json.dumps({"attachments_scanned": n_with_content,
                      "pattern_counts": out["pattern_counts"]}, indent=2))


if __name__ == "__main__":
    main()
