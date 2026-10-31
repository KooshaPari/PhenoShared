#!/usr/bin/env python3
"""Reconciled official-API census; v1 is reused only for pure export helpers.

No Atom fallback on a credentialed failure. No credentials or raw API bodies
are persisted. A complete result means two matching public API observations,
not access to private/deleted/unlisted history or to caption text.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CHANNEL_ID = "UCwBhBDsqiQflTMLy2epbQVw"
UPLOADS_ID = "UUwBhBDsqiQflTMLy2epbQVw"
HANDLE = "@EmergentGarden"
MAX_PAGES = 20
MAX_REQUESTS = 48
MAX_BYTES = 2_000_000
VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}\Z")


class AcquisitionError(RuntimeError):
    """Messages are fixed codes, never raw URLs, response bodies or secrets."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AcquisitionError("API_REDIRECT_REFUSED")


class ApiClient:
    def __init__(self, key: str):
        if not key:
            raise AcquisitionError("API_KEY_MISSING")
        self._key = key
        self.audit: list[dict] = []
        self.opener = urllib.request.build_opener(NoRedirect())

    def __call__(self, resource: str, params: dict) -> dict:
        if resource not in {"channels", "playlistItems", "videos"}:
            raise AcquisitionError("RESOURCE_NOT_ALLOWED")
        clean = {k: str(v) for k, v in params.items() if v is not None}
        if "key" in clean:
            raise AcquisitionError("KEY_PARAMETER_NOT_ALLOWED")
        query = urllib.parse.urlencode({**clean, "key": self._key})
        url = f"https://www.googleapis.com/youtube/v3/{resource}?{query}"
        for attempt in range(3):
            if len(self.audit) >= MAX_REQUESTS:
                raise AcquisitionError("REQUEST_BUDGET_EXCEEDED")
            record = {"resource": resource, "parameters": clean, "attempt": attempt + 1}
            self.audit.append(record)
            try:
                req = urllib.request.Request(url, headers={
                    "Accept": "application/json",
                    "User-Agent": "ResearchLedger-EmergentGarden/2.0",
                })
                with self.opener.open(req, timeout=30) as response:
                    body = response.read(MAX_BYTES + 1)
                    record["http_status"] = response.status
                if len(body) > MAX_BYTES:
                    raise AcquisitionError("API_BODY_LIMIT_EXCEEDED")
                record["response_sha256"] = hashlib.sha256(body).hexdigest()
                payload = json.loads(body)
                if not isinstance(payload, dict) or "error" in payload:
                    raise AcquisitionError("API_RESPONSE_INVALID")
                return payload
            except urllib.error.HTTPError as exc:
                record["http_status"] = exc.code
                if exc.code in {429, 500, 502, 503, 504} and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise AcquisitionError(f"API_HTTP_{exc.code}") from None
            except (urllib.error.URLError, TimeoutError, OSError):
                raise AcquisitionError("API_TRANSPORT_FAILURE") from None
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise AcquisitionError("API_JSON_INVALID") from None
        raise AcquisitionError("API_RETRY_EXHAUSTED")


def get_channel(api) -> dict:
    payload = api("channels", {
        "part": "snippet,contentDetails,statistics", "forHandle": HANDLE, "maxResults": 1,
    })
    items = payload.get("items") or []
    if len(items) != 1 or items[0].get("id") != CHANNEL_ID:
        raise AcquisitionError("CHANNEL_IDENTITY_MISMATCH")
    channel = items[0]
    uploads = channel.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    if uploads != UPLOADS_ID:
        raise AcquisitionError("UPLOADS_IDENTITY_MISMATCH")
    return channel


def count_of(channel: dict) -> int | None:
    value = channel.get("statistics", {}).get("videoCount")
    return int(value) if str(value).isdigit() else None


