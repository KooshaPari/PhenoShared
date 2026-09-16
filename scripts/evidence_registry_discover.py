#!/usr/bin/env python3
"""Metadata-only evidence discovery logic.

Contains the ``discover`` function that orchestrates source-specific
discovery operations (HuggingFace, ModelScope, GitHub, ArXiv, Reddit,
local corpus).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pheno.evidence.adapters import (
    GitHubAdapter,
    LocalCorpusAdapter,
    ModelScopeAdapter,
    RedditAdapter,
)
from pheno.evidence.redaction import redact_text
from pheno.evidence.store import RegistryStore

REMOTE_SOURCES = {"hf", "modelscope", "github", "arxiv", "reddit"}
ALL_SOURCES = REMOTE_SOURCES | {"local_corpus"}


def _operation_id(
    source: str, kind: str, index: int, *, parent: str | None = None
) -> str:
    suffix = f"{kind}:{index:04d}"
    return f"{parent}:{suffix}" if parent else f"{source}:{suffix}"


def _safe_error(exc: Exception) -> dict[str, str]:
    """Return useful failure classification without echoing request data or paths."""

    return {"type": type(exc).__name__, "message": "operation failed"}


def _new_operation(
    report: dict[str, Any],
    *,
    operation_id: str,
    source: str,
    kind: str,
    subject: str | None = None,
) -> dict[str, Any]:
    operation: dict[str, Any] = {
        "operation_id": operation_id,
        "source": source,
        "kind": kind,
        "status": "planned",
        "snapshots": 0,
        "records": 0,
    }
    if subject is not None:
        operation["subject"] = redact_text(subject)
    report["operations"].append(operation)
    report["planned"] += 1
    return operation


def _fail_operation(
    report: dict[str, Any], operation: dict[str, Any], exc: Exception
) -> None:
    operation["status"] = "failed"
    operation["error"] = _safe_error(exc)
    report["failed"] += 1
    report["errors"].append(
        {
            "operation_id": operation["operation_id"],
            "source": operation["source"],
            "kind": operation["kind"],
            "error": operation["error"],
        }
    )


def _attempt_operation(
    report: dict[str, Any],
    *,
    operation_id: str,
    source: str,
    kind: str,
    action,
    subject: str | None = None,
) -> tuple[bool, Any]:
    """Attempt one bounded operation and contain its failure."""

    operation = _new_operation(
        report,
        operation_id=operation_id,
        source=source,
        kind=kind,
        subject=subject,
    )
    report["queries"] += 1  # compatibility: attempted metadata operations
    try:
        snapshots, records, value = action()
    except Exception as exc:
        _fail_operation(report, operation, exc)
        return False, None
    operation["snapshots"] = int(snapshots)
    operation["records"] = int(records)
    report["snapshots"] += int(snapshots)
    report["records"] += int(records)
    if kind in {"resolve", "hydrate"} and int(records) < 1:
        _fail_operation(
            report,
            operation,
            ValueError("explicit metadata resolution normalized no records"),
        )
        return False, value
    operation["status"] = "completed"
    report["completed"] += 1
    return True, value


def _skip_operation(
    report: dict[str, Any],
    *,
    operation_id: str,
    source: str,
    kind: str,
    reason: str,
    subject: str | None = None,
) -> None:
    operation = _new_operation(
        report,
        operation_id=operation_id,
        source=source,
        kind=kind,
        subject=subject,
    )
    operation["status"] = "skipped"
    operation["reason"] = reason
    report["skipped"] += 1


def discover(
    config: Mapping[str, Any],
    sources: list[str],
    store: RegistryStore,
    *,
    max_queries: int | None,
    allow_metadata_network: bool,
    resolve_only: bool = False,
) -> dict[str, Any]:
    if (
        any(source in REMOTE_SOURCES for source in sources)
        and not allow_metadata_network
    ):
        raise ValueError("remote discovery requires --allow-metadata-network")
    policy = config["policy"]
    # Look up the transport classes + persist_page via the public
    # re-export module so monkey-patching tests that target
    # ``scripts.evidence_registry.MetadataClient``,
    # ``HuggingFaceAdapter``, ``ArxivAdapter``, ``persist_page``
    # apply at the call sites below.
    import scripts.evidence_registry as _cli

    client = _cli.MetadataClient(
        timeout=float(policy.get("timeout_seconds", 20)),
        max_response_bytes=int(policy.get("max_response_bytes", 8 * 1024 * 1024)),
        retries=int(policy.get("retries", 3)),
    )
    counts: dict[str, Any] = {
        "snapshots": 0,
        "records": 0,
        "queries": 0,
        "planned": 0,
        "completed": 0,
        "failed": 0,
        "skipped": 0,
        "operations": [],
        "errors": [],
    }
    for source in sources:
        source_config = config["sources"][source]
        queries = [] if resolve_only else list(source_config.get("queries", []))
        if max_queries is not None:
            queries = queries[:max_queries]
        if source == "local_corpus":
            roots = list(source_config.get("roots", []))
            if max_queries is not None:
                roots = roots[:max_queries]
            for index, root in enumerate(roots):
                operation_id = _operation_id(source, "query", index)

                def scan_local(root_value=root):
                    snapshot_count = 0
                    record_count = 0
                    for page in LocalCorpusAdapter.scan(
                        Path(root_value),
                        pattern=str(source_config.get("pattern", "ChatGPT-*.md")),
                    ):
                        snapshots, records = _cli.persist_page(
                            store, page, LocalCorpusAdapter.normalize
                        )
                        snapshot_count += snapshots
                        record_count += records
                    return snapshot_count, record_count, None

                _attempt_operation(
                    counts,
                    operation_id=operation_id,
                    source=source,
                    kind="query",
                    action=scan_local,
                )
            continue

        if source == "hf":
            try:
                adapter: Any = _cli.HuggingFaceAdapter(client)
            except Exception as exc:
                specs = [
                    ("resolve", index, str(subject))
                    for index, subject in enumerate(
                        source_config.get("resolve_models", [])
                    )
                ] + [("query", index, None) for index, _row in enumerate(queries)]
                for kind, index, subject in specs:
                    operation = _new_operation(
                        counts,
                        operation_id=_operation_id(source, kind, index),
                        source=source,
                        kind=kind,
                        subject=subject,
                    )
                    counts["queries"] += 1
                    _fail_operation(counts, operation, exc)
                continue
            hydrate_limit = int(source_config.get("hydrate_limit", 0))
            for index, model_id in enumerate(source_config.get("resolve_models", [])):

                def resolve_hf(subject=str(model_id)):
                    detail = adapter.detail(subject)
                    snapshots, records = _cli.persist_page(
                        store, detail, adapter.normalize
                    )
                    return snapshots, records, None

                _attempt_operation(
                    counts,
                    operation_id=_operation_id(source, "resolve", index),
                    source=source,
                    kind="resolve",
                    action=resolve_hf,
                    subject=str(model_id),
                )
            for index, row in enumerate(queries):
                operation_id = _operation_id(source, "query", index)

                def search_hf(query=row):
                    page = adapter.search(
                        str(query["query"]),
                        limit=int(query.get("limit", 25)),
                        author=query.get("author"),
                    )
                    snapshots, records = _cli.persist_page(
                        store, page, adapter.normalize
                    )
                    candidates = adapter.candidate_ids(page)[:hydrate_limit]
                    return snapshots, records, candidates

                succeeded, candidates = _attempt_operation(
                    counts,
                    operation_id=operation_id,
                    source=source,
                    kind="query",
                    action=search_hf,
                )
                if not succeeded:
                    continue
                for hydrate_index, model_id in enumerate(candidates):

                    def hydrate_hf(subject=model_id):
                        detail = adapter.detail(subject)
                        snapshots, records = _cli.persist_page(
                            store, detail, adapter.normalize
                        )
                        return snapshots, records, None

                    _attempt_operation(
                        counts,
                        operation_id=_operation_id(
                            source, "hydrate", hydrate_index, parent=operation_id
                        ),
                        source=source,
                        kind="hydrate",
                        action=hydrate_hf,
                        subject=model_id,
                    )
        elif source == "modelscope":
            try:
                adapter = ModelScopeAdapter(client)
            except Exception as exc:
                specs = [
                    ("resolve", index, str(subject))
                    for index, subject in enumerate(
                        source_config.get("resolve_models", [])
                    )
                ] + [("query", index, None) for index, _row in enumerate(queries)]
                for kind, index, subject in specs:
                    operation = _new_operation(
                        counts,
                        operation_id=_operation_id(source, kind, index),
                        source=source,
                        kind=kind,
                        subject=subject,
                    )
                    counts["queries"] += 1
                    _fail_operation(counts, operation, exc)
                continue
            hydrate_limit = int(source_config.get("hydrate_limit", 0))
            for index, model_id in enumerate(source_config.get("resolve_models", [])):

                def resolve_modelscope(subject=str(model_id)):
                    detail = adapter.detail(subject)
                    snapshots, records = _cli.persist_page(
                        store, detail, adapter.normalize
                    )
                    return snapshots, records, None

                _attempt_operation(
                    counts,
                    operation_id=_operation_id(source, "resolve", index),
                    source=source,
                    kind="resolve",
                    action=resolve_modelscope,
                    subject=str(model_id),
                )
            for index, row in enumerate(queries):
                operation_id = _operation_id(source, "query", index)

                def search_modelscope(query=row):
                    page = adapter.search(
                        str(query["query"]),
                        page_number=int(query.get("page_number", 1)),
                        page_size=int(query.get("page_size", 25)),
                        owner=query.get("owner"),
                        sort=query.get("sort"),
                        filters=query.get("filters"),
                    )
                    snapshots, records = _cli.persist_page(
                        store, page, adapter.normalize
                    )
                    candidates = adapter.candidate_ids(page)[:hydrate_limit]
                    return snapshots, records, candidates

                succeeded, candidates = _attempt_operation(
                    counts,
                    operation_id=operation_id,
                    source=source,
                    kind="query",
                    action=search_modelscope,
                )
                if not succeeded:
                    continue
                for hydrate_index, model_id in enumerate(candidates):

                    def hydrate_modelscope(subject=model_id):
                        detail = adapter.detail(subject)
                        snapshots, records = _cli.persist_page(
                            store, detail, adapter.normalize
                        )
                        return snapshots, records, None

                    _attempt_operation(
                        counts,
                        operation_id=_operation_id(
                            source, "hydrate", hydrate_index, parent=operation_id
                        ),
                        source=source,
                        kind="hydrate",
                        action=hydrate_modelscope,
                        subject=model_id,
                    )
        elif source == "github":
            try:
                adapter = GitHubAdapter(client, token=os.environ.get("GITHUB_TOKEN"))
            except Exception as exc:
                specs = [
                    ("resolve", index, str(subject))
                    for index, subject in enumerate(
                        source_config.get("resolve_repositories", [])
                    )
                ] + [("query", index, None) for index, _row in enumerate(queries)]
                for kind, index, subject in specs:
                    operation = _new_operation(
                        counts,
                        operation_id=_operation_id(source, kind, index),
                        source=source,
                        kind=kind,
                        subject=subject,
                    )
                    counts["queries"] += 1
                    _fail_operation(counts, operation, exc)
                continue
            hydrate_limit = int(source_config.get("hydrate_limit", 0))
            for index, full_name in enumerate(
                source_config.get("resolve_repositories", [])
            ):

                def resolve_github(subject=str(full_name)):
                    detail = adapter.resolve_commit(subject, "HEAD")
                    snapshots, records = _cli.persist_page(
                        store,
                        detail,
                        lambda value, *, raw_sha256: adapter.normalize_commit(
                            value,
                            raw_sha256=raw_sha256,
                            full_name=subject,
                        ),
                    )
                    return snapshots, records, None

                _attempt_operation(
                    counts,
                    operation_id=_operation_id(source, "resolve", index),
                    source=source,
                    kind="resolve",
                    action=resolve_github,
                    subject=str(full_name),
                )
            for index, row in enumerate(queries):
                operation_id = _operation_id(source, "query", index)

                def search_github(query=row):
                    page = adapter.search(
                        str(query["query"]),
                        page=int(query.get("page", 1)),
                        per_page=int(query.get("per_page", 30)),
                        sort=str(query.get("sort", "updated")),
                        order=str(query.get("order", "desc")),
                    )
                    snapshots, records = _cli.persist_page(
                        store, page, adapter.normalize
                    )
                    candidates = adapter.candidates(page)[:hydrate_limit]
                    return snapshots, records, candidates

                succeeded, candidates = _attempt_operation(
                    counts,
                    operation_id=operation_id,
                    source=source,
                    kind="query",
                    action=search_github,
                )
                if not succeeded:
                    continue
                for hydrate_index, (full_name, ref) in enumerate(candidates):

                    def hydrate_github(name=full_name, revision=ref):
                        detail = adapter.resolve_commit(name, revision)
                        snapshots, records = _cli.persist_page(
                            store,
                            detail,
                            lambda value, *, raw_sha256: adapter.normalize_commit(
                                value,
                                raw_sha256=raw_sha256,
                                full_name=name,
                            ),
                        )
                        return snapshots, records, None

                    _attempt_operation(
                        counts,
                        operation_id=_operation_id(
                            source, "hydrate", hydrate_index, parent=operation_id
                        ),
                        source=source,
                        kind="hydrate",
                        action=hydrate_github,
                        subject=full_name,
                    )
        elif source == "arxiv":
            try:
                adapter = _cli.ArxivAdapter(client)
            except Exception as exc:
                specs = [
                    ("resolve", index, str(subject))
                    for index, subject in enumerate(
                        source_config.get("resolve_papers", [])
                    )
                ] + [("query", index, None) for index, _row in enumerate(queries)]
                for kind, index, subject in specs:
                    operation = _new_operation(
                        counts,
                        operation_id=_operation_id(source, kind, index),
                        source=source,
                        kind=kind,
                        subject=subject,
                    )
                    counts["queries"] += 1
                    _fail_operation(counts, operation, exc)
                continue
            for index, paper_id in enumerate(source_config.get("resolve_papers", [])):

                def resolve_arxiv(subject=str(paper_id)):
                    detail = adapter.resolve_paper(subject)
                    snapshots, records = _cli.persist_page(
                        store, detail, adapter.normalize
                    )
                    return snapshots, records, None

                _attempt_operation(
                    counts,
                    operation_id=_operation_id(source, "resolve", index),
                    source=source,
                    kind="resolve",
                    action=resolve_arxiv,
                    subject=str(paper_id),
                )
            for index, row in enumerate(queries):

                def search_arxiv(query=row):
                    page = adapter.search(
                        str(query["query"]),
                        start=int(query.get("start", 0)),
                        max_results=int(query.get("max_results", 25)),
                    )
                    snapshots, records = _cli.persist_page(
                        store, page, adapter.normalize
                    )
                    return snapshots, records, None

                _attempt_operation(
                    counts,
                    operation_id=_operation_id(source, "query", index),
                    source=source,
                    kind="query",
                    action=search_arxiv,
                )
        elif source == "reddit":
            token = os.environ.get("REDDIT_ACCESS_TOKEN")
            user_agent = os.environ.get("REDDIT_USER_AGENT")
            if not token or not user_agent:
                for index, _row in enumerate(queries):
                    _skip_operation(
                        counts,
                        operation_id=_operation_id(source, "query", index),
                        source=source,
                        kind="query",
                        reason="credentials_unavailable",
                    )
                if queries:
                    counts["errors"].append(
                        {
                            "source": source,
                            "kind": "setup",
                            "error": {
                                "type": "CredentialsUnavailable",
                                "message": "operation prerequisites unavailable",
                            },
                        }
                    )
                continue
            try:
                adapter = RedditAdapter(
                    client, access_token=token, user_agent=user_agent
                )
            except Exception as exc:
                for index, _row in enumerate(queries):
                    operation = _new_operation(
                        counts,
                        operation_id=_operation_id(source, "query", index),
                        source=source,
                        kind="query",
                    )
                    counts["queries"] += 1
                    _fail_operation(counts, operation, exc)
                continue
            for index, row in enumerate(queries):

                def search_reddit(query=row):
                    raw_page = adapter.search(
                        str(query["query"]),
                        limit=int(query.get("limit", 25)),
                        subreddit=query.get("subreddit"),
                    )
                    snapshot_count = 0
                    record_count = 0
                    for citation_page in adapter.citation_pages(raw_page):
                        snapshots, records = _cli.persist_page(
                            store,
                            citation_page,
                            adapter.normalize_citation,
                        )
                        snapshot_count += snapshots
                        record_count += records
                    return snapshot_count, record_count, None

                _attempt_operation(
                    counts,
                    operation_id=_operation_id(source, "query", index),
                    source=source,
                    kind="query",
                    action=search_reddit,
                )
    if counts["planned"] != counts["completed"] + counts["failed"] + counts["skipped"]:
        raise RuntimeError("discovery operation accounting invariant failed")
    counts["validation"] = store.validate()
    counts["ok"] = not counts["errors"] and counts["validation"]["ok"]
    return {
        "schema_version": "pheno.evidence.discovery-run.v2",
        "metadata_only": True,
        "artifact_download": False,
        "shortlist_mutation": False,
        "resolve_only": resolve_only,
        "max_queries": max_queries,
        **counts,
    }
