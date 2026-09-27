"""Split phenotype-canonicalization SOURCE-INDEX.md to satisfy the 500-line limit.

The index had grown to 589 lines. The primary file keeps the GitHub-source
entries (G01-G23); the appendix file gains the library/instruction/web-source
entries (L01, U01, E01, W01-W20) ahead of the W21-W24 entries it already held.

No entry content is altered: lines are only relocated.
"""

import sys

ROOT = "/Users/kooshapari/CodeProjects/docs/phenotype-canonicalization"
INDEX = f"{ROOT}/SOURCE-INDEX.md"
DETAIL = f"{ROOT}/SOURCE-INDEX-DETAIL.md"

# First line index (1-based) of the appendix block in SOURCE-INDEX.md.
SPLIT_AT = 342


def main() -> int:
    index_lines = open(INDEX).read().split("\n")
    detail_lines = open(DETAIL).read().split("\n")

    main_body = index_lines[: SPLIT_AT - 1]
    moved = index_lines[SPLIT_AT - 1 :]

    footer = [
        "---",
        "",
        "## Appendix",
        "",
        "Library documents, user instructions, verification evidence and web",
        "sources (L01, U01, E01, W01-W24) plus the Liveness Status table are in",
        "[`SOURCE-INDEX-DETAIL.md`](SOURCE-INDEX-DETAIL.md).",
        "",
    ]

    new_detail_header = [
        "# Source Index — Appendix (L01, U01, E01, W01-W24, Liveness Status)",
        "",
        "This file is an appendix to [`SOURCE-INDEX.md`](SOURCE-INDEX.md). It"
        " carries the library-document, user-instruction, verification-evidence"
        " and web-source entries plus the full Liveness Status table. No"
        " information from the original source index has been omitted.",
        "",
    ]
    # Drop the appendix file's old one-line header + blank note lines (first 3).
    detail_rest = detail_lines[3:]

    with open(INDEX, "w") as handle:
        handle.write("\n".join(main_body + footer))
    with open(DETAIL, "w") as handle:
        handle.write("\n".join(new_detail_header + moved + detail_rest))

    print(f"index entries kept: lines 1-{SPLIT_AT - 1}")
    print(f"appendix lines moved: {len(moved)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