def enumerate_uploads(api) -> tuple[list[dict], list[dict], list[str]]:
    rows, pages, faults = [], [], []
    token, seen = None, set()
    for number in range(1, MAX_PAGES + 1):
        if token in seen:
            raise AcquisitionError("PAGINATION_TOKEN_CYCLE")
        seen.add(token)
        payload = api("playlistItems", {
            "part": "snippet,contentDetails,status", "playlistId": UPLOADS_ID,
            "maxResults": 50, "pageToken": token,
        })
        items = payload.get("items")
        if not isinstance(items, list):
            raise AcquisitionError("PLAYLIST_ITEMS_INVALID")
        if any(not isinstance(row, dict) for row in items):
            raise AcquisitionError("PLAYLIST_ROW_INVALID")
        total = payload.get("pageInfo", {}).get("totalResults")
        pages.append({"page": number, "rows": len(items), "reported_total": total})
        rows.extend(items)
        token = payload.get("nextPageToken")
        if not token:
            totals = [page["reported_total"] for page in pages]
            if any(not isinstance(t, int) or isinstance(t, bool) for t in totals):
                faults.append("PLAYLIST_TOTAL_MISSING")
            elif len(set(totals)) != 1 or totals[0] != len(rows):
                faults.append("PLAYLIST_TOTAL_MISMATCH")
            return rows, pages, faults
        if not isinstance(token, str):
            raise AcquisitionError("PAGINATION_TOKEN_INVALID")
    raise AcquisitionError("PAGE_BUDGET_EXCEEDED")


def index_uploads(rows: list[dict]) -> tuple[list[str], dict[str, int], dict]:
    ids, positions, invalid = [], {}, []
    for index, row in enumerate(rows):
        snippet = row.get("snippet") or {}
        video_id = (row.get("contentDetails") or {}).get("videoId")
        video_id = video_id or (snippet.get("resourceId") or {}).get("videoId")
        if not isinstance(video_id, str) or not VIDEO_ID.fullmatch(video_id):
            invalid.append({"row_index": index, "reason": "MISSING_OR_INVALID_VIDEO_ID"})
            continue
        ids.append(video_id)
        positions.setdefault(video_id, snippet.get("position", index))
    counts = collections.Counter(ids)
    return list(dict.fromkeys(ids)), positions, {
        "raw_rows": len(rows), "valid_id_rows": len(ids),
        "unique_ids": len(counts), "invalid_rows": invalid,
        "duplicates": {key: value for key, value in counts.items() if value > 1},
    }


def normalize_video(row: dict, position, describe, duration) -> dict:
    snippet, content, status = (row.get(k) or {} for k in ("snippet", "contentDetails", "status"))
    caption = content.get("caption")
    return {
        "playlist_position": position, "video_id": row["id"],
        "canonical_url": f"https://www.youtube.com/watch?v={row['id']}",
        "title": snippet.get("title"), "published_at": snippet.get("publishedAt"),
        "channel_id": snippet.get("channelId"), "category_id": snippet.get("categoryId"),
        "default_language": snippet.get("defaultLanguage"),
        "default_audio_language": snippet.get("defaultAudioLanguage"),
        "live_broadcast_content": snippet.get("liveBroadcastContent"),
        "tags": sorted(snippet.get("tags") or [], key=str.casefold),
        "duration_iso8601": content.get("duration"),
        "duration_seconds": duration(content.get("duration")),
        "caption_available": caption == "true" if caption in {"true", "false"} else None,
        "definition": content.get("definition"), "dimension": content.get("dimension"),
        "projection": content.get("projection"), "licensed_content": content.get("licensedContent"),
        "privacy_status": status.get("privacyStatus"), "upload_status": status.get("uploadStatus"),
        "made_for_kids": status.get("madeForKids"),
        "self_declared_made_for_kids": status.get("selfDeclaredMadeForKids"),
        "topic_categories": sorted((row.get("topicDetails") or {}).get("topicCategories") or []),
        "description": describe(snippet.get("description") or ""),
    }


