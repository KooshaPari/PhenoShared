"""Hugging Face Hub metadata discovery without artifact downloads."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import replace
from typing import Any
from urllib.parse import quote, unquote, urlparse

import requests

from .base import DiscoveryPage, MetadataClient, normalized_record, with_retry

_COMMIT_SHA = re.compile(r"^[0-9a-fA-F]{40}$")
_MODEL_ID = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?/"
    r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$"
)
_PARAMETER_HINT = re.compile(
    r"(?<![A-Za-z0-9.])(\d+(?:\.\d+)?)\s*([BM])(?=$|[-_.])",
    re.IGNORECASE,
)


class HuggingFaceAdapter:
    """Hugging Face Hub metadata discovery (no artifact downloads).

    Search, detail, and hydrate_config all return DiscoveryPages;
    normalize() turns each page into registry records; candidate_ids()
    enumerates model ids from a search page.

    Satisfies both SourceAdapter (kind, endpoint, search, normalize)
    AND CandidateExtractor (candidate_ids for bulk enumeration).

    Mutability: pages returned by ``search`` are marked
    ``incomplete=True`` because a full record requires a detail fetch
    to pin the SHA revision.
    """

    kind = "hf"
    endpoint = "https://huggingface.co/api/models"

    def __init__(self, client: MetadataClient) -> None:
        """Initialize the HuggingFace adapter with the shared metadata client."""
        self.client = client

    @with_retry()
    def search(
        self, query: str, *, limit: int = 25, author: str | None = None
    ) -> DiscoveryPage:
        """Search the HuggingFace Hub and return a DiscoveryPage (incomplete=True)."""
        if not query.strip() or not 1 <= limit <= 100:
            raise ValueError("Hugging Face search requires a query and limit 1..100")
        params: dict[str, Any] = {"search": query, "limit": limit}
        if author:
            params["author"] = author
        page = self.client.request(
            source_kind=self.kind,
            method="GET",
            url=self.endpoint,
            params=params,
        )
        if not isinstance(page.payload, list):
            raise ValueError("Hugging Face search response must be an array")
        # Search records require a detail/revision hydration before execution.
        return replace(page, incomplete=True)

    @staticmethod
    def _check_model_id(model_id: str) -> None:
        if not _MODEL_ID.fullmatch(model_id):
            raise ValueError("Hugging Face detail requires owner/model")

    @with_retry()
    def detail(
        self,
        model_id: str,
        *,
        revision: str | None = None,
        hydrate_config: bool = True,
    ) -> DiscoveryPage:
        """Fetch a single HuggingFace model record; optionally hydrate config."""
        self._check_model_id(model_id)
        encoded = quote(model_id, safe="/")
        endpoint = f"{self.endpoint}/{encoded}"
        if revision:
            endpoint += f"/revision/{quote(revision, safe='')}"
        page = self.client.request(
            source_kind=self.kind,
            method="GET",
            url=endpoint,
        )
        if not isinstance(page.payload, Mapping):
            raise ValueError("Hugging Face detail response must be an object")
        resolved_id = str(
            page.payload.get("id") or page.payload.get("modelId") or ""
        ).strip()
        if resolved_id != model_id:
            raise ValueError("Hugging Face detail response identity mismatch")
        sha = str(page.payload.get("sha") or "").strip()
        detail = replace(page, incomplete=not bool(_COMMIT_SHA.fullmatch(sha)))
        if hydrate_config and _COMMIT_SHA.fullmatch(sha):
            try:
                return self.hydrate_config(detail)
            except requests.HTTPError as exc:
                response = exc.response
                if response is None or response.status_code != 404:
                    raise
                payload = dict(detail.payload)
                payload["_pheno_config_hydration"] = {
                    "filename": "config.json",
                    "revision": sha.lower(),
                    "status": "missing",
                }
                return replace(detail, payload=payload, incomplete=True)
        return detail

    @with_retry()
    def hydrate_config(self, detail: DiscoveryPage) -> DiscoveryPage:
        """Merge immutable, bounded ``config.json`` metadata into a detail page.

        Only the full commit returned by the Hub detail API and the literal
        ``config.json`` path are accepted. Model artifacts, mutable branch
        names, arbitrary repository paths, and cross-host redirects are not.
        """

        if detail.source_kind != self.kind or not isinstance(detail.payload, Mapping):
            raise ValueError("config hydration requires a Hugging Face detail page")
        model_id = str(
            detail.payload.get("id") or detail.payload.get("modelId") or ""
        ).strip()
        self._check_model_id(model_id)
        revision = str(detail.payload.get("sha") or "").strip()
        if not _COMMIT_SHA.fullmatch(revision):
            raise ValueError("config hydration requires a full immutable commit SHA")

        encoded = quote(model_id, safe="/")
        config_url = f"https://huggingface.co/{encoded}/resolve/{revision}/config.json"
        config_page = self.client.request(
            source_kind=self.kind,
            method="GET",
            url=config_url,
            headers={"Accept": "application/json"},
        )
        final = urlparse(config_page.final_url)
        decoded_path = unquote(final.path)
        if (
            final.scheme != "https"
            or (final.hostname or "").lower() != "huggingface.co"
            or not decoded_path.endswith("/config.json")
            or revision.lower() not in decoded_path.lower()
        ):
            raise ValueError("config hydration followed an unexpected URL")

        config = config_page.payload
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except json.JSONDecodeError as exc:
                raise ValueError("Hugging Face config.json is invalid JSON") from exc
        if not isinstance(config, Mapping):
            raise ValueError("Hugging Face config.json must contain an object")

        merged = dict(detail.payload)
        merged["config"] = dict(config)
        merged["_pheno_config_hydration"] = {
            "filename": "config.json",
            "revision": revision.lower(),
            "status": "hydrated",
            "url": config_page.final_url,
        }
        query = dict(detail.query)
        query["config_hydration"] = {
            "filename": "config.json",
            "revision": revision.lower(),
        }
        return replace(
            detail,
            query=query,
            retrieved_at=config_page.retrieved_at,
            payload=merged,
            incomplete=False,
        )

    @staticmethod
    def candidate_ids(page: DiscoveryPage) -> list[str]:
        """Extract model-id strings from a HuggingFace search DiscoveryPage."""
        if not isinstance(page.payload, list):
            return []
        return [
            str(item.get("id") or item.get("modelId"))
            for item in page.payload
            if isinstance(item, Mapping) and (item.get("id") or item.get("modelId"))
        ]

    @staticmethod
    def _license(item: Mapping[str, Any]) -> list[str]:
        card = item.get("cardData")
        values: list[str] = []
        if isinstance(card, Mapping):
            license_value = card.get("license")
            if isinstance(license_value, str):
                values.append(license_value)
            elif isinstance(license_value, list):
                values.extend(str(value) for value in license_value if value)
        for tag in item.get("tags") or []:
            if isinstance(tag, str) and tag.startswith("license:"):
                values.append(tag.split(":", 1)[1])
        return list(dict.fromkeys(values))

    @staticmethod
    def _config_views(config: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        text_config = config.get("text_config")
        return [config, text_config] if isinstance(text_config, Mapping) else [config]

    @staticmethod
    def _positive_int(
        views: list[Mapping[str, Any]], keys: tuple[str, ...]
    ) -> int | None:
        for view in views:
            for key in keys:
                value = view.get(key)
                if isinstance(value, int) and not isinstance(value, bool) and value > 0:
                    return value
        return None

    @classmethod
    def _architecture(cls, config: Mapping[str, Any]) -> str | None:
        for view in cls._config_views(config):
            architectures = view.get("architectures")
            if isinstance(architectures, list) and architectures:
                architecture = architectures[0]
                if isinstance(architecture, str) and architecture.strip():
                    return architecture.strip()
            model_type = view.get("model_type")
            if isinstance(model_type, str) and model_type.strip():
                return model_type.strip()
        return None

    @staticmethod
    def _name_parameter_hint(model_id: str) -> int | None:
        name = model_id.rsplit("/", 1)[-1]
        match = _PARAMETER_HINT.search(name)
        if match is None:
            return None
        scale = 1_000_000_000 if match.group(2).upper() == "B" else 1_000_000
        return int(float(match.group(1)) * scale)

    @classmethod
    def _parameter_floor(cls, config: Mapping[str, Any]) -> int | None:
        views = cls._config_views(config)
        hidden = cls._positive_int(views, ("hidden_size", "d_model", "n_embd"))
        vocab = cls._positive_int(views, ("vocab_size",))
        if hidden is None or vocab is None:
            return None
        embedding = cls._positive_int(views, ("embedding_size",)) or hidden
        return vocab * embedding

    @classmethod
    def _implausible_parameter_total(
        cls,
        value: Any,
        *,
        model_id: str,
        config: Mapping[str, Any],
        active_parameters: int | None,
    ) -> str | None:
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            return "value is not a positive integer"
        name_hint = cls._name_parameter_hint(model_id)
        if name_hint is not None and value < name_hint // 5:
            return f"value is below 20% of the {name_hint}-parameter name hint"
        floor = cls._parameter_floor(config)
        if floor is not None and value < floor:
            return f"value is below the {floor}-parameter embedding floor"
        if active_parameters is not None and value < active_parameters:
            return "value is below the config-declared active parameter count"
        if value < 100_000 and cls._architecture(config) is not None:
            return "value is too small for the declared model architecture"
        return None

    @classmethod
    def _mtp(cls, config: Mapping[str, Any]) -> str | None:
        views = cls._config_views(config)
        layers = cls._positive_int(
            views,
            (
                "num_nextn_predict_layers",
                "num_mtp_layers",
                "mtp_num_hidden_layers",
                "mtp_depth",
            ),
        )
        if layers is not None:
            suffix = "s" if layers != 1 else ""
            return f"native MTP ({layers} predictor layer{suffix})"
        for view in views:
            for key in ("mtp_config", "multi_token_predictor"):
                if isinstance(view.get(key), Mapping):
                    return "native MTP configured"
            if view.get("use_mtp") is True:
                return "native MTP enabled"
            for key in ("draft_model", "draft_model_name", "draft_model_config"):
                value = view.get(key)
                if isinstance(value, str) and value.strip():
                    return f"draft model: {value.strip()[:120]}"
                if isinstance(value, Mapping):
                    return "draft model configured"
        return None

    @classmethod
    def _modalities(cls, config: Mapping[str, Any]) -> list[str]:
        values: list[str] = []
        explicit = config.get("modalities")
        if isinstance(explicit, list):
            values.extend(
                value.strip().lower()
                for value in explicit
                if isinstance(value, str) and value.strip()
            )
        if isinstance(config.get("text_config"), Mapping) or cls._architecture(config):
            values.append("text")
        if isinstance(config.get("vision_config"), Mapping) or any(
            key in config for key in ("image_token_id", "image_token_index")
        ):
            values.append("image")
        if isinstance(config.get("video_config"), Mapping) or any(
            key in config for key in ("video_token_id", "video_token_index")
        ):
            values.append("video")
        if isinstance(config.get("audio_config"), Mapping) or any(
            key in config for key in ("audio_token_id", "audio_token_index")
        ):
            values.append("audio")
        return list(dict.fromkeys(values or ["text"]))

    @classmethod
    def _model(
        cls, item: Mapping[str, Any]
    ) -> tuple[dict[str, Any] | None, list[str], bool]:
        config = item.get("config")
        safetensors = item.get("safetensors")
        if not isinstance(config, Mapping) and not isinstance(safetensors, Mapping):
            return None, [], False
        parsed_config: Mapping[str, Any] = config if isinstance(config, Mapping) else {}
        views = cls._config_views(parsed_config)
        model_id = str(item.get("id") or item.get("modelId") or "")
        active_parameters = cls._positive_int(
            views,
            ("active_parameters", "num_active_parameters", "active_parameter_count"),
        )
        config_total = cls._positive_int(
            views,
            ("total_parameters", "num_parameters", "parameter_count"),
        )
        notes: list[str] = []
        anomaly = False
        total_parameters: int | None = None
        hub_total = (
            safetensors.get("total") if isinstance(safetensors, Mapping) else None
        )
        if hub_total is not None:
            reason = cls._implausible_parameter_total(
                hub_total,
                model_id=model_id,
                config=parsed_config,
                active_parameters=active_parameters,
            )
            if reason is None:
                total_parameters = hub_total
            else:
                anomaly = True
                notes.append(
                    f"Rejected Hub safetensors.total={hub_total!r}: {reason}; "
                    "parameter count requires independent verification."
                )
        if total_parameters is None and config_total is not None:
            reason = cls._implausible_parameter_total(
                config_total,
                model_id=model_id,
                config=parsed_config,
                active_parameters=active_parameters,
            )
            if reason is None:
                total_parameters = config_total
                notes.append(
                    "Used the config-declared total parameter count; it was not "
                    "inferred from the repository name."
                )
            else:
                anomaly = True
                notes.append(
                    f"Rejected config-declared total_parameters={config_total!r}: "
                    f"{reason}."
                )
        if (
            active_parameters is not None
            and total_parameters is not None
            and active_parameters > total_parameters
        ):
            anomaly = True
            notes.append(
                "Rejected config-declared active parameter count because it exceeds "
                "the accepted total parameter count."
            )
            active_parameters = None
        return (
            {
                "architecture": cls._architecture(parsed_config),
                "total_parameters": total_parameters,
                "active_parameters": active_parameters,
                "context_tokens": cls._positive_int(
                    views,
                    (
                        "max_position_embeddings",
                        "max_sequence_length",
                        "seq_length",
                        "n_positions",
                    ),
                ),
                "modalities": cls._modalities(parsed_config),
                "mtp_or_draft": cls._mtp(parsed_config),
                "expert_count": cls._positive_int(
                    views,
                    (
                        "num_experts",
                        "num_local_experts",
                        "n_routed_experts",
                        "num_routed_experts",
                    ),
                ),
                "experts_per_token": cls._positive_int(
                    views,
                    (
                        "num_experts_per_tok",
                        "num_experts_per_token",
                        "moe_top_k",
                        "router_top_k",
                    ),
                ),
            },
            notes,
            anomaly,
        )

    def normalize(
        self, page: DiscoveryPage, *, raw_sha256: str
    ) -> list[dict[str, Any]]:
        """Normalize a HF detail/search page to a list of registry records."""
        records: list[dict[str, Any]] = []
        items = [page.payload] if isinstance(page.payload, Mapping) else page.payload
        for item in items:
            if not isinstance(item, Mapping):
                continue
            model_id = str(item.get("id") or item.get("modelId") or "").strip()
            if not _MODEL_ID.fullmatch(model_id):
                continue
            sha = str(item.get("sha") or "").strip()
            fallback = str(
                item.get("lastModified") or item.get("createdAt") or "mutable"
            )
            pinned = bool(_COMMIT_SHA.fullmatch(sha))
            revision = sha.lower() if pinned else fallback
            model, model_notes, model_anomaly = self._model(item)
            hydration = item.get("_pheno_config_hydration")
            hydration_status = (
                hydration.get("status") if isinstance(hydration, Mapping) else None
            )
            if hydration_status == "hydrated":
                hydration_note = (
                    "Pinned config.json metadata was hydrated at the resolved commit."
                )
            elif hydration_status == "missing":
                hydration_note = (
                    "Pinned config.json returned HTTP 404; the immutable Hub detail "
                    "was retained as incomplete."
                )
            else:
                hydration_note = (
                    "Hydrate pinned config.json, repository tree, card, and license "
                    "files before admission."
                )
            notes = [
                "Hub metadata only; no model artifacts were downloaded.",
                hydration_note,
                *model_notes,
            ]
            record = normalized_record(
                page=page,
                raw_sha256=raw_sha256,
                canonical_name=model_id,
                canonical_url=f"https://huggingface.co/{quote(model_id, safe='/')}",
                revision=revision,
                mutable=not pinned,
                aliases=[],
                released_at=item.get("createdAt"),
                declared_licenses=self._license(item),
                license_urls=[
                    "https://huggingface.co/"
                    f"{quote(model_id, safe='/')}/blob/"
                    f"{quote(revision, safe='')}/LICENSE"
                ],
                model=model,
                notes=notes,
            )
            if model_anomaly:
                record["quality"]["incomplete"] = True
                record["quality"]["confidence"] = "low"
            records.append(record)
        return records


__all__ = ["HuggingFaceAdapter"]
