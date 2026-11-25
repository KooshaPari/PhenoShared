#!/usr/bin/env python3
"""
verify_contract.py — feynman's reference verifier for EvaluationReport v0.1

Usage:
    python scripts/verify_contract.py                          # check that the
                                                               # embedded schema
                                                               # parses + hashes
    python scripts/verify_contract.py path/to/artifact.json    # verify an
                                                               # artifact against
                                                               # the contract
"""

import hashlib
import json
import re
import sys
from pathlib import Path

from bench.contracts.cell_metrics import (
    effective_pass_at_1,
    suite_gen_ok_mean,
    task_gen_ok,
)

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "bench/contracts/EVAL_RESULT_CANONICALIZATION.md"
CELL_METRICS_DOC = ROOT / "bench/contracts/CELL_PASS_METRICS.md"

# Enums — must stay byte-identical with the schema in EVAL_RESULT_CANONICALIZATION.md
ALLOWED_SUITES = frozenset(
    {
        "mmlu-pro",
        "gpqa-diamond",
        "aime",
        "arc-agi-2",
        "livecodebench",
        "aider-polyglot",
        "swe-bench",
        "swe-bench-pro",
        "bfcl",
        "terminal-bench",
    }
)
ALLOWED_STATUSES = frozenset({"ok", "wrong", "error", "skipped"})
ALLOWED_JUDGES = frozenset({"deterministic", "regex", "llm"})
ALLOWED_VARIANTS = frozenset({"stock", "ours"})
ALLOWED_JUDGE_MODES = frozenset({"deterministic", "llm"})
ALLOWED_ENERGY = frozenset({"none", "m1_pmu", "nvidia_smi"})
ALLOWED_EVIDENCE = frozenset(
    {"live verified", "historical", "reported", "inferred", "unknown"}
)
ALLOWED_WINNERS = frozenset({"stock", "ours", "tie"})