def collect(api, describe, duration) -> dict:
    before = get_channel(api)
    rows, pages, faults = enumerate_uploads(api)
    ids, positions, first = index_uploads(rows)
    details = {}
    duplicate_details, unexpected_details = [], []
    for start in range(0, len(ids), 50):
        batch = ids[start:start + 50]
        payload = api("videos", {
            "part": "snippet,contentDetails,status,topicDetails,liveStreamingDetails", "id": ",".join(batch),
        })
        items = payload.get("items")
        if not isinstance(items, list):
            raise AcquisitionError("VIDEO_DETAILS_INVALID")
        for row in items:
            video_id = row.get("id")
            if video_id not in batch:
                unexpected_details.append(video_id)
                continue
            if video_id in details:
                duplicate_details.append(video_id)
            details[video_id] = row
    # Independent second enumeration catches many same-count concurrent edits.
    again_rows, again_pages, again_faults = enumerate_uploads(api)
    again_ids, _, second = index_uploads(again_rows)
    after = get_channel(api)
    faults.extend(again_faults)
    missing = sorted(set(ids) - details.keys())
    wrong_owner = sorted(key for key, row in details.items()
                         if row.get("snippet", {}).get("channelId") != CHANNEL_ID)
    nonpublic = sorted(key for key, row in details.items()
                       if row.get("status", {}).get("privacyStatus") != "public")
    checks = {
        "channel_count_present": count_of(before) is not None and count_of(after) is not None,
        "channel_count_stable": count_of(before) == count_of(after),
        "channel_count_matches_unique_ids": count_of(before) == len(ids),
        "all_playlist_rows_have_valid_ids": not first["invalid_rows"] and not second["invalid_rows"],
        "no_duplicate_playlist_ids": not first["duplicates"] and not second["duplicates"],
        "both_playlist_totals_reconcile": not faults,
        "two_ordered_inventories_match": ids == again_ids,
        "all_public_details_resolved": not missing,
        "no_duplicate_details": not duplicate_details,
        "no_unrequested_details": not unexpected_details,
        "all_details_belong_to_channel": not wrong_owner,
        "all_details_public": not nonpublic,
        "details_count_matches_inventory": len(details) == len(ids),
    }
    complete = all(checks.values())
    videos = [normalize_video(details[key], positions[key], describe, duration)
              for key in ids if key in details]
    videos.sort(key=lambda row: (row.get("published_at") or "", row["video_id"]), reverse=True)
    snippet = before.get("snippet") or {}
    reconciliation = {
        "scope": "public_uploads_visible_to_youtube_data_api_at_capture",
        "checks": checks, "failed_checks": [key for key, passed in checks.items() if not passed],
        "channel_count_before": count_of(before), "channel_count_after": count_of(after),
        "first_pass": first, "second_pass": second,
        "first_pass_pages": pages, "second_pass_pages": again_pages,
        "pagination_faults": sorted(set(faults)), "missing_video_details": missing,
        "unexpected_detail_ids": unexpected_details, "duplicate_detail_ids": duplicate_details,
        "wrong_channel_ids": wrong_owner, "nonpublic_ids": nonpublic,
        "first_ordered_ids_sha256": hashlib.sha256(json.dumps(ids).encode()).hexdigest(),
        "second_ordered_ids_sha256": hashlib.sha256(json.dumps(again_ids).encode()).hexdigest(),
        "interpretation": "Matching observations are not an atomic snapshot or access to non-public history.",
    }
    return {
        "provider": "youtube_data_api_v3", "inventory_complete": complete,
        "gate_state": "PASS" if complete else "PARTIAL",
        "limit_reason": None if complete else "; ".join(reconciliation["failed_checks"]),
        "channel": {
            "channel_id": CHANNEL_ID, "handle": HANDLE, "title": snippet.get("title"),
            "uploads_playlist_id": UPLOADS_ID, "reported_public_video_count": count_of(before),
            "description_sha256": hashlib.sha256(snippet.get("description", "").encode()).hexdigest(),
        },
        "playlist_item_count": len(rows), "unique_video_id_count": len(ids),
        "video_detail_count": len(videos), "missing_video_details": missing,
        "reconciliation": reconciliation, "videos": videos,
    }


