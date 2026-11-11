#!/usr/bin/env python3
"""Secure credential wipe (operator-authorized 2026-10-11: 'creds wont be rotated,
up to you to secure and wipe off system').

Scans target files for credential-shaped strings (same patterns as the F2b scan,
plus a few extras) and replaces each match in place with [REDACTED-CRED-n].
Zip archives containing a scrubbed extracted copy are re-packed from the scrubbed
files. Produces goal2/credential_wipe.md (counts only, no secrets).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

PATTERNS = {
    "aws_access_key": r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b",
    "github_token": r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b",
    "openai_style_key": r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b",
    "anthropic_key": r"\bsk-ant-[A-Za-z0-9_-]{20,}\b",
    "slack_token": r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b",
    "google_api_key": r"\bAIza[0-9A-Za-z_-]{35}\b",
    "jwt": r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b",
    "private_key_block": r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY(?: BLOCK)?",
    "password_assignment": r"(?i)\b(?:password|passwd|pwd|secret|api[_-]?key|auth[_-]?token)\s*[:=]\s*[\"']?([^\s\"']{8,})",
    "bearer_header": r"(?i)\bBearer\s+[A-Za-z0-9._-]{20,}",
}

COMPILED = {k: re.compile(v) for k, v in PATTERNS.items()}
WIPE_LOG = []
COUNTER = {"n": 0}


def scrub_text(text):
    for name, pat in COMPILED.items():
        def repl(m):
            COUNTER["n"] += 1
            return f"[REDACTED-CRED-{COUNTER['n']}]"
        text = pat.sub(repl, text)
    return text


def scrub_file(path):
    try:
        with open(path, encoding="utf-8") as f:
            original = f.read()
    except (UnicodeDecodeError, IsADirectoryError):
        return 0
    scrubbed = scrub_text(original)
    if scrubbed != original:
        tmp = path + ".wipe-tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(scrubbed)
        os.replace(tmp, path)
    n = sum(1 for _ in re.finditer(r"\[REDACTED-CRED-\d+\]", scrubbed)) - \
        sum(1 for _ in re.finditer(r"\[REDACTED-CRED-\d+\]", original))
    WIPE_LOG.append({"file": path, "replacements": COUNTER["n"]})
    return COUNTER["n"]


def rescan(path):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except (UnicodeDecodeError, IsADirectoryError):
        return 0
    return sum(len(p.findall(text)) for p in COMPILED.values())


EXCLUDE_DIRS = {".venv", "venv", "site-packages", "node_modules", "__pycache__", ".git", ".fix-tmp"}


def main():
    roots = [
        "/Users/kooshapari/Downloads/conversations.json",
        "/Users/kooshapari/Downloads/light_metadata-000",
        "/Users/kooshapari/Exports/claude-20261010/raw",
        "/Users/kooshapari/Exports/analysis",
    ]
    targets = []
    for r in roots:
        if os.path.isfile(r):
            targets.append(r)
        else:
            for dirpath, dirs, files in os.walk(r):
                dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
                for fn in files:
                    if fn.endswith((".json", ".jsonl", ".md", ".txt", ".tsv", ".py", ".html", ".csv")):
                        targets.append(os.path.join(dirpath, fn))

    total = 0
    dirty = []
    for t in targets:
        COUNTER["n"] = 0
        n = scrub_file(t)
        if n:
            dirty.append({"file": t, "replacements": n})
            total += n

    # repack conversations-000.zip from the scrubbed extracted copy
    zip_path = "/Users/kooshapari/Exports/claude-20261010/conversations-000.zip"
    src_dir = "/Users/kooshapari/Exports/claude-20261010/raw/conversations-000"
    repacked = False
    if os.path.exists(zip_path) and os.path.isdir(src_dir):
        tmpd = tempfile.mkdtemp(prefix="ziprepack-")
        try:
            newzip = os.path.join(tmpd, "conversations-000-new.zip")
            subprocess.run(["zip", "-r", "-q", newzip, "conversations-000"],
                           cwd=os.path.dirname(src_dir), check=True)
            # verify the new zip is clean
            testdir = os.path.join(tmpd, "t")
            os.makedirs(testdir)
            subprocess.run(["unzip", "-q", newzip, "-d", testdir], check=True)
            dirty_zip = False
            for dirpath, _d, files in os.walk(testdir):
                for fn in files:
                    if rescan(os.path.join(dirpath, fn)):
                        dirty_zip = True
            if not dirty_zip:
                shutil.move(newzip, zip_path)
                repacked = True
            else:
                os.unlink(newzip)
        finally:
            shutil.rmtree(tmpd, ignore_errors=True)

    # verification pass over everything
    residue = {t: rescan(t) for t in targets}
    residue = {k: v for k, v in residue.items() if v}

    report = {
        "targets_scanned": len(targets),
        "files_scrubbed": len(dirty),
        "total_replacements": total,
        "repacked_zip_clean": repacked,
        "residue_after_wipe": residue,
        "scrubbed": dirty,
    }
    out = "/Users/kooshapari/Exports/analysis/goal2/credential_wipe.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(json.dumps({"targets_scanned": len(targets), "files_scrubbed": len(dirty),
                      "total_replacements": total, "repacked_zip_clean": repacked,
                      "residue": residue}, indent=2))


if __name__ == "__main__":
    main()
