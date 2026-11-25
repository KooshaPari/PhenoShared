"""arXiv Atom API discovery with mandatory pacing and version awareness."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ElementTree  # nosec B405
from dataclasses import replace
from typing import Any

from .base import DiscoveryPage, MetadataClient, normalized_record, with_retry

_ATOM = "{http://www.w3.org/2005/Atom}"
_OPENSEARCH = "{http://a9.com/-/spec/opensearch/1.1/}"
_ARXIV_ID = re.compile(
    r"^(?P<base>\d{2}(?:0[1-9]|1[0-2])\.\d{4,5})(?:v(?P<version>[1-9]\d*))?$"
)
_VERSIONED_ID = re.compile(r"^\d{2}(?:0[1-9]|1[0-2])\.\d{4,5}v[1-9]\d*$")


class ArxivAdapter:
    """arXiv Atom API discovery adapter.

    Search and resolve_paper return DiscoveryPages; normalize() turns
    each page into one or more registry records (one per <entry>).

    Satisfies the SourceAdapter Protocol (kind, endpoint, search,
    normalize). Does NOT satisfy CandidateExtractor — arXiv search
    pages are typically narrow queries, not bulk enumerations.
    """

    kind = "arxiv"
    endpoint = "https://export.arxiv.org/api/query"

    def __init__(self, client: MetadataClient) -> None:
        """Initialize the adapter with the shared metadata client."""

        self.client = client

    @with_retry()
    def search(
        self,
        query: str,
        *,
        start: int = 0,
        max_results: int = 25,
        sort_by: str = "submittedDate",
        sort_order: str = "descending",
    ) -> DiscoveryPage:
        """Run an arXiv Atom-API query and return a DiscoveryPage."""
        if not query.strip() or start < 0 or not 1 <= max_results <= 2000:
            raise ValueError(
                "arXiv search requires a query, nonnegative start, and 1..2000 results"
            )
        if sort_by not in {"relevance", "lastUpdatedDate", "submittedDate"}:
            raise ValueError("unsupported arXiv sortBy")
        if sort_order not in {"ascending", "descending"}:
            raise ValueError("unsupported arXiv sortOrder")
        page = self.client.request(
            source_kind=self.kind,
            method="GET",
            url=self.endpoint,
            params={
                "search_query": query,
                "start": start,
                "max_results": max_results,
                "sortBy": sort_by,
                "sortOrder": sort_order,
            },
            minimum_interval=3.0,
        )
        root = self._root(page)
        total_text = root.findtext(f"{_OPENSEARCH}totalResults") or "0"
        try:
            total = int(total_text)
        except ValueError:
            total = 0
        return replace(page, incomplete=(start + max_results < total))

    @with_retry()
    def resolve_paper(self, paper_id: str) -> DiscoveryPage:
        """Resolve one modern arXiv base/versioned ID through ``id_list``."""

        requested = self._validated_id(paper_id)
        page = self.client.request(
            source_kind=self.kind,
            method="GET",
            url=self.endpoint,
            params={"id_list": requested, "start": 0, "max_results": 1},
            minimum_interval=3.0,
        )
        entries = self._root(page).findall(f"{_ATOM}entry")
        if len(entries) != 1:
            raise ValueError(
                f"arXiv resolution expected exactly one entry, received {len(entries)}"
            )
        returned = self._entry_id(entries[0])
        returned_match = _ARXIV_ID.fullmatch(returned)
        if returned_match is None:
            raise ValueError("arXiv resolution returned a malformed modern identifier")
        requested_match = _ARXIV_ID.fullmatch(requested)
        assert requested_match is not None  # nosec B101
        if returned_match.group("base") != requested_match.group("base"):
            raise ValueError("arXiv resolution identity mismatch")
        if requested_match.group("version") is not None and returned != requested:
            raise ValueError("arXiv resolution version mismatch")
        return replace(page, incomplete=False)

    @staticmethod
    def _validated_id(paper_id: str) -> str:
        if not isinstance(paper_id, str) or _ARXIV_ID.fullmatch(paper_id) is None:
            raise ValueError(
                "arXiv paper id must be a modern base or versioned id such as "
                "2603.03251 or 2603.03251v2"
            )
        return paper_id

    @staticmethod
    def _entry_id(entry: ElementTree.Element) -> str:
        raw_id = (entry.findtext(f"{_ATOM}id") or "").strip().rstrip("/")
        return raw_id.rsplit("/", 1)[-1]

    @staticmethod
    def _root(page: DiscoveryPage) -> ElementTree.Element:
        if not isinstance(page.payload, str):
            raise ValueError("arXiv response must be Atom XML text")
        try:
            # bandit: arXiv returns external (untrusted) Atom XML; the
            # stdlib ElementTree is vulnerable to billion-laughs and
            # external-entity attacks on untrusted input. The
            # `_ATOM`/`_OPENSEARCH`/`_ARXIV_ID` parsers below only
            # read element text, not entities or DTDs, so this is
            # safe — but document the audit callout.
            return ElementTree.fromstring(page.payload)  # nosec B314
        except ElementTree.ParseError as exc:
            raise ValueError("arXiv returned invalid Atom XML") from exc

    def normalize(
        self, page: DiscoveryPage, *, raw_sha256: str
    ) -> list[dict[str, Any]]:
        """Normalize an arXiv search DiscoveryPage to one record per <entry>."""
        records: list[dict[str, Any]] = []
        for entry in self._root(page).findall(f"{_ATOM}entry"):
            arxiv_id = self._entry_id(entry)
            if not arxiv_id:
                continue
            title = " ".join((entry.findtext(f"{_ATOM}title") or "").split())
            versioned = bool(_VERSIONED_ID.fullmatch(arxiv_id))
            revision = arxiv_id
            license_urls = [
                str(link.attrib["href"])
                for link in entry.findall(f"{_ATOM}link")
                if link.attrib.get("rel") == "license" and link.attrib.get("href")
            ]
            categories = [
                str(node.attrib["term"])
                for node in entry.findall(f"{_ATOM}category")
                if node.attrib.get("term")
            ]
            notes = [f"Title: {title}"] if title else []
            if categories:
                notes.append("Categories: " + ", ".join(categories))
            records.append(
                normalized_record(
                    page=page,
                    raw_sha256=raw_sha256,
                    canonical_name=arxiv_id,
                    canonical_url=f"https://arxiv.org/abs/{arxiv_id}",
                    revision=revision,
                    mutable=not versioned,
                    aliases=[title] if title else [],
                    released_at=entry.findtext(f"{_ATOM}published"),
                    declared_licenses=[],
                    license_urls=license_urls,
                    notes=notes,
                )
            )
        return records


__all__ = ["ArxivAdapter"]
