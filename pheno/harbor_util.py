"""Shared Harbor + OmniRoute / Fireworks helpers for eval scripts."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, cast


def harbor_exe() -> str:
    """Return the path to the harbor CLI executable (Windows-aware)."""
    appdata = (
        Path(os.environ.get("APPDATA", ""))
        / "Python"
        / "Python314"
        / "Scripts"
        / "harbor.exe"
    )
    if appdata.exists():
        return str(appdata)
    return "harbor"


def _load_forge_creds() -> list[dict[Any, Any]]:
    cred_path = Path.home() / "forge" / ".credentials.json"
    if not cred_path.exists():
        return []
    return cast(list[dict[Any, Any]], json.loads(cred_path.read_text(encoding="utf-8")))


def litellm_model(
    model_id: str, *, direct: bool = False, direct_model: str | None = None
) -> str:
    """Map a model id to a litellm ``provider/model`` string for the harbor CLI."""
    if direct:
        mid = direct_model or model_id
        if mid.startswith("accounts/"):
            return f"fireworks_ai/{mid}"
        return mid
    if "/" not in model_id:
        return f"openai/{model_id}"
    return f"openai/{model_id}"


def omniroute_env() -> dict[str, str]:
    """Return an env dict with the OmniRoute LiteLLM proxy defaults."""
    env = os.environ.copy()
    if not env.get("OPENAI_API_KEY"):
        for entry in _load_forge_creds():
            if entry.get("id") in ("openai_compatible", "openai_responses_compatible"):
                key = (entry.get("auth_details") or {}).get("api_key")
                if key:
                    env["OPENAI_API_KEY"] = key
                    break
    env.setdefault("OPENAI_BASE_URL", "http://127.0.0.1:20128/v1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    return env


def fireworks_env(credential_id: str = "fireworks-ai-firepass") -> dict[str, str]:
    """Build an env for the Fireworks AI OpenAI-compat endpoint."""
    env = os.environ.copy()
    fpk = env.get("FIREWORKS_AI_API_KEY") or env.get("OPENAI_API_KEY")
    if not fpk:
        for entry in _load_forge_creds():
            if entry.get("id") == credential_id:
                fpk = (entry.get("auth_details") or {}).get("api_key")
                break
    if fpk:
        env["OPENAI_API_KEY"] = fpk
        env["FIREWORKS_AI_API_KEY"] = fpk
    env["OPENAI_BASE_URL"] = "https://api.fireworks.ai/inference/v1"
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    return env


def local_env(base_url: str, *, api_key: str = "local-no-key") -> dict[str, str]:
    """OpenAI-compatible env for direct llama-server endpoints."""
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = api_key
    env["OPENAI_BASE_URL"] = base_url.rstrip("/")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    return env


def route_env(entry: dict[str, Any], cfg: dict[str, Any] | None = None) -> tuple[str, str, dict[str, str]]:
    """Resolve ``(route_kind, harbor_model, env)`` for a harbor_tbench_routes.yaml entry."""
    """Resolve (route_kind, harbor_model, env) for harbor_tbench_routes.yaml entries."""
    route_kind = entry.get("route_kind", "omniroute_cloud")
    if route_kind in ("local_direct", "pheno_serve"):
        default_base = (
            "http://127.0.0.1:21080/v1"
            if route_kind == "pheno_serve"
            else "http://127.0.0.1:8080/v1"
        )
        base = entry.get("base_url", default_base)
        api_model = entry.get("api_model", entry.get("label", "local"))
        prov = (cfg or {}).get("provider") or {}
        key = prov.get("local_api_key", "local-no-key")
        return route_kind, f"openai/{api_model}", local_env(base, api_key=key)
    if entry.get("combo"):
        return route_kind, "openai/Main", omniroute_env()
    model_id = entry["id"]
    return route_kind, litellm_model(model_id), omniroute_env()
