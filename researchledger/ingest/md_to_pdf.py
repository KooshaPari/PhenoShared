#!/usr/bin/env python3
"""md_to_pdf.py - render a markdown document to a styled PDF using reportlab.

Written because this machine has no LaTeX engine, no weasyprint, and cupsfilter
cannot render HTML. reportlab is available, so we build the PDF directly.

Supports the subset of markdown this project actually uses: ATX headings,
pipe tables, bullet and numbered lists, fenced code blocks, blockquotes,
inline bold/code, and horizontal rules.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------- styles
_BASE = getSampleStyleSheet()["BodyText"]

S_BODY = ParagraphStyle(
    "body", parent=_BASE, fontSize=9.2, leading=12.6, spaceAfter=5,
)
S_H1 = ParagraphStyle(
    "h1", parent=_BASE, fontSize=17, leading=20, spaceBefore=2,
    spaceAfter=7, textColor=colors.HexColor("#111111"),
)
S_H2 = ParagraphStyle(
    "h2", parent=_BASE, fontSize=12.5, leading=15, spaceBefore=12,
    spaceAfter=5, textColor=colors.HexColor("#1a1a1a"),
)
S_H3 = ParagraphStyle(
    "h3", parent=_BASE, fontSize=10.6, leading=13, spaceBefore=9,
    spaceAfter=4, textColor=colors.HexColor("#222222"),
)
S_CODE = ParagraphStyle(
    "code", parent=_BASE, fontName="Courier", fontSize=8, leading=10.4,
    leftIndent=7, spaceAfter=5, backColor=colors.HexColor("#f4f4f4"),
    borderPadding=4,
)
S_QUOTE = ParagraphStyle(
    "quote", parent=_BASE, fontSize=9.2, leading=12.6, leftIndent=10,
    textColor=colors.HexColor("#444444"), spaceAfter=5,
    borderPadding=3,
)
S_BULLET = ParagraphStyle(
    "bullet", parent=S_BODY, leftIndent=12, bulletIndent=3, spaceAfter=2.4,
)
S_CELL = ParagraphStyle("cell", parent=_BASE, fontSize=7.9, leading=9.9)
S_CELL_H = ParagraphStyle(
    "cellh", parent=S_CELL, fontName="Helvetica-Bold",
    textColor=colors.HexColor("#111111"),
)


def _inline(text: str) -> str:
    """Convert the inline markdown this project uses into reportlab markup."""
    t = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<i>\1</i>", t)
    t = re.sub(r"`([^`]+)`", r'<font face="Courier" size="8">\1</font>', t)
    return t


def _rule(width: float) -> HRFlowable:
    return HRFlowable(width=width, thickness=0.6, color=colors.HexColor("#cccccc"),
                      spaceBefore=3, spaceAfter=6)


def build_table(rows: list[list[str]], avail: float) -> Table:
    ncols = max(len(r) for r in rows)
    rows = [r + [""] * (ncols - len(r)) for r in rows]
    data = []
    for i, row in enumerate(rows):
        style = S_CELL_H if i == 0 else S_CELL
        data.append([Paragraph(_inline(c), style) for c in row])
    # weight columns by their max content length, with a floor
    weights = []
    for c in range(ncols):
        longest = max(len(r[c]) for r in rows)
        weights.append(max(longest, 8) ** 0.62)
    total = sum(weights)
    widths = [avail * (w / total) for w in weights]
    tbl = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ededed")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    return tbl


def convert(md_path: Path, pdf_path: Path, title: str) -> tuple[int, int]:
    avail = A4[0] - 2 * 16 * mm
    lines = md_path.read_text(encoding="utf-8").splitlines()

    story: list = []
    tables = 0
    headings = 0

    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()

        # fenced code
        if line.startswith("```"):
            block, i = [], i + 1
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            text = "<br/>".join(
                l.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") or "&nbsp;"
                for l in block
            )
            story.append(Paragraph(text, S_CODE))
            continue

        # table
        if line.startswith("|") and i + 1 < len(lines) and re.match(
            r"^\|[\s:|-]+\|$", lines[i + 1].strip()
        ):
            rows = []
            header = [c.strip() for c in line.strip().strip("|").split("|")]
            rows.append(header)
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            story.append(Spacer(1, 2))
            story.append(build_table(rows, avail))
            story.append(Spacer(1, 7))
            tables += 1
            continue

        # headings
        if line.startswith("# "):
            story.append(Paragraph(_inline(line[2:]), S_H1))
            story.append(_rule(avail))
            headings += 1
        elif line.startswith("## "):
            story.append(Paragraph(_inline(line[3:]), S_H2))
            headings += 1
        elif line.startswith("### "):
            story.append(Paragraph(_inline(line[4:]), S_H3))
            headings += 1
        elif line.startswith("---") and set(line) <= {"-"}:
            story.append(_rule(avail))
        elif line.startswith("> "):
            story.append(Paragraph(_inline(line[2:]), S_QUOTE))
        elif re.match(r"^\s*[-*] ", raw):
            story.append(Paragraph(_inline(re.sub(r"^\s*[-*] ", "", raw)),
                                   S_BULLET, bulletText="\u2022"))
        elif re.match(r"^\s*\d+\. ", raw):
            num = re.match(r"^\s*(\d+)\. ", raw).group(1)
            story.append(Paragraph(_inline(re.sub(r"^\s*\d+\. ", "", raw)),
                                   S_BULLET, bulletText=f"{num}."))
        elif not line.strip():
            pass
        else:
            story.append(Paragraph(_inline(line), S_BODY))
        i += 1

    doc = SimpleDocTemplate(
        str(pdf_path), pagesize=A4,
        leftMargin=16 * mm, rightMargin=16 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
        title=title, author="jcode agent",
    )

    def _footer(canv, d):
        canv.saveState()
        canv.setFont("Helvetica", 7)
        canv.setFillColor(colors.HexColor("#888888"))
        canv.drawString(16 * mm, 9 * mm, title)
        canv.drawRightString(A4[0] - 16 * mm, 9 * mm, f"page {d.page}")
        canv.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return headings, tables


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("usage: md_to_pdf.py <input.md> <output.pdf> [title]")
    src = Path(sys.argv[1]).expanduser()
    dst = Path(sys.argv[2]).expanduser()
    ttl = sys.argv[3] if len(sys.argv) > 3 else src.stem
    h, t = convert(src, dst, ttl)
    print(f"wrote {dst} ({dst.stat().st_size} bytes; {h} headings, {t} tables)")
