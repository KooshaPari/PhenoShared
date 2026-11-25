#!/usr/bin/env python3
"""Audit System CLI -- evaluate products against the rubric.

Usage:
    python eval.py run [--product NAME] [--all] [--output DIR]
    python eval.py score [--product NAME]
    python eval.py dashboard [--input DIR] [--output FILE]
    python eval.py list
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE  # eval.py is at repo root
RUBRIC_PATH = REPO / "rubric" / "rubric-v1.json"
SCORECARDS_DIR = REPO / "scorecards"
OUTPUT_DIR = REPO / "output"


def load_rubric():
    data = json.loads(RUBRIC_PATH.read_bytes())
    return data["criteria"]


def discover_products():
    """Find all scorecard files and extract product names."""
    products = {}
    if not SCORECARDS_DIR.exists():
        return products
    for f in sorted(SCORECARDS_DIR.glob("*-audit.json")):
        name = f.stem.replace("-audit", "")
        products[name] = f
    return products


def load_card(path):
    data = json.loads(path.read_bytes())
    return data.get("criteria", data) if isinstance(data, dict) else data


def aggregate_card_statuses(mappings, rubric_criteria):
    """Aggregate card statuses per unique qualified key (most conservative)."""
    STATUS_MAP = {"satisfied": "satisfied", "partial": "unsatisfied", "missing": "unsatisfied"}
    rubric_index = {}
    for c in rubric_criteria:
        rubric_index.setdefault(c["id"], []).append(
            {"source": c["source"], "domain": c["domain"]}
        )

    qkey_agg = {}
    for m in mappings:
        cid = m["card_id"]
        resolved_source = m.get("resolved_source", "unknown")
        domain = "unknown"
        for r in rubric_criteria:
            if r["id"] == cid and r["source"] == resolved_source:
                domain = r["domain"]
                break
        if domain == "unknown":
            matches = rubric_index.get(cid, [])
            if matches:
                domain = matches[0]["domain"]

        qkey = f"{resolved_source}:{domain}:{cid}"
        mapped_status = STATUS_MAP.get(m.get("card_status", "missing"), "unsatisfied")
        if qkey not in qkey_agg:
            qkey_agg[qkey] = {"source": resolved_source, "domain": domain, "id": cid, "statuses": set()}
        qkey_agg[qkey]["statuses"].add(mapped_status)

    rows = []
    for qkey, info in sorted(qkey_agg.items()):
        worst = "unsatisfied" if "unsatisfied" in info["statuses"] else "satisfied"
        rows.append({
            "source": info["source"],
            "domain": info["domain"],
            "id": info["id"],
            "status": worst,
            "subject": "substrate",
        })
    return rows


def simple_evaluate(rubric_rows, audit_rows):
    """Run a simplified evaluation (same logic as dry_run.py but inline)."""
    rubric_keys = set()
    for r in rubric_rows:
        key = f"{r['source']}:{r['domain']}:{r.get('legacy_id', r.get('id', ''))}"
        rubric_keys.add(key)

    assessed = 0
    failed = 0
    passed = 0
    partial = 0
    for a in audit_rows:
        key = f"{a['source']}:{a['domain']}:{a.get('legacy_id', a.get('id', ''))}"
        if key in rubric_keys:
            assessed += 1
            status = a["status"]
            if status == "unsatisfied":
                failed += 1
            elif status == "partial":
                partial += 1
            else:
                passed += 1

    return {
        "assessed": assessed,
        "failed": failed,
        "passed": passed,
        "partial": partial,
        "pass_rate": round(passed / assessed * 100, 1) if assessed > 0 else 0,
        "partial_rate": round(partial / assessed * 100, 1) if assessed > 0 else 0,
    }


def load_audit_scorecard(name):
    """Load a rich audit scorecard if available (has source+domain fields)."""
    for pattern in [f"{name}-audit.json", f"{name.lower()}-audit.json"]:
        path = SCORECARDS_DIR / pattern
        if path.exists():
            data = json.loads(path.read_bytes())
            criteria = data.get("criteria", [])
            if criteria and "source" in criteria[0] and "domain" in criteria[0]:
                return criteria
    return None


def evaluate_with_audit(product_name, audit_criteria, rubric_criteria):
    """Evaluate a product using its rich audit scorecard directly."""
    STATUS_MAP = {"satisfied": "satisfied", "partial": "partial", "missing": "unsatisfied"}
    rubric_by_id_domain = {}
    for c in rubric_criteria:
        key = (c["id"], c["source"], c["domain"])
        rubric_by_id_domain[key] = c

    audit_rows = []
    for c in audit_criteria:
        cid = c["id"]
        source = c.get("source", "unknown")
        domain = c.get("domain", "unknown")
        status = STATUS_MAP.get(c.get("status", "missing"), "unsatisfied")
        audit_rows.append({
            "id": cid, "source": source, "domain": domain, "status": status
        })

    rubric_subset = []
    for a in audit_rows:
        key = (a["id"], a["source"], a["domain"])
        if key in rubric_by_id_domain:
            rubric_subset.append(rubric_by_id_domain[key])

    return simple_evaluate(rubric_subset, audit_rows)


def cmd_run(args):
    """Run evaluation for one or all products."""
    rubric_criteria = load_rubric()
    products = discover_products()

    if not products:
        print("No scorecards found in", SCORECARDS_DIR)
        return 1

    if args.product:
        if args.product not in products:
            print(f"Product not found: {args.product}")
            print(f"Available: {', '.join(sorted(products))}")
            return 1
        targets = {args.product: products[args.product]}
    else:
        targets = products

    # Load resolved mapping if available
    resolved_path = REPO / "audits" / "2026-09-07" / "dry_run" / "RESOLVED-MAPPING.json"
    resolved = {}
    if resolved_path.exists():
        resolved = json.loads(resolved_path.read_bytes())

    results = {}
    for name, card_path in sorted(targets.items()):
        # Try rich audit scorecard first (has source+domain per criterion)
        audit_criteria = load_audit_scorecard(name)
        if audit_criteria:
            result = evaluate_with_audit(name, audit_criteria, rubric_criteria)
        else:
            # Fall back to resolved mapping approach
            card_criteria = load_card(card_path)

            if name in resolved.get("cards", {}):
                mappings = resolved["cards"][name]
            else:
                rubric_by_id = defaultdict(list)
                for c in rubric_criteria:
                    rubric_by_id[c["id"]].append(c)
                mappings = []
                for cr in card_criteria:
                    cid = cr.get("id", "")
                    matches = rubric_by_id.get(cid, [])
                    source = matches[0]["source"] if matches else "unknown"
                    domain = matches[0]["domain"] if matches else "unknown"
                    mappings.append({
                        "card_id": cid,
                        "card_status": cr.get("status", "missing"),
                        "resolved_source": source,
                        "rubric_domain": domain,
                        "match_type": "auto" if matches else "missing",
                    })

            audit_rows = aggregate_card_statuses(mappings, rubric_criteria)

            audit_keys = set()
            for a in audit_rows:
                audit_keys.add((a["source"], a["domain"], a.get("id", a.get("legacy_id", ""))))
            rubric_subset = [
                r for r in rubric_criteria
                if (r["source"], r["domain"], r["id"]) in audit_keys
            ]

            result = simple_evaluate(rubric_subset, audit_rows)

        result["product"] = name
        result["source"] = "audit" if audit_criteria else "mapping"
        result["card_rows"] = len(audit_criteria) if audit_criteria else len(load_card(card_path))
        result["unique_criteria"] = result["assessed"]
        results[name] = result

    # Print results
    print(f"\n{'Product':<25} {'Source':>7} {'Criteria':>8} {'Passed':>8} {'Partial':>8} {'Failed':>8} {'Rate':>8}")
    print("-" * 82)
    for name in sorted(results):
        r = results[name]
        partial = r.get("partial", 0)
        src = r.get("source", "?")[:7]
        print(f"{name:<25} {src:>7} {r['assessed']:>8} {r['passed']:>8} {partial:>8} {r['failed']:>8} {r['pass_rate']:>7.1f}%")

    # Save output
    out_dir = Path(args.output) if args.output else OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "evaluation-results.json"
    out_file.write_bytes(json.dumps({
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "rubric_criteria_count": len(rubric_criteria),
        "products": results,
    }, indent=2).encode())
    print(f"\nResults saved to {out_file}")
    return 0


def cmd_dashboard(args):
    """Generate HTML dashboard."""
    # Find latest evaluation results
    results_file = Path(args.input) if args.input else OUTPUT_DIR / "evaluation-results.json"
    if not results_file.exists():
        print(f"No results found at {results_file}")
        print("Run `python eval.py run` first.")
        return 1

    data = json.loads(results_file.read_bytes())
    products = data.get("products", {})

    # Sort by pass rate
    sorted_products = sorted(products.items(), key=lambda x: x[1]["pass_rate"])

    # Build HTML
    rows_html = ""
    for name, r in sorted_products:
        rate = r["pass_rate"]
        partial = r.get("partial", 0)
        source = r.get("source", "?")
        color = "#ef4444" if rate < 50 else "#f59e0b" if rate < 80 else "#22c55e"
        bar_width = rate
        partial_width = partial / r['assessed'] * 100 if r.get('assessed', 0) > 0 else 0
        src_color = "#60a5fa" if source == "audit" else "#94a3b8"
        rows_html += f"""
        <tr>
            <td class="font-mono font-bold">{name}</td>
            <td class="text-right"><span style="color:{src_color}">{source}</span></td>
            <td class="text-right">{r['assessed']}</td>
            <td class="text-right text-green">{r['passed']}</td>
            <td class="text-right" style="color:#fbbf24">{partial}</td>
            <td class="text-right text-red">{r['failed']}</td>
            <td>
                <div class="bar-bg">
                    <div class="bar-fill" style="width:{bar_width}%;background:{color}"></div>
                    <div class="bar-fill" style="width:{partial_width}%;background:#fbbf24;margin-left:-{partial_width}%;opacity:0.5"></div>
                </div>
                <span class="rate">{rate:.1f}%</span>
            </td>
        </tr>"""

    total_criteria = data.get("rubric_criteria_count", 0)
    total_products = len(products)
    avg_rate = sum(r["pass_rate"] for r in products.values()) / total_products if total_products else 0

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Audit Dashboard</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: -apple-system, system-ui, sans-serif; background:#0f172a; color:#e2e8f0; padding:2rem; }}
  h1 {{ font-size:1.5rem; margin-bottom:0.5rem; }}
  .meta {{ color:#94a3b8; margin-bottom:2rem; font-size:0.875rem; }}
  .summary {{ display:flex; gap:2rem; margin-bottom:2rem; }}
  .card {{ background:#1e293b; border-radius:8px; padding:1.5rem; min-width:180px; }}
  .card .label {{ color:#94a3b8; font-size:0.75rem; text-transform:uppercase; }}
  .card .value {{ font-size:2rem; font-weight:bold; margin-top:0.25rem; }}
  table {{ width:100%; border-collapse:collapse; }}
  th {{ text-align:left; padding:0.75rem; border-bottom:2px solid #334155; color:#94a3b8; font-size:0.75rem; text-transform:uppercase; }}
  td {{ padding:0.75rem; border-bottom:1px solid #1e293b; }}
  .text-right {{ text-align:right; }}
  .text-green {{ color:#22c55e; }}
  .text-red {{ color:#ef4444; }}
  .font-mono {{ font-family:monospace; }}
  .font-bold {{ font-weight:bold; }}
  .bar-bg {{ background:#334155; border-radius:4px; height:8px; width:120px; display:inline-block; vertical-align:middle; }}
  .bar-fill {{ height:100%; border-radius:4px; }}
  .rate {{ margin-left:0.5rem; font-size:0.875rem; }}
</style>
</head>
<body>
<h1>Audit Dashboard</h1>
<div class="meta">Generated {data.get('evaluated_at', 'unknown')} | Rubric v1 ({total_criteria} criteria)</div>
<div class="summary">
  <div class="card"><div class="label">Products</div><div class="value">{total_products}</div></div>
  <div class="card"><div class="label">Rubric Criteria</div><div class="value">{total_criteria}</div></div>
  <div class="card"><div class="label">Avg Pass Rate</div><div class="value">{avg_rate:.1f}%</div></div>
</div>
<table>
<thead><tr><th>Product</th><th class="text-right">Source</th><th class="text-right">Criteria</th><th class="text-right">Passed</th><th class="text-right">Partial</th><th class="text-right">Failed</th><th>Pass Rate</th></tr></thead>
<tbody>{rows_html}</tbody>
</table>
</body>
</html>"""

    out_file = Path(args.output) if args.output else OUTPUT_DIR / "dashboard.html"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_bytes(html.encode())
    print(f"Dashboard written to {out_file}")
    return 0


def cmd_list(args):
    """List available products."""
    products = discover_products()
    if not products:
        print("No scorecards found.")
        return 1
    print(f"\nAvailable products ({len(products)}):")
    for name in sorted(products):
        card = load_card(products[name])
        print(f"  {name:<25} {len(card)} criteria")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Audit System CLI")
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Run evaluation")
    run_p.add_argument("--product", "-p", help="Product name (default: all)")
    run_p.add_argument("--output", "-o", help="Output directory")

    dash_p = sub.add_parser("dashboard", help="Generate HTML dashboard")
    dash_p.add_argument("--input", "-i", help="Evaluation results JSON")
    dash_p.add_argument("--output", "-o", help="Output HTML file")

    sub.add_parser("list", help="List available products")

    args = parser.parse_args()
    if args.command == "run":
        return cmd_run(args)
    elif args.command == "dashboard":
        return cmd_dashboard(args)
    elif args.command == "list":
        return cmd_list(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