def main() -> int:
    # Existing parsing/export helpers only; v1 acquisition and completion logic are not invoked.
    import collect_emergent_garden_youtube as legacy

    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default="docs/corpora/emergent-garden")
    args = parser.parse_args()
    started = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    try:
        api = ApiClient(os.environ.get("YOUTUBE_API_KEY", "").strip())
        body = collect(api, legacy.description_record, legacy.parse_duration)
    except AcquisitionError as exc:
        print(json.dumps({"state": "ERROR", "error_code": str(exc),
                          "previous_snapshot_preserved": True}), file=sys.stderr)
        return 1
    except Exception as exc:
        print(json.dumps({"state": "ERROR", "error_type": type(exc).__name__,
                          "previous_snapshot_preserved": True}), file=sys.stderr)
        return 1
    captured = legacy.now_utc()
    refresh_by = (started + dt.timedelta(days=30)).isoformat().replace("+00:00", "Z")
    inventory = {
        "schema_version": "1.1", "campaign_id": legacy.CAMPAIGN_ID,
        "generated_at": captured, "capture_started_at": started.isoformat(),
        "refresh_or_delete_by": refresh_by, "collector_version": "2.0.0",
        "requested_handle": HANDLE, "channel_url": legacy.CHANNEL_URL,
        "expected_channel_id": CHANNEL_ID, "expected_uploads_playlist_id": UPLOADS_ID,
        "acquisition_mode": "youtube_data_api_v3", "api_key_present": True,
        "acquisition_error": None, "api_requests": api.audit, **body,
    }
    coverage = legacy.build_text_coverage(inventory, captured)
    edges = legacy.build_edges(inventory, captured)
    for exported in (coverage, edges):
        exported["refresh_or_delete_by"] = refresh_by
        exported["collector_version"] = "2.0.0"
    status = {
        "schema_version": "1.1", "campaign_id": legacy.CAMPAIGN_ID, "generated_at": captured,
        "refresh_or_delete_by": refresh_by, "collector_version": "2.0.0",
        "gate": "G1_INVENTORY", "state": body["gate_state"], "provider": body["provider"],
        "inventory_complete": body["inventory_complete"], "normalized_video_count": len(body["videos"]),
        "blocking_reason": body["limit_reason"], "api_key_present": True,
        "api_request_count": len(api.audit), "reconciliation": body["reconciliation"],
        "coverage_summary": coverage["summary"], "edge_summary": edges["summary"],
        "next_action": "acquire permitted source text and review nested evidence" if body["inventory_complete"]
        else "review explicit reconciliation failures; do not equate API access with completeness",
    }
    root = Path(args.output_root)
    for name, value in (("channel-inventory", inventory), ("text-coverage", coverage),
                        ("description-edges", edges), ("census-status", status)):
        legacy.write_json(root / "data" / f"youtube-{name}-v1.json", value)
    report = legacy.build_report(inventory, coverage, edges, captured)
    if not body["inventory_complete"]:
        report = report.replace(
            "The complete census is not established. The committed records come from YouTube's "
            "official Atom channel feed and therefore represent only its recent window.",
            "The official API was queried successfully, but the observed inventory did not reconcile.")
        report = report.replace("**G1 inventory gate:** **BLOCKED**", "**G1 inventory gate:** **PARTIAL**")
        report = report.replace(
            "`G1_INVENTORY` remains blocked until a YouTube Data API v3 key is available to enumerate "
            "and reconcile the complete official uploads playlist. `G2_TEXT_COVERAGE` cannot be promoted "
            "from the recent-window sample.",
            "`G1_INVENTORY` remains partial until the failed reconciliation checks below are resolved. "
            "API access is working; transcript acquisition remains separate.")
    report += "\n## Machine-checked reconciliation\n\n"
    for name, passed in body["reconciliation"]["checks"].items():
        report += f"- `{name}`: {'PASS' if passed else 'FAIL'}\n"
    report += f"\nAPI requests: {len(api.audit)}. Refresh or delete API-derived metadata by {refresh_by}.\n"
    report += "\nScope is public uploads visible at capture. Transcripts, private/deleted history, "
    report += "and experiment reproduction remain unverified. Caption flags are not transcript text.\n"
    path = root / "research" / "YOUTUBE-CENSUS-WAVE-2.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")
    print(json.dumps(status, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
