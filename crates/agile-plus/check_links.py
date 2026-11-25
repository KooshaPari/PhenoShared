"""Check all internal markdown links in docs/ directory."""

import os
import re
import sys

DOCS_DIR = r"C:\Users\koosh\Dev\AgilePlus\docs"


def extract_links(filepath):
    """Extract all internal markdown links from a file."""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    links = []
    # Pattern: [text](url)
    pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    for m in pattern.finditer(content):
        url = m.group(2).strip()
        # Skip external links, anchors, mailto
        if (
            url.startswith("http://")
            or url.startswith("https://")
            or url.startswith("#")
            or url.startswith("mailto:")
        ):
            continue
        links.append((m.group(1), url, m.start()))

    return links


def resolve_target(source_file, link_url):
    """Resolve a relative link URL to an absolute filesystem path."""
    source_dir = os.path.dirname(os.path.abspath(source_file))

    # Strip fragment/anchor
    url = link_url.split("#")[0]

    # Remove any query string
    url = url.split("?")[0]

    if not url.strip():
        return None

    if os.path.isabs(url):
        target = os.path.join(r"C:\Users\koosh\Dev\AgilePlus", url.lstrip("/\\"))
    else:
        target = os.path.normpath(os.path.join(source_dir, url))

    return target


def main():
    results = []

    for root, dirs, files in os.walk(DOCS_DIR):
        for f in files:
            if f.endswith(".md"):
                filepath = os.path.join(root, f)
                relpath = os.path.relpath(filepath, r"C:\Users\koosh\Dev\AgilePlus")
                links = extract_links(filepath)

                for text, url, pos in links:
                    target = resolve_target(filepath, url)
                    if target and not os.path.exists(target):
                        results.append((relpath, url, text, target))

    # Summary
    print(f"Found {len(results)} broken internal links:")
    print()
    for src, url, text, target in sorted(results):
        print(f"  [{src}]")
        print(f"    Link: [{text}]({url})")
        print(f"    Missing: {target}")
        print()

    return len(results)


if __name__ == "__main__":
    sys.exit(main())
