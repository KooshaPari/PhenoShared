#!/usr/bin/env python3
"""Which absorbed files did the commit silently drop, and which rule dropped them?

`git add` obeys .gitignore, so an absorbed tree is not what gets committed. The
working tree verified correct while the commit was missing 452 files of
`slipstream`, 53 of `zz-ref-HeliosCLI` and 2 each of two others - and no amount of
working-tree verification can see that, because the files are present on disk and
absent from the object.

This lists those files with the ignore rule responsible, so the loss is specific
rather than a count.

Usage:
    python check_ignored.py apps/slipstream [apps/other ...]
"""
import subprocess
import sys

SHARED = r"C:\Users\koosh\PhenoShared"


def sh(args):
    p = subprocess.run(args, cwd=SHARED, capture_output=True, text=True, errors="replace")
    return p.returncode, p.stdout, p.stderr


def main():
    prefixes = sys.argv[1:]
    if not prefixes:
        print(__doc__)
        return 2
    for prefix in prefixes:
        code, out, err = sh(["git", "ls-files", "--others", "--ignored",
                             "--exclude-standard", "--", prefix])
        if code != 0:
            print("%s: %s" % (prefix, err.strip()[:120]))
            continue
        files = [f for f in out.splitlines() if f.strip()]
        print("=== %s: %d ignored files ===" % (prefix, len(files)))
        if not files:
            continue
        # Ask git which rule applies to each, and group by rule. The paths go on
        # stdin: 452 of them overflow the Windows command line limit, which fails
        # with WinError 206 rather than anything helpful.
        proc = subprocess.run(["git", "check-ignore", "-v", "--no-index", "--stdin"],
                              cwd=SHARED, capture_output=True, text=True,
                              errors="replace", input="\n".join(files))
        detail = proc.stdout
        rules = {}
        for line in detail.splitlines():
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            src, _, pattern = parts[0].partition(":")
            rules.setdefault("%s:%s" % (src.split("/")[-1], pattern), []).append(parts[1])
        for rule in sorted(rules, key=lambda r: -len(rules[r])):
            examples = rules[rule]
            print("  %-46s %5d   e.g. %s"
                  % (rule, len(examples), examples[0][len(prefix):].lstrip("/")))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
