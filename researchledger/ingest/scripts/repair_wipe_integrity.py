#!/usr/bin/env python3
"""Post-wipe integrity repair.

The credential scrubber replaced matches that sometimes consumed the backslash of
an escaped quote inside JSON string values, leaving orphan unescaped quotes.
This pass: parse every JSON/JSONL touched by the wipe; on failure apply targeted
fixups (re-escape quotes that immediately follow a [REDACTED-CRED-n] marker)
until the file parses again. Reports per-file parse status before/after.
"""
import json
import os
import re
import sys

CANDIDATES = [
    "/Users/kooshapari/Downloads/conversations.json",
    "/Users/kooshapari/Downloads/light_metadata-000",
    "/Users/kooshapari/Exports/claude-20261010/raw",
    "/Users/kooshapari/Exports/analysis",
]

FIXUPS = [
    (re.compile(r'(\[REDACTED-CRED-\d+\])"'), r'\1\\"'),      # orphan quote after marker
]


def check_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            if path.endswith(".jsonl"):
                for i, line in enumerate(f):
                    if line.strip():
                        json.loads(line)
            else:
                json.load(f)
        return True
    except Exception:
        return False


def repair_jsonl(path):
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    changed = False
    out = []
    for line in lines:
        if not line.strip():
            out.append(line)
            continue
        try:
            json.loads(line)
            out.append(line)
            continue
        except Exception:
            pass
        cur = line
        for _ in range(6):  # bounded fixup iterations
            fixed = cur
            for pat, rep in FIXUPS:
                fixed = pat.sub(rep, fixed)
            if fixed == cur:
                break
            cur = fixed
            try:
                json.loads(cur)
                break
            except Exception:
                continue
        try:
            json.loads(cur)
            out.append(cur if cur.endswith("\n") else cur + "\n")
            changed = True
        except Exception:
            print(f"UNREPAIRABLE line in {path}: {line[:120]!r}", file=sys.stderr)
            out.append(line)
    if changed:
        tmp = path + ".fix-tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.writelines(out)
        os.replace(tmp, path)
    return changed


def repair_json(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    cur = text
    try:
        json.loads(cur)
        return False
    except Exception:
        pass
    for _ in range(6):
        fixed = cur
        for pat, rep in FIXUPS:
            fixed = pat.sub(rep, fixed)
        if fixed == cur:
            break
        cur = fixed
        try:
            json.loads(cur)
            tmp = path + ".fix-tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(cur)
            os.replace(tmp, path)
            return True
        except Exception:
            continue
    print(f"UNREPAIRABLE json: {path}", file=sys.stderr)
    return False


def main():
    targets = []
    for r in CANDIDATES:
        if os.path.isfile(r):
            targets.append(r)
        else:
            for dirpath, _d, files in os.walk(r):
                for fn in files:
                    if fn.endswith((".json", ".jsonl")):
                        targets.append(os.path.join(dirpath, fn))

    broken_before, repaired, still_broken = [], [], []
    for t in targets:
        if check_json(t):
            continue
        broken_before.append(t)
        fixed = repair_jsonl(t) if t.endswith(".jsonl") else repair_json(t)
        (repaired if fixed and check_json(t) else still_broken).append(t)

    print(json.dumps({
        "files_checked": len(targets),
        "broken_before": len(broken_before),
        "repaired": len(repaired),
        "still_broken": still_broken,
        "broken_files": broken_before,
    }, indent=2))


if __name__ == "__main__":
    main()
