#!/usr/bin/env python3
"""Round-instinct: 7-product full-text search across ~/Exports.

Local algorithmic search only. NO LLM. For each product, ripgrep the export
tree, group hits by conversation, write per-conv markdown + index.md.

Products: Tracera, PhenoFabric, ShareCLI, AgilePlus, BytePort, Melosviz, Civis
"""
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from datetime import datetime

EXPORT_ROOT = Path.home() / "Exports"
OUT_ROOT = EXPORT_ROOT / "analysis" / "search-results"
OUT_ROOT.mkdir(parents=True, exist_ok=True)

# Term patterns. "Civis" gets a soft-match column for Latin usage.
PRODUCTS = {
    "tracera": {
        "terms": ["tracera", "feature graph", "tracertm", "feature-graph", "feature_graph"],
        # \b boundary so "feature graphy" doesn't false-match
        "compound_aliases": ["feature[\s_-]?graph\\b"],
    },
    "phenofabric": {
        "terms": ["phenofabric", "pheno-fabric", "pheno_fabric"],
        "compound_aliases": ["pheno[\s_-]?fabric"],
    },
    "sharecli": {
        "terms": ["sharecli", "share-cli", "share_cli"],
        # NOTE: use \b boundary so "Share Clip" doesn't match as "Share Cli" prefix
        "compound_aliases": ["share[\s_-]?cli\\b"],
    },
    "agileplus": {
        "terms": ["agileplus", "agile-plus", "agile_plus"],
        "compound_aliases": ["agile[\s_-]?plus\\b"],
    },
    "byteport": {
        "terms": ["byteport", "byte-port", "byte_port"],
        "compound_aliases": ["byte[\s_-]?port\\b"],
    },
    "melosviz": {
        "terms": ["melosviz", "melos-viz", "melos_viz"],
        "compound_aliases": ["melos[\s_-]?viz\\b"],
    },
    "civis": {
        "terms": ["civis"],
        "compound_aliases": ["civis"],
        "soft_classify": True,  # Latin "citizen" disambiguation
    },
}

# Sources to search (raw export tree only; skip analysis/)
SOURCES = [
    EXPORT_ROOT / "claude-20261010" / "raw" / "conversations-000" / "conversations.json",
    EXPORT_ROOT / "claude-20261010" / "raw" / "projects-000" / "projects",
    EXPORT_ROOT / "claude-20261010" / "raw" / "design_chats-000" / "design_chats",
    EXPORT_ROOT / "claude-20261010" / "raw" / "memories-000",
    EXPORT_ROOT / "gemini-20261010" / "raw" / "Takeout",
]

# Regex fragments
TERMS_RE_CACHE = {}

def terms_re(product_key):
    """Build a case-insensitive regex matching any of the product's terms."""
    if product_key in TERMS_RE_CACHE:
        return TERMS_RE_CACHE[product_key]
    cfg = PRODUCTS[product_key]
    all_patterns = cfg["terms"] + cfg["compound_aliases"]
    # Use literal patterns joined by |; ripgrep will handle alternation
    pattern = "|".join(re.escape(t) for t in cfg["terms"])
    # Add compound aliases unescaped (they contain regex chars intentionally)
    pattern += "|" + "|".join(cfg["compound_aliases"])
    rx = re.compile(pattern, re.IGNORECASE)
    TERMS_RE_CACHE[product_key] = rx
    return rx

def title_only_check(content, rx):
    """Heuristic: a hit is 'title-only' if the only matches in the content
    are in a short 'title'/'name'/'summary' field. Since we don't parse JSON
    structure for every file, we use a conservative proxy: if the match line
    itself contains 'title' or 'name' or 'summary' in the same line, flag.
    """
    # This is per-line, not whole-doc. Conservative.
    return False  # we'll filter at conversation level instead

