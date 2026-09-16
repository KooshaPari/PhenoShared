#!/usr/bin/env python3
"""Apply cloud four-role tier mapping to OmniRoute Main combo."""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

import requests
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import Any

from pheno.paths import CONFIG_DIR, OMNIROUTE_DB, OMNIROUTE_URL, TRAINING_DIR

CLOUD_TIERS = CONFIG_DIR / "cloud_tiers.yaml"
COMBO_MAIN = CONFIG_DIR / "combo_main.json"
OMNI_CONFIG = Path.home() / ".pi" / "agent" / "omniroute.json"
MODELS_JSON = Path.home() / ".pi" / "agent" / "models.json"

ROLE_PATTERNS: dict[str, list[tuple[str, str]]] = {
    "emergency": [
        ("claude", r"claude-opus|opus-4"),
        ("openai", r"gpt-5\.5|gpt-5-5"),
        ("minimax", r"minimax"),
        ("kimi", r"kimi|fireworks"),
    ],
    "teacher": [
        ("claude", r"claude-opus|opus-4"),
        ("openai", r"gpt-5\.5|gpt-5-4"),
        ("local", r"qwen3\.5-4b|qwen"),
    ],
    "parallel": [
        ("openai", r"codex-spark|gpt-5\.3-codex"),
        ("local", r"qwen3\.5-4b|qwen"),
        ("minimax", r"minimax"),
    ],
}


def _expand(path_str: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(path_str)))


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_combo_main(path: Path) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def merge_tiers(cloud: dict[str, Any], combo_main: dict[str, Any]) -> dict[str, Any]:
    merged = dict(combo_main)
    merged.setdefault("combo_id", cloud.get("combo_id", "Main"))
    merged["budget_states"] = cloud.get(
        "budget_states", merged.get("budget_states", {})
    )
    merged["escalation_ladder"] = cloud.get("escalation_ladder", [])
    merged["roles_yaml"] = cloud.get("roles", {})
    merged["applied_at"] = datetime.now(UTC).isoformat()
    return merged


def _match_role(provider_id: str, model: str) -> str | None:
    blob = f"{provider_id}/{model}".lower()
    for role, patterns in ROLE_PATTERNS.items():
        for prov, regex in patterns:
            if prov in blob or re.search(regex, blob):
                return role
    return None


def _provider_tier_weight(merged: dict[str, Any], role: str, provider_id: str, model: str) -> int:
    tiers = merged.get("tier_weights", {})
    role_cfg = tiers.get(role, {})
    blob = f"{provider_id}/{model}".lower()
    best = 0
    for entry in role_cfg.get("providers", []):
        prov = str(entry.get("provider", "")).lower()
        mdl = str(entry.get("model", "")).lower()
        if prov in blob or mdl in blob or re.search(re.escape(mdl), blob):
            best = max(best, int(entry.get("tier_weight", 0)))
    for lane in role_cfg.get("lanes", []):
        mdl = str(lane.get("model", "")).lower()
        if mdl in blob:
            best = max(best, int(lane.get("tier_weight", 0)))
    return best


def annotate_combo_data(data: dict[str, Any], merged: dict[str, Any]) -> dict[str, Any]:
    out = json.loads(json.dumps(data))
    config = out.setdefault("config", {})
    config["weights"] = merged.get("router_weights", config.get("weights", {}))
    config["phenoTiers"] = merged.get("tier_weights", {})
    config["phenoBudgetStates"] = merged.get("budget_states", {})
    config["phenoComboSource"] = str(COMBO_MAIN)
    config["phenoAppliedAt"] = merged["applied_at"]

    models = out.get("models", [])
    for entry in models:
        if not isinstance(entry, dict):
            continue
        provider_id = str(entry.get("providerId", ""))
        model = str(entry.get("model", ""))
        role = _match_role(provider_id, model)
        if role:
            entry["phenoRole"] = role
            tw = _provider_tier_weight(merged, role, provider_id, model)
            if tw:
                entry["tierWeight"] = tw
                entry["weight"] = max(int(entry.get("weight", 0)), tw)
    out["models"] = models
    out["updatedAt"] = merged["applied_at"]
    return out