def _sort(obj):
    if isinstance(obj, dict):
        return {k: _sort(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [_sort(x) for x in obj]
    return obj


def canonical_bytes(obj):
    return json.dumps(
        _sort(obj),
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_hex(obj):
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def load_embedded_schema():
    text = DOC.read_text(encoding="utf-8")
    m = re.search(r"```json\n(.*?)\n```", text, flags=re.DOTALL)
    if not m:
        raise RuntimeError("No JSON fence block in CANONICALIZATION doc")
    return json.loads(m.group(1))


def declared_schema_hash():
    text = DOC.read_text(encoding="utf-8")
    m = re.search(r"SCHEMA_HASH = ([a-f0-9]{64})", text)
    if not m:
        raise RuntimeError("No SCHEMA_HASH = ... line in CANONICALIZATION doc")
    return m.group(1)


def verify_self():
    """Confirm embedded schema parses and matches declared SCHEMA_HASH."""
    schema = load_embedded_schema()
    declared = declared_schema_hash()
    computed = sha256_hex(schema)
    return {
        "schema_parses": True,
        "schema_bytes": len(canonical_bytes(schema)),
        "schema_required": schema["required"],
        "schema_top_level_props": list(schema["properties"].keys()),
        "SCHEMA_HASH_declared": declared,
        "SCHEMA_HASH_computed": computed,
        "SCHEMA_HASH_match": declared == computed,
    }


def verify_artifact(path):
    """Accept or reject an EvaluationReport artifact."""
    schema = load_embedded_schema()
    schema_hash = sha256_hex(schema)

    try:
        artifact = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        return False, f"artifact JSON load failed: {e}"

    # C1
    if artifact.get("contract_version") != "0.1":
        return False, f"C1 contract_version={artifact.get('contract_version')} != '0.1'"

    # E5–E9 — run-level enums
    run = artifact.get("run", {})
    if run.get("variant") not in ALLOWED_VARIANTS:
        return False, f"E5 run.variant={run.get('variant')!r} not in {ALLOWED_VARIANTS}"
    if run.get("judge_mode") not in ALLOWED_JUDGE_MODES:
        return (
            False,
            f"E6 run.judge_mode={run.get('judge_mode')!r} not in {ALLOWED_JUDGE_MODES}",
        )
    if run.get("energy_source") not in ALLOWED_ENERGY:
        return (
            False,
            f"E7 run.energy_source={run.get('energy_source')!r} not in {ALLOWED_ENERGY}",
        )
    if run.get("evidence_label") not in ALLOWED_EVIDENCE:
        return (
            False,
            f"E8 run.evidence_label={run.get('evidence_label')!r} not in {ALLOWED_EVIDENCE}",
        )

    # E10 — comparator.winner enum
    comp = artifact.get("comparator", {})
    if comp.get("winner") not in ALLOWED_WINNERS:
        return (
            False,
            f"E10 comparator.winner={comp.get('winner')!r} not in {ALLOWED_WINNERS}",
        )
    if artifact.get("totals", {}).get("evidence_label") not in ALLOWED_EVIDENCE:
        return False, "E11 totals.evidence_label invalid"

    # C2
    if artifact.get("schema_hash") != schema_hash:
        return False, "C2 schema_hash mismatch"

    # C3 — top_level_sha256
    body = {k: v for k, v in artifact.items() if k != "hash_chain"}
    if sha256_hex(body) != artifact["hash_chain"]["top_level_sha256"]:
        return False, "C3 hash_chain.top_level_sha256 mismatch"

    # C3b — task_ids_sorted_sha256 is over ALL suites concatenated (sorted lex),
    # joined with newlines, encoded UTF-8, then SHA-256 hex — NOT canonicalized.
    all_ids = sorted(
        t["task_id"] for s in artifact.get("suites", []) for t in s["task_results"]
    )
    expected_ids_hash = hashlib.sha256("\n".join(all_ids).encode("utf-8")).hexdigest()
    if expected_ids_hash != artifact["hash_chain"]["task_ids_sorted_sha256"]:
        return (
            False,
            f"C3b hash_chain.task_ids_sorted_sha256 mismatch (expected {expected_ids_hash})",
        )

    # Per-suite checks C4, C5
    for s in artifact.get("suites", []):
        ids = [t["task_id"] for t in s["task_results"]]
        if len(set(ids)) != len(ids):
            return False, f"C4 suite={s['suite']} has duplicate task_ids"
        # E1 — enum check on suite name
        if s["suite"] not in ALLOWED_SUITES:
            return False, f"E1 suite.name={s['suite']!r} not in {ALLOWED_SUITES}"
        # E2 — enum check on evidence_label
        if s["evidence_label"] not in ALLOWED_EVIDENCE:
            return False, f"E2 suite.evidence_label={s['evidence_label']!r} not allowed"
        # C5 — pass@1 / gen_ok: prefer gen_ok when present (v0.2 cell contract)
        gen_ok_mean = suite_gen_ok_mean(s)
        if gen_ok_mean is not None:
            if round(s.get("gen_ok", gen_ok_mean), 4) != gen_ok_mean:
                return False, (
                    f"C5 suite={s['suite']} gen_ok mismatch "
                    f"(recomputed {gen_ok_mean} vs declared {s.get('gen_ok')})"
                )
            if (
                s["evidence_label"] == "reported"
                and round(s["pass_at_1"], 4) != gen_ok_mean
            ):
                return False, (
                    f"C5 suite={s['suite']} pass_at_1 must alias gen_ok for reported "
                    f"evidence (gen_ok={gen_ok_mean} vs pass_at_1={s['pass_at_1']})"
                )
        else:
            n_ok = sum(1 for t in s["task_results"] if t["status"] == "ok")
            expected_passat1 = round(n_ok / s["n"], 4)
            if expected_passat1 != round(s["pass_at_1"], 4):
                return False, (
                    f"C5 suite={s['suite']} pass@1 mismatch "
                    f"(recomputed {expected_passat1} vs declared {s['pass_at_1']})"
                )
        for ti, t in enumerate(s["task_results"]):
            gen_ok = task_gen_ok(t)
            if gen_ok is not None and s["evidence_label"] == "reported":
                legacy_pass = (t.get("additionalProperties") or {}).get("pass_at_1")
                if legacy_pass is not None and round(float(legacy_pass), 4) != round(
                    gen_ok, 4
                ):
                    return False, (
                        f"C5 task[{ti}] pass_at_1 must alias gen_ok for reported evidence"
                    )
            if t["status"] not in ALLOWED_STATUSES:
                return (
                    False,
                    f"E3 task[{ti}].status={t['status']!r} not in {ALLOWED_STATUSES}",
                )
            if t["judge"] not in ALLOWED_JUDGES:
                return (
                    False,
                    f"E4 task[{ti}].judge={t['judge']!r} not in {ALLOWED_JUDGES}",
                )

    # C6 — totals must derive from suites
    suites = artifact.get("suites", [])
    total_cells = sum(s["n"] for s in suites)
    total_passed = sum(s["passed"] for s in suites)
    totals = artifact.get("totals", {})
    if totals.get("cells") != total_cells:
        return (
            False,
            f"C6 totals.cells={totals.get('cells')} != sum(suite.n)={total_cells}",
        )
    if totals.get("passed") != total_passed:
        return (
            False,
            f"C6 totals.passed={totals.get('passed')} != sum(suite.passed)={total_passed}",
        )
    if total_cells > 0:
        gen_ok_totals = totals.get("gen_ok")
        if gen_ok_totals is not None:
            weighted_gen_ok = round(
                sum(effective_pass_at_1(s) * s["n"] for s in suites) / total_cells,
                4,
            )
            if round(float(gen_ok_totals), 4) != weighted_gen_ok:
                return False, (
                    f"C6 totals.gen_ok={gen_ok_totals} != derived {weighted_gen_ok}"
                )
            if totals.get("evidence_label") == "reported" and round(
                totals.get("pass_at_1", -1), 4
            ) != round(float(gen_ok_totals), 4):
                return False, (
                    "C6 totals.pass_at_1 must alias gen_ok for reported evidence"
                )
        else:
            expected_overall = round(total_passed / total_cells, 4)
            if expected_overall != round(totals.get("pass_at_1", -1), 4):
                return False, (
                    f"C6 totals.pass_at_1={totals.get('pass_at_1')} != derived {expected_overall}"
                )

    return True, "artifact accepted"


if __name__ == "__main__":
    if len(sys.argv) > 1:
        ok, msg = verify_artifact(sys.argv[1])
        print(f"{'OK' if ok else 'FAIL'}: {msg}")
        sys.exit(0 if ok else 1)
    else:
        result = verify_self()
        for k, v in result.items():
            print(f"{k:>26}: {v}")
        sys.exit(0 if result["SCHEMA_HASH_match"] else 2)
