"""Query and planning methods for the evidence registry.

This module contains configuration loading, source selection, and
discovery plan generation.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import yaml

from pheno.evidence.adapters import (
    ArxivAdapter,
    GitHubAdapter,
    HuggingFaceAdapter,
    LocalCorpusAdapter,
    ModelScopeAdapter,
    RedditAdapter,
)
from pheno.evidence.redaction import redact_object, redact_text

ROOT = Path(__file__).resolve().parents[1]


def load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if payload.get("schema_version") != "pheno.evidence.config.v1":
        raise ValueError("unsupported evidence registry config schema")
    policy = payload.get("policy") or {}
    if policy.get("metadata_only") is not True:
        raise ValueError("policy.metadata_only must be true")
    if policy.get("allow_model_artifact_download") is not False:
        raise ValueError("model artifact downloads must remain disabled")
    if policy.get("mutate_locked_shortlist") is not False:
        raise ValueError("discovery cannot mutate the locked shortlist")
    if not isinstance(payload.get("sources"), dict):
        raise ValueError("config.sources must be an object")
    return payload


def resolve_state_root(config: Mapping[str, Any], override: Path | None) -> Path:
    if override is not None:
        return override.resolve()
    configured = Path(str(config.get("state_root", "state/evidence_registry")))
    return configured if configured.is_absolute() else (ROOT / configured).resolve()


def selected_sources(config: Mapping[str, Any], requested: list[str]) -> list[str]:
    ALL_SOURCES = {"hf", "modelscope", "github", "arxiv", "reddit", "local_corpus"}
    unknown = sorted(set(requested) - ALL_SOURCES - {"all"})
    if unknown:
        raise ValueError(f"unknown sources: {unknown}")
    candidates = sorted(
        ALL_SOURCES if not requested or "all" in requested else set(requested)
    )
    source_config = config["sources"]
    return [
        name for name in candidates if (source_config.get(name) or {}).get("enabled")
    ]


def _operation_id(
    source: str, kind: str, index: int, *, parent: str | None = None
) -> str:
    suffix = f"{kind}:{index:04d}"
    return f"{parent}:{suffix}" if parent else f"{source}:{suffix}"


def plan(
    config: Mapping[str, Any],
    sources: Iterable[str],
    max_queries: int | None,
) -> dict[str, Any]:
    REMOTE_SOURCES = {"hf", "modelscope", "github", "arxiv", "reddit"}
    rows: list[dict[str, Any]] = []
    endpoints = {
        "hf": HuggingFaceAdapter.endpoint,
        "modelscope": ModelScopeAdapter.endpoint,
        "github": GitHubAdapter.endpoint,
        "arxiv": ArxivAdapter.endpoint,
        "reddit": RedditAdapter.endpoint,
        "local_corpus": LocalCorpusAdapter.endpoint,
    }
    for source in sources:
        source_config = config["sources"][source]
        queries = source_config.get("queries", [])
        if source == "local_corpus":
            queries = [
                {
                    "root_index": index,
                    "pattern": source_config.get("pattern", "ChatGPT-*.md"),
                }
                for index, _root in enumerate(source_config.get("roots", []))
            ]
        if max_queries is not None:
            queries = list(queries)[:max_queries]
        for index, query in enumerate(queries):
            rows.append(
                {
                    "operation_id": _operation_id(source, "query", index),
                    "source": source,
                    "endpoint": endpoints[source],
                    "query": redact_object(query),
                    "network": source in REMOTE_SOURCES,
                    "artifact_download": False,
                    "shortlist_mutation": False,
                }
            )
        resolution_key = {
            "hf": "resolve_models",
            "modelscope": "resolve_models",
            "github": "resolve_repositories",
            "arxiv": "resolve_papers",
        }.get(source)
        if resolution_key:
            for index, subject in enumerate(source_config.get(resolution_key, [])):
                rows.append(
                    {
                        "operation_id": _operation_id(source, "resolve", index),
                        "source": source,
                        "endpoint": endpoints[source],
                        "resolve_subject": redact_text(str(subject)),
                        "network": True,
                        "artifact_download": False,
                        "shortlist_mutation": False,
                    }
                )
    return {
        "schema_version": "pheno.evidence.discovery-plan.v1",
        "metadata_only": True,
        "operations": rows,
    }