def load_main_combo(
    conn: sqlite3.Connection, combo_id: str
) -> tuple[str, str, dict] | None:
    row = conn.execute(
        "SELECT id, name, data FROM combos WHERE name = ? OR id = ? LIMIT 1",
        (combo_id, combo_id),
    ).fetchone()
    if not row:
        return None
    cid, name, raw = row
    return cid, name, json.loads(raw) if raw else {}


def apply_sqlite(db: Path, merged: dict[str, Any], combo_id: str) -> dict[str, Any]:
    conn = sqlite3.connect(db)
    loaded = load_main_combo(conn, combo_id)
    if not loaded:
        conn.close()
        raise SystemExit(f"Combo '{combo_id}' not found in {db}")
    cid, name, data = loaded
    updated = annotate_combo_data(data, merged)
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "UPDATE combos SET data = ?, updated_at = ? WHERE id = ?",
        (json.dumps(updated, ensure_ascii=False), now, cid),
    )
    conn.commit()
    conn.close()
    print(f"SQLite: updated combo {name} ({cid}) with pheno tier overlay")
    return updated


def export_training(merged: dict[str, Any], combo_payload: dict | None) -> Path:
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    out = TRAINING_DIR / "combo_main.json"
    doc = {
        "combo_id": merged.get("combo_id", "Main"),
        "tier_weights": merged.get("tier_weights", {}),
        "router_weights": merged.get("router_weights", {}),
        "budget_states": merged.get("budget_states", {}),
        "escalation_ladder": merged.get("escalation_ladder", []),
        "roles_yaml": merged.get("roles_yaml", {}),
        "applied_at": merged.get("applied_at"),
        "omniroute_combo": combo_payload,
    }
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Export: {out}")
    return out


def _omni_api_key() -> str | None:
    key = os.environ.get("OMNIROUTE_API_KEY")
    if key:
        return key
    if MODELS_JSON.exists():
        try:
            models = json.loads(MODELS_JSON.read_text(encoding="utf-8"))
            return models.get("providers", {}).get("omni", {}).get("apiKey")
        except (json.JSONDecodeError, OSError):
            return None
    return None


def apply_api(base_url: str, merged: dict[str, Any], combo_id: str, combo_payload: dict[str, Any]) -> bool:
    key = _omni_api_key()
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    url = f"{base_url.rstrip('/')}/api/combos/{combo_id}"
    r = requests.put(url, headers=headers, json=combo_payload, timeout=30)
    if r.status_code in (200, 201):
        print(f"API: updated combo {combo_id}")
        return True
    print(f"API: failed {r.status_code} {r.text[:300]}")
    return False


def main() -> None:
    p = argparse.ArgumentParser(
        description="Apply cloud tier mapping to OmniRoute Main combo"
    )
    p.add_argument("--cloud-tiers", type=Path, default=CLOUD_TIERS)
    p.add_argument("--combo-main", type=Path, default=COMBO_MAIN)
    p.add_argument("--db", type=Path, default=OMNIROUTE_DB)
    p.add_argument("--url", default=OMNIROUTE_URL)
    p.add_argument(
        "--combo-id", default=None, help="Override combo id (default: from yaml)"
    )
    p.add_argument(
        "--mode", choices=["sqlite", "export", "api", "both"], default="both"
    )
    args = p.parse_args()

    cloud = load_yaml(args.cloud_tiers)
    combo_main = load_combo_main(args.combo_main)
    combo_id = (
        args.combo_id or cloud.get("combo_id") or combo_main.get("combo_id") or "Main"
    )
    merged = merge_tiers(cloud, combo_main)

    combo_payload: dict | None = None
    if args.mode in ("sqlite", "both", "api"):
        combo_payload = apply_sqlite(args.db, merged, combo_id)
    if args.mode in ("export", "both"):
        export_training(merged, combo_payload)
    if args.mode == "api":
        if combo_payload is None:
            conn = sqlite3.connect(args.db)
            loaded = load_main_combo(conn, combo_id)
            conn.close()
            if not loaded:
                raise SystemExit(f"Combo '{combo_id}' not found")
            combo_payload = annotate_combo_data(loaded[2], merged)
        apply_api(args.url, merged, combo_id, combo_payload)


if __name__ == "__main__":
    main()