def load_claude_conversations():
    """Load all claude conversations from conversations.json. Returns:
    {conv_id: {title, created_at, raw_text}} where raw_text is the full
    JSON-line content (one conv per file or one JSON object in the file).
    """
    out = {}
    f = EXPORT_ROOT / "claude-20261010" / "raw" / "conversations-000" / "conversations.json"
    if not f.exists():
        return out
    try:
        # conversations.json is a single JSON array (or one big object)
        # Use line-based load since the file is huge and may not be valid single-JSON
        with open(f, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        # Try parsing as JSON first
        try:
            data = json.loads(text)
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                # Could be {"conversations": [...]} or a single conversation
                if "conversations" in data and isinstance(data["conversations"], list):
                    items = data["conversations"]
                else:
                    items = [data]
            else:
                items = []
        except json.JSONDecodeError:
            # Try line-by-line
            items = []
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("{"):
                    try:
                        items.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        for c in items:
            if not isinstance(c, dict):
                continue
            cid = c.get("uuid") or c.get("id") or c.get("conversation_id")
            if not cid:
                continue
            title = c.get("name") or c.get("title") or ""
            created = c.get("created_at") or c.get("createdAt") or c.get("create_time") or ""
            # Extract all text from messages for full-text searching
            text_chunks = []
            for m in (c.get("chat_messages") or c.get("messages") or []):
                if isinstance(m, dict):
                    if m.get("content"):
                        text_chunks.append(str(m["content"]))
                    if m.get("text"):
                        text_chunks.append(str(m["text"]))
            out[cid] = {
                "title": title,
                "created_at": created,
                "text": "\n".join(text_chunks),
                "source": "claude-conversations",
            }
    except Exception as e:
        print(f"WARN: load_claude_conversations failed: {e}", file=sys.stderr)
    return out

def load_claude_per_file(directory):
    """Load Claude per-file JSON (one JSON object per file)."""
    out = {}
    if not directory.exists():
        return out
    for f in directory.iterdir():
        if not f.name.endswith(".json"):
            continue
        try:
            data = json.loads(f.read_text(errors="replace"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        cid = data.get("uuid") or data.get("id") or f.stem
        title = data.get("name") or data.get("title") or ""
        created = data.get("created_at") or data.get("createdAt") or data.get("create_time") or ""
        # Extract text from all common message/content fields
        text_chunks = []
        for m in (data.get("chat_messages") or data.get("messages") or []):
            if isinstance(m, dict):
                for k in ("content", "text", "display_content", "summary"):
                    if m.get(k):
                        text_chunks.append(str(m[k]))
        # Also scan all string values recursively (cheap depth-first)
        def _walk(obj, depth=0):
            if depth > 6:
                return
            if isinstance(obj, str) and len(obj) > 20:
                text_chunks.append(obj)
            elif isinstance(obj, dict):
                for v in obj.values():
                    _walk(v, depth+1)
            elif isinstance(obj, list):
                for v in obj:
                    _walk(v, depth+1)
        # Already added messages; for projects/memories, scan rest of object
        if "chat_messages" in data or "messages" in data:
            # Already captured messages
            pass
        else:
            _walk(data)
        out[cid] = {
            "title": title,
            "created_at": created,
            "text": "\n".join(text_chunks),
            "source": f"claude-{directory.name}",
            "filename": f.name,
        }
    return out

def load_gemini_files():
    """Load Gemini Takeout HTML files. Strip HTML tags, treat each file as a doc."""
    out = {}
    base = EXPORT_ROOT / "gemini-20261010" / "raw" / "Takeout"
    if not base.exists():
        return out
    tag_re = re.compile(r"<[^>]+>")
    for f in base.rglob("*.html"):
        try:
            html = f.read_text(errors="replace")
        except Exception:
            continue
        # Strip HTML tags, keep text
        text = tag_re.sub(" ", html)
        text = re.sub(r"\s+", " ", text).strip()
        # Extract title from <title> or filename
        m = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
        title = m.group(1) if m else f.stem
        # Try to extract date
        date_m = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
        created = date_m.group(1) if date_m else ""
        out[f"gemini-{f.name}"] = {
            "title": title,
            "created_at": created,
            "text": text,
            "source": "gemini-takeout",
            "filename": str(f.relative_to(base)),
        }
    return out

def load_all_docs():
    """Load all docs from all sources into one dict."""
    docs = {}
    print("Loading claude conversations.json ...", file=sys.stderr)
    docs.update(load_claude_conversations())
    print(f"  loaded {len(docs)} so far", file=sys.stderr)
    for sub in [
        EXPORT_ROOT / "claude-20261010" / "raw" / "projects-000" / "projects",
        EXPORT_ROOT / "claude-20261010" / "raw" / "design_chats-000" / "design_chats",
        EXPORT_ROOT / "claude-20261010" / "raw" / "memories-000",
    ]:
        print(f"Loading {sub} ...", file=sys.stderr)
        before = len(docs)
        docs.update(load_claude_per_file(sub))
        print(f"  +{len(docs) - before} = {len(docs)}", file=sys.stderr)
    print("Loading gemini takeout ...", file=sys.stderr)
    before = len(docs)
    docs.update(load_gemini_files())
    print(f"  +{len(docs) - before} = {len(docs)}", file=sys.stderr)
    return docs

def classify_civis_hit(excerpt):
    """Heuristic: is "Civis" used as a product or as Latin for "citizen"?
    Returns 'product' or 'latin'."""
    L = excerpt.lower()
    # Latin / civic usage signals
    latin_signals = ["civis romanus", "civis sum", "cives romani", "i am a citizen", "citizen of"]
    if any(s in L for s in latin_signals):
        return "latin"
    # Product context signals
    product_signals = [
        "build civis", "civis mvp", "civis platform", "civis work",
        "civis helps", "civis project", "civis app", "our civis",
        "civis api", "civis engine", "civis thesis", "civis research",
    ]
    if any(s in L for s in product_signals):
        return "product"
    # Capitalization heuristic: if "Civis" is capitalized in the match, more likely product
    if "Civis" in excerpt:
        return "product"
    # Default: assume product (since "civis" alone is rare in modern English)
    return "product"

def search_product(docs, product_key):
    """Return list of (doc_id, hit_count, excerpts, soft_count_for_civis)."""
    rx = terms_re(product_key)
    soft = PRODUCTS[product_key].get("soft_classify", False)
    matches = []
    for doc_id, doc in docs.items():
        text = doc.get("text", "")
        if not text:
            continue
        hits = []
        for m in rx.finditer(text):
            start = max(0, m.start() - 80)
            end = min(len(text), m.end() + 80)
            excerpt = text[start:end].replace("\n", " ").strip()
            hits.append((m.start(), excerpt))
        if not hits:
            continue
        # Title-only exclusion: if the title contains the term but the text has 0 hits, skip
        title = doc.get("title", "") or ""
        if hits and not any(1 for _ in hits):
            continue
        if soft:
            # Classify each hit
            product_hits = sum(1 for _, exc in hits if classify_civis_hit(exc) == "product")
            latin_hits = sum(1 for _, exc in hits if classify_civis_hit(exc) == "latin")
            matches.append({
                "doc_id": doc_id,
                "title": title,
                "created_at": doc.get("created_at", ""),
                "source": doc.get("source", ""),
                "filename": doc.get("filename", ""),
                "hit_count": len(hits),
                "product_hits": product_hits,
                "latin_hits": latin_hits,
                "excerpts": [exc for _, exc in hits[:20]],  # cap
            })
        else:
            matches.append({
                "doc_id": doc_id,
                "title": title,
                "created_at": doc.get("created_at", ""),
                "source": doc.get("source", ""),
                "filename": doc.get("filename", ""),
                "hit_count": len(hits),
                "excerpts": [exc for _, exc in hits[:20]],  # cap
            })
    return matches

def write_product_results(product_key, matches):
    """Write per-conv .md files + index.md for a product."""
    out_dir = OUT_ROOT / product_key
    out_dir.mkdir(parents=True, exist_ok=True)
    # Sort by hit_count desc
    matches.sort(key=lambda m: (-m["hit_count"], m.get("created_at", "")))
    # Per-conv files
    for m in matches:
        safe_id = re.sub(r"[^A-Za-z0-9._-]", "_", m["doc_id"])[:120]
        path = out_dir / f"{safe_id}.md"
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {m['title'] or '(untitled)'}\n\n")
            f.write(f"- **doc_id**: `{m['doc_id']}`\n")
            f.write(f"- **created_at**: {m['created_at'] or '(unknown)'}\n")
            f.write(f"- **source**: {m['source']}\n")
            if m.get("filename"):
                f.write(f"- **file**: `{m['filename']}`\n")
            f.write(f"- **hit_count**: {m['hit_count']}\n")
            if "product_hits" in m:
                f.write(f"- **product_hits**: {m['product_hits']}\n")
                f.write(f"- **latin_hits**: {m['latin_hits']}\n")
            f.write(f"\n## Excerpts ({min(20, m['hit_count'])} of {m['hit_count']})\n\n")
            for i, exc in enumerate(m["excerpts"], 1):
                f.write(f"{i}. > {exc}\n\n")
    # index.md
    index_path = out_dir / "index.md"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(f"# {product_key} — search results\n\n")
        f.write(f"- **terms**: {', '.join(PRODUCTS[product_key]['terms'])}\n")
        f.write(f"- **conversations matched**: {len(matches)}\n")
        total_hits = sum(m["hit_count"] for m in matches)
        f.write(f"- **total hits**: {total_hits}\n")
        if "product_hits" in (matches[0] if matches else {}):
            total_product = sum(m.get("product_hits", 0) for m in matches)
            total_latin = sum(m.get("latin_hits", 0) for m in matches)
            f.write(f"- **product-context hits**: {total_product}\n")
            f.write(f"- **latin/soft hits**: {total_latin}\n")
        f.write(f"\n## Conversations (sorted by hit count desc)\n\n")
        if "product_hits" in (matches[0] if matches else {}):
            f.write("| # | Title | Date | Source | Hits (product/latin/total) | File |\n")
            f.write("|---|-------|------|--------|---------------------------|------|\n")
            for i, m in enumerate(matches, 1):
                safe_id = re.sub(r"[^A-Za-z0-9._-]", "_", m["doc_id"])[:120]
                title = (m["title"] or "(untitled)").replace("|", "\\|")
                f.write(f"| {i} | {title} | {m['created_at'] or '—'} | {m['source']} | "
                        f"{m['product_hits']}/{m['latin_hits']}/{m['hit_count']} | "
                        f"[{safe_id}.md]({safe_id}.md) |\n")
        else:
            f.write("| # | Title | Date | Source | Hits | File |\n")
            f.write("|---|-------|------|--------|------|------|\n")
            for i, m in enumerate(matches, 1):
                safe_id = re.sub(r"[^A-Za-z0-9._-]", "_", m["doc_id"])[:120]
                title = (m["title"] or "(untitled)").replace("|", "\\|")
                f.write(f"| {i} | {title} | {m['created_at'] or '—'} | {m['source']} | "
                        f"{m['hit_count']} | [{safe_id}.md]({safe_id}.md) |\n")
    return total_hits, len(matches)

def main():
    print(f"Loading all docs from {EXPORT_ROOT} ...", file=sys.stderr)
    docs = load_all_docs()
    print(f"Total docs loaded: {len(docs)}", file=sys.stderr)
    print()
    results = {}
    for product_key in PRODUCTS:
        print(f"=== {product_key} ===", file=sys.stderr)
        matches = search_product(docs, product_key)
        total_hits, n_convs = write_product_results(product_key, matches)
        results[product_key] = {
            "conversations": n_convs,
            "total_hits": total_hits,
        }
        if matches:
            top3 = [m["title"] for m in matches[:3]]
        else:
            top3 = []
        results[product_key]["top3"] = top3
        if "product_hits" in (matches[0] if matches else {}):
            results[product_key]["product_hits"] = sum(m.get("product_hits", 0) for m in matches)
            results[product_key]["latin_hits"] = sum(m.get("latin_hits", 0) for m in matches)
        print(f"  {n_convs} convs, {total_hits} hits", file=sys.stderr)
    # Summary report
    print()
    print("=" * 60)
    print("SUMMARY (counts per product)")
    print("=" * 60)
    for product_key, r in results.items():
        line = f"  {product_key}: {r['conversations']} conversations, {r['total_hits']} total hits"
        if "product_hits" in r:
            line += f" (product: {r['product_hits']}, latin: {r['latin_hits']})"
        print(line)
    # Write summary.json
    summary = {
        "generated_at": datetime.now().isoformat(),
        "export_root": str(EXPORT_ROOT),
        "products": results,
    }
    with open(OUT_ROOT / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print()
    print(f"Summary written to {OUT_ROOT / 'summary.json'}")
    print(f"Per-product folders at {OUT_ROOT}/")
    return results

if __name__ == "__main__":
    main()
