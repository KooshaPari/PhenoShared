#!/usr/bin/env python3
"""Build a normalized, publication-safe Emergent Garden YouTube census.

Primary route: YouTube Data API v3 using YOUTUBE_API_KEY.
Fallback route: the official YouTube Atom channel feed, which is recent-window only.

The script never stores raw API responses or full video descriptions. It stores
metadata needed for provenance, coverage, and outbound-edge analysis: hashes,
lengths, short excerpts, chapters, and URLs.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable

CAMPAIGN_ID = "eg-nested-corpus-2026-09"
HANDLE = "@EmergentGarden"
EXPECTED_CHANNEL_ID = "UCwBhBDsqiQflTMLy2epbQVw"
EXPECTED_UPLOADS_PLAYLIST = "UUwBhBDsqiQflTMLy2epbQVw"
CHANNEL_URL = "https://www.youtube.com/@EmergentGarden/videos"
ATOM_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={EXPECTED_CHANNEL_ID}"
API_BASE = "https://www.googleapis.com/youtube/v3"
USER_AGENT = "ResearchLedger-EmergentGarden/1.0 (+https://github.com/KooshaPari/ResearchLedger)"
URL_RE = re.compile(r"https?://[^\s<>()\[\]{}\"']+")
CHAPTER_RE = re.compile(r"^\s*((?:\d{1,2}:)?\d{1,2}:\d{2})\s+(.+?)\s*$")
ISO_DURATION_RE = re.compile(
    r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def request_text(url: str, *, timeout: int = 30) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, application/atom+xml, text/xml;q=0.9, */*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8")


def request_json(url: str) -> dict[str, Any]:
    return json.loads(request_text(url))


def api_get(resource: str, params: dict[str, Any], api_key: str) -> dict[str, Any]:
    clean = {key: str(value) for key, value in params.items() if value is not None}
    clean["key"] = api_key
    return request_json(f"{API_BASE}/{resource}?{urllib.parse.urlencode(clean)}")


def chunks(values: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_url(raw: str) -> str:
    candidate = html.unescape(raw).rstrip(".,;:!?)]}")
    parsed = urllib.parse.urlsplit(candidate)
    if parsed.netloc.lower() in {"www.youtube.com", "youtube.com"} and parsed.path == "/redirect":
        query = urllib.parse.parse_qs(parsed.query)
        redirected = (query.get("q") or query.get("url") or [None])[0]
        if redirected:
            candidate = redirected
            parsed = urllib.parse.urlsplit(candidate)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query_pairs = [(key, value) for key, value in query_pairs if not key.lower().startswith("utm_")]
    return urllib.parse.urlunsplit(
        (
            parsed.scheme.lower(),
            host,
            parsed.path or "/",
            urllib.parse.urlencode(sorted(query_pairs)),
            "",
        )
    )


def classify_url(url: str) -> str:
    host = urllib.parse.urlsplit(url).netloc.lower()
    if host == "github.com" or host.endswith(".github.com"):
        return "IMPLEMENTATION_CANDIDATE"
    if host in {"arxiv.org", "doi.org"} or host.endswith(".acm.org") or host.endswith(".ieee.org"):
        return "PRIMARY_SOURCE_CANDIDATE"
    if host in {"emergentgarden.io", "evolvecode.io", "neuralpatterns.io"}:
        return "AUTHOR_DIRECT"
    if host in {"youtube.com", "youtu.be"}:
        return "YOUTUBE_RELATED"
    if host in {
        "discord.gg",
        "patreon.com",
        "ko-fi.com",
        "twitter.com",
        "x.com",
        "bsky.app",
    }:
        return "COMMUNITY_OR_SOCIAL"
    return "CONTEXT_CANDIDATE"


def extract_urls(description: str) -> list[dict[str, str]]:
    seen: set[str] = set()
    rows: list[dict[str, str]] = []
    for match in URL_RE.finditer(description):
        original = match.group(0).rstrip(".,;:!?)]}")
        canonical = normalize_url(original)
        if canonical in seen:
            continue
        seen.add(canonical)
        rows.append(
            {
                "original_url": original,
                "canonical_url": canonical,
                "domain": urllib.parse.urlsplit(canonical).netloc.lower(),
                "edge_class": classify_url(canonical),
            }
        )
    return rows


def parse_chapters(description: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in description.splitlines():
        match = CHAPTER_RE.match(line)
        if not match:
            continue
        stamp, title = match.groups()
        pieces = [int(value) for value in stamp.split(":")]
        seconds = pieces[0] * 60 + pieces[1] if len(pieces) == 2 else pieces[0] * 3600 + pieces[1] * 60 + pieces[2]
        rows.append({"timestamp": stamp, "offset_seconds": seconds, "title": title})
    return rows


def parse_duration(value: str | None) -> int | None:
    if not value:
        return None
    match = ISO_DURATION_RE.match(value)
    if not match:
        return None
    parts = {key: int(item or 0) for key, item in match.groupdict().items()}
    return parts["days"] * 86400 + parts["hours"] * 3600 + parts["minutes"] * 60 + parts["seconds"]


def description_record(description: str) -> dict[str, Any]:
    compact = " ".join(description.split())
    return {
        "sha256": sha256_text(description),
        "character_count": len(description),
        "line_count": len(description.splitlines()),
        "excerpt": compact[:280],
        "chapters": parse_chapters(description),
        "outbound_links": extract_urls(description),
    }


def api_inventory(api_key: str) -> dict[str, Any]:
    channel_payload = api_get(
        "channels",
        {
            "part": "snippet,contentDetails,statistics,status",
            "forHandle": HANDLE,
            "maxResults": 1,
        },
        api_key,
    )
    items = channel_payload.get("items") or []
    if len(items) != 1:
        raise RuntimeError(f"channels.list returned {len(items)} items for {HANDLE}")
    channel = items[0]
    channel_id = channel.get("id")
    if channel_id != EXPECTED_CHANNEL_ID:
        raise RuntimeError(f"handle resolved to {channel_id!r}, expected {EXPECTED_CHANNEL_ID!r}")
    uploads = (((channel.get("contentDetails") or {}).get("relatedPlaylists") or {}).get("uploads"))
    if not uploads:
        raise RuntimeError("channels.list did not return the uploads playlist")

    playlist_rows: list[dict[str, Any]] = []
    page_token: str | None = None
    while True:
        payload = api_get(
            "playlistItems",
            {
                "part": "snippet,contentDetails,status",
                "playlistId": uploads,
                "maxResults": 50,
                "pageToken": page_token,
            },
            api_key,
        )
        playlist_rows.extend(payload.get("items") or [])
        page_token = payload.get("nextPageToken")
        if not page_token:
            break

    playlist_ids: list[str] = []
    position_by_id: dict[str, int] = {}
    for row in playlist_rows:
        video_id = ((row.get("contentDetails") or {}).get("videoId")) or (
            (((row.get("snippet") or {}).get("resourceId") or {}).get("videoId"))
        )
        if not video_id:
            continue
        playlist_ids.append(video_id)
        position_by_id[video_id] = int((row.get("snippet") or {}).get("position", len(position_by_id)))

    details: dict[str, dict[str, Any]] = {}
    for batch in chunks(playlist_ids, 50):
        payload = api_get(
            "videos",
            {
                "part": "snippet,contentDetails,status,topicDetails,liveStreamingDetails",
                "id": ",".join(batch),
                "maxResults": 50,
            },
            api_key,
        )
        for row in payload.get("items") or []:
            details[row["id"]] = row

    missing_details = [video_id for video_id in playlist_ids if video_id not in details]
    videos: list[dict[str, Any]] = []
    for video_id in playlist_ids:
        row = details.get(video_id)
        if not row:
            continue
        snippet = row.get("snippet") or {}
        content_details = row.get("contentDetails") or {}
        status = row.get("status") or {}
        description = snippet.get("description") or ""
        videos.append(
            {
                "playlist_position": position_by_id.get(video_id),
                "video_id": video_id,
                "canonical_url": f"https://www.youtube.com/watch?v={video_id}",
                "title": snippet.get("title"),
                "published_at": snippet.get("publishedAt"),
                "channel_id": snippet.get("channelId"),
                "category_id": snippet.get("categoryId"),
                "default_language": snippet.get("defaultLanguage"),
                "default_audio_language": snippet.get("defaultAudioLanguage"),
                "live_broadcast_content": snippet.get("liveBroadcastContent"),
                "tags": sorted(snippet.get("tags") or [], key=str.casefold),
                "duration_iso8601": content_details.get("duration"),
                "duration_seconds": parse_duration(content_details.get("duration")),
                "caption_available": content_details.get("caption") == "true",
                "definition": content_details.get("definition"),
                "dimension": content_details.get("dimension"),
                "projection": content_details.get("projection"),
                "licensed_content": content_details.get("licensedContent"),
                "privacy_status": status.get("privacyStatus"),
                "upload_status": status.get("uploadStatus"),
                "made_for_kids": status.get("madeForKids"),
                "self_declared_made_for_kids": status.get("selfDeclaredMadeForKids"),
                "topic_categories": sorted((row.get("topicDetails") or {}).get("topicCategories") or []),
                "description": description_record(description),
            }
        )

    videos.sort(key=lambda value: ((value.get("published_at") or ""), value["video_id"]), reverse=True)
    channel_snippet = channel.get("snippet") or {}
    channel_statistics = channel.get("statistics") or {}
    return {
        "provider": "youtube_data_api_v3",
        "inventory_complete": len(missing_details) == 0,
        "gate_state": "PASS" if len(missing_details) == 0 else "PARTIAL",
        "limit_reason": None
        if len(missing_details) == 0
        else "playlist items returned without public videos.list details",
        "channel": {
            "channel_id": channel_id,
            "handle": HANDLE,
            "title": channel_snippet.get("title"),
            "description_sha256": sha256_text(channel_snippet.get("description") or ""),
            "uploads_playlist_id": uploads,
            "reported_public_video_count": int(channel_statistics.get("videoCount", len(videos))),
            "hidden_subscriber_count": bool(channel_statistics.get("hiddenSubscriberCount")),
            "country": channel_snippet.get("country"),
            "custom_url": channel_snippet.get("customUrl"),
        },
        "playlist_item_count": len(playlist_ids),
        "video_detail_count": len(videos),
        "missing_video_details": missing_details,
        "videos": videos,
    }


def atom_inventory() -> dict[str, Any]:
    root = ET.fromstring(request_text(ATOM_URL))
    namespaces = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }
    videos: list[dict[str, Any]] = []
    for position, entry in enumerate(root.findall("atom:entry", namespaces)):
        video_id = (entry.findtext("yt:videoId", default="", namespaces=namespaces) or "").strip()
        group = entry.find("media:group", namespaces)
        description = ""
        if group is not None:
            description = group.findtext("media:description", default="", namespaces=namespaces)
        videos.append(
            {
                "playlist_position": position,
                "video_id": video_id,
                "canonical_url": f"https://www.youtube.com/watch?v={video_id}",
                "title": entry.findtext("atom:title", default="", namespaces=namespaces),
                "published_at": entry.findtext("atom:published", default="", namespaces=namespaces),
                "channel_id": EXPECTED_CHANNEL_ID,
                "category_id": None,
                "default_language": None,
                "default_audio_language": None,
                "live_broadcast_content": None,
                "tags": [],
                "duration_iso8601": None,
                "duration_seconds": None,
                "caption_available": None,
                "definition": None,
                "dimension": None,
                "projection": None,
                "licensed_content": None,
                "privacy_status": "public",
                "upload_status": None,
                "made_for_kids": None,
                "self_declared_made_for_kids": None,
                "topic_categories": [],
                "description": description_record(description),
            }
        )
    videos.sort(key=lambda value: ((value.get("published_at") or ""), value["video_id"]), reverse=True)
    return {
        "provider": "youtube_atom_channel_feed",
        "inventory_complete": False,
        "gate_state": "BLOCKED",
        "limit_reason": (
            "YOUTUBE_API_KEY was unavailable; the official Atom channel feed exposes only a recent "
            "window and cannot establish the complete uploads census."
        ),
        "channel": {
            "channel_id": EXPECTED_CHANNEL_ID,
            "handle": HANDLE,
            "title": root.findtext("atom:title", default="Emergent Garden", namespaces=namespaces),
            "description_sha256": None,
            "uploads_playlist_id": EXPECTED_UPLOADS_PLAYLIST,
            "reported_public_video_count": None,
            "hidden_subscriber_count": None,
            "country": None,
            "custom_url": None,
        },
        "playlist_item_count": len(videos),
        "video_detail_count": len(videos),
        "missing_video_details": [],
        "videos": videos,
    }


def build_text_coverage(inventory: dict[str, Any], generated_at: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for video in inventory["videos"]:
        description = video["description"]
        rows.append(
            {
                "video_id": video["video_id"],
                "title": video.get("title"),
                "published_at": video.get("published_at"),
                "description_present": description["character_count"] > 0,
                "description_character_count": description["character_count"],
                "description_sha256": description["sha256"],
                "chapter_count": len(description["chapters"]),
                "outbound_link_count": len(description["outbound_links"]),
                "caption_available": video.get("caption_available"),
                "transcript_state": "UNACQUIRED",
                "allowed_transcript_routes": [
                    "creator_supplied",
                    "first_party_licensed",
                    "permissioned_export",
                    "manual_youtube_ui",
                    "operator_notes",
                    "local_asr_supplied_media",
                ],
                "prohibited_routes": [
                    "unattended_youtube_scrape",
                    "undocumented_transcript_endpoint",
                    "browser_cookie_extraction",
                    "video_or_audio_download",
                ],
            }
        )
    captions = [row["caption_available"] for row in rows]
    return {
        "schema_version": "1.0",
        "campaign_id": CAMPAIGN_ID,
        "generated_at": generated_at,
        "provider": inventory["provider"],
        "inventory_complete": inventory["inventory_complete"],
        "summary": {
            "videos": len(rows),
            "descriptions_present": sum(bool(row["description_present"]) for row in rows),
            "videos_with_chapters": sum(row["chapter_count"] > 0 for row in rows),
            "videos_with_outbound_links": sum(row["outbound_link_count"] > 0 for row in rows),
            "caption_available_true": sum(value is True for value in captions),
            "caption_available_false": sum(value is False for value in captions),
            "caption_availability_unknown": sum(value is None for value in captions),
            "transcripts_acquired": 0,
        },
        "videos": rows,
    }


def build_edges(inventory: dict[str, Any], generated_at: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for video in inventory["videos"]:
        for link in video["description"]["outbound_links"]:
            rows.append(
                {
                    "from_type": "youtube_video",
                    "from_video_id": video["video_id"],
                    "from_title": video.get("title"),
                    "from_published_at": video.get("published_at"),
                    "edge_class": link["edge_class"],
                    "original_url": link["original_url"],
                    "canonical_url": link["canonical_url"],
                    "domain": link["domain"],
                    "verification_state": "DISCOVERED_NOT_EXPANDED",
                }
            )
    rows.sort(
        key=lambda row: (
            row["from_published_at"] or "",
            row["from_video_id"],
            row["canonical_url"],
        ),
        reverse=True,
    )
    domain_counts = collections.Counter(row["domain"] for row in rows)
    class_counts = collections.Counter(row["edge_class"] for row in rows)
    return {
        "schema_version": "1.0",
        "campaign_id": CAMPAIGN_ID,
        "generated_at": generated_at,
        "provider": inventory["provider"],
        "inventory_complete": inventory["inventory_complete"],
        "summary": {
            "edges": len(rows),
            "unique_targets": len({row["canonical_url"] for row in rows}),
            "unique_domains": len(domain_counts),
            "domain_counts": dict(sorted(domain_counts.items(), key=lambda item: (-item[1], item[0]))),
            "edge_class_counts": dict(sorted(class_counts.items(), key=lambda item: (-item[1], item[0]))),
        },
        "edges": rows,
    }


def markdown_escape(value: Any) -> str:
    return str(value if value is not None else "—").replace("|", "\\|").replace("\n", " ")


def format_seconds(seconds: int | None) -> str:
    if seconds is None:
        return "—"
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"


def build_report(
    inventory: dict[str, Any],
    coverage: dict[str, Any],
    edges: dict[str, Any],
    generated_at: str,
) -> str:
    complete = inventory["inventory_complete"]
    lines = [
        "# Emergent Garden YouTube Census — Wave 2",
        "",
        f"**Campaign:** `{CAMPAIGN_ID}`  ",
        f"**Captured:** {generated_at}  ",
        f"**Provider:** `{inventory['provider']}`  ",
        f"**G1 inventory gate:** **{'PASS' if complete else 'BLOCKED'}**  ",
        f"**Official uploads playlist:** `{inventory['channel']['uploads_playlist_id']}`  ",
        f"**Inventory complete:** **{'yes' if complete else 'no'}**",
        "",
        "## Verdict",
        "",
    ]
    if complete:
        lines.extend(
            [
                (
                    f"The official uploads playlist resolved to {len(inventory['videos'])} public video "
                    "records. The census is normalized from `channels.list`, `playlistItems.list`, and "
                    "batched `videos.list` responses; raw API payloads are not committed."
                ),
                "",
            ]
        )
    else:
        lines.extend(
            [
                (
                    "The complete census is not established. The committed records come from YouTube's "
                    "official Atom channel feed and therefore represent only its recent window."
                ),
                "",
                f"**Blocking reason:** {inventory['limit_reason']}",
                "",
                "Do not treat the row count below as the channel's total upload count.",
                "",
            ]
        )

    summary = coverage["summary"]
    lines.extend(
        [
            "## Coverage",
            "",
            "| Measure | Count |",
            "|---|---:|",
            f"| Normalized video records | {summary['videos']} |",
            f"| Non-empty descriptions | {summary['descriptions_present']} |",
            f"| Videos with parsed chapters | {summary['videos_with_chapters']} |",
            f"| Videos with outbound links | {summary['videos_with_outbound_links']} |",
            f"| Caption signal: yes | {summary['caption_available_true']} |",
            f"| Caption signal: no | {summary['caption_available_false']} |",
            f"| Caption signal: unknown | {summary['caption_availability_unknown']} |",
            f"| Transcript text acquired | {summary['transcripts_acquired']} |",
            f"| Description outbound edges | {edges['summary']['edges']} |",
            f"| Unique outbound targets | {edges['summary']['unique_targets']} |",
            "",
            (
                "Descriptions are represented by SHA-256, length, a short excerpt, parsed chapter lines, "
                "and outbound URLs. Full descriptions and raw API responses are deliberately omitted."
            ),
            "",
            "## Upload inventory",
            "",
            "| Published | Video | Duration | Captions | Description chars | Chapters | Links |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for video in inventory["videos"]:
        published = (video.get("published_at") or "")[:10] or "—"
        title = f"[{markdown_escape(video.get('title'))}]({video['canonical_url']})"
        caption = video.get("caption_available")
        caption_text = "yes" if caption is True else "no" if caption is False else "unknown"
        description = video["description"]
        lines.append(
            f"| {published} | {title} | {format_seconds(video.get('duration_seconds'))} | "
            f"{caption_text} | {description['character_count']} | "
            f"{len(description['chapters'])} | {len(description['outbound_links'])} |"
        )

    domain_counts = edges["summary"]["domain_counts"]
    lines.extend(["", "## Description-link frontier", ""])
    if domain_counts:
        lines.extend(["| Domain | Discovered edges |", "|---|---:|"])
        for domain, count in list(domain_counts.items())[:40]:
            lines.append(f"| `{markdown_escape(domain)}` | {count} |")
    else:
        lines.append("No outbound links were exposed by the current provider window.")

    lines.extend(
        [
            "",
            "## G2 text-coverage state",
            "",
            "- description metadata: normalized for every returned record;",
            "- chapter lines: parsed when present;",
            "- caption availability: recorded only when `videos.list` exposes the signal;",
            "- transcript text: unacquired;",
            (
                "- permitted future routes: creator-supplied, first-party licensed, permissioned export, "
                "manual YouTube UI, operator notes, or ASR over media supplied by the operator;"
            ),
            (
                "- prohibited routes remain unattended YouTube scraping, undocumented transcript "
                "endpoints, cookie extraction, and audiovisual downloading."
            ),
            "",
            "## Alternative explanations and failure modes",
            "",
            (
                "1. Playlist count can differ from the channel statistics count because deleted, private, "
                "upcoming, live, or recently indexed records may not resolve identically."
            ),
            (
                "2. `contentDetails.caption` is a coarse availability signal, not proof that a legally "
                "retrievable transcript exists for this campaign."
            ),
            (
                "3. A URL in a creator description establishes a direct outbound edge, not endorsement of "
                "every claim at the target and not proof of repository lineage."
            ),
            (
                "4. An Atom-feed row set can be internally correct while still being an incomplete channel "
                "census."
            ),
            (
                "5. Missing links may reflect description edits, shortened URLs, client-rendered content, "
                "or provider-field limitations rather than true absence."
            ),
            "",
            "## Gate transition",
            "",
        ]
    )
    if complete:
        lines.append(
            "`G1_INVENTORY` may advance to pass after independent count and duplicate reconciliation. "
            "`G2_TEXT_COVERAGE` remains partial until the permitted transcript matrix is reviewed."
        )
    else:
        lines.append(
            "`G1_INVENTORY` remains blocked until a YouTube Data API v3 key is available to enumerate "
            "and reconcile the complete official uploads playlist. `G2_TEXT_COVERAGE` cannot be promoted "
            "from the recent-window sample."
        )
    lines.append("")
    return "\n".join(lines)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default="docs/corpora/emergent-garden")
    args = parser.parse_args()
    root = Path(args.output_root)
    generated_at = now_utc()
    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()

    mode = "youtube_data_api_v3" if api_key else "youtube_atom_channel_feed"
    try:
        inventory_body = api_inventory(api_key) if api_key else atom_inventory()
        acquisition_error = None
    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        TimeoutError,
        RuntimeError,
        ValueError,
        ET.ParseError,
    ) as error:
        if not api_key:
            print(f"Atom acquisition failed: {error}", file=sys.stderr)
            return 1
        try:
            inventory_body = atom_inventory()
            inventory_body["gate_state"] = "BLOCKED"
            inventory_body["limit_reason"] = (
                f"YouTube Data API acquisition failed ({type(error).__name__}: {error}); "
                "official Atom recent-window fallback used."
            )
            acquisition_error = f"{type(error).__name__}: {error}"
            mode = "youtube_data_api_v3_failed_atom_fallback"
        except Exception as fallback_error:  # noqa: BLE001 - preserve both failure modes
            print(f"API and Atom fallback failed: {error}; {fallback_error}", file=sys.stderr)
            return 1

    inventory = {
        "schema_version": "1.0",
        "campaign_id": CAMPAIGN_ID,
        "generated_at": generated_at,
        "requested_handle": HANDLE,
        "channel_url": CHANNEL_URL,
        "expected_channel_id": EXPECTED_CHANNEL_ID,
        "expected_uploads_playlist_id": EXPECTED_UPLOADS_PLAYLIST,
        "acquisition_mode": mode,
        "api_key_present": bool(api_key),
        "acquisition_error": acquisition_error,
        **inventory_body,
    }
    coverage = build_text_coverage(inventory, generated_at)
    edges = build_edges(inventory, generated_at)
    report = build_report(inventory, coverage, edges, generated_at)
    status = {
        "schema_version": "1.0",
        "campaign_id": CAMPAIGN_ID,
        "generated_at": generated_at,
        "gate": "G1_INVENTORY",
        "state": inventory["gate_state"],
        "provider": inventory["provider"],
        "inventory_complete": inventory["inventory_complete"],
        "normalized_video_count": len(inventory["videos"]),
        "blocking_reason": inventory["limit_reason"],
        "api_key_present": bool(api_key),
        "next_action": (
            "reconcile playlist count, duplicates, and text coverage"
            if inventory["inventory_complete"]
            else "provide YOUTUBE_API_KEY through repository secrets and rerun the workflow"
        ),
    }

    write_json(root / "data" / "youtube-channel-inventory-v1.json", inventory)
    write_json(root / "data" / "youtube-text-coverage-v1.json", coverage)
    write_json(root / "data" / "youtube-description-edges-v1.json", edges)
    write_json(root / "data" / "youtube-census-status-v1.json", status)
    report_path = root / "research" / "YOUTUBE-CENSUS-WAVE-2.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    print(json.dumps(status, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
