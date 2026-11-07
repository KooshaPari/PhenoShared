#!/usr/bin/env python3
"""Read-only comments intake. Full text is private input, never a Git export.

Use commentThreads.list, and comments.list for reply sets not fully embedded.
Audience authors are not profiled: names, avatars and channel IDs are discarded.
Only equality with the known creator channel is retained. All text/links are
untrusted research data. Pin/heart state is unknown because this API omits it.
"""
from __future__ import annotations
import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

CHANNEL = "UCwBhBDsqiQflTMLy2epbQVw"
ALLOWED = {"videos", "commentThreads", "comments"}
URL_RE = re.compile(r"https?://[^\s<>\"\[\]]+")
STAMP_RE = re.compile(r"^\s*(?:[-*]\s*)?(\d{1,3}:\d{2}(?::\d{2})?)\s*(?:[-–—|:]\s*)?(.+)$")

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

class Stop(RuntimeError):
    pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise Stop("REDIRECT_REFUSED")

class Client:
    def __init__(self, key, max_requests=6000, max_seconds=900):
        if not key:
            raise Stop("KEY_MISSING")
        self.key, self.max_requests = key, max_requests
        self.deadline = time.monotonic() + max_seconds
        self.lock, self.audit = threading.Lock(), []
        self.next_slot = 0.0

    def __call__(self, resource, params):
        if resource not in ALLOWED or "key" in params:
            raise Stop("RESOURCE_REFUSED")
        clean = {k: v for k, v in params.items() if v is not None}
        url = "https://www.googleapis.com/youtube/v3/" + resource + "?" + urllib.parse.urlencode({**clean, "key": self.key})
        for attempt in range(3):
            with self.lock:
                if len(self.audit) >= self.max_requests or time.monotonic() >= self.deadline:
                    raise Stop("BUDGET_EXHAUSTED")
                delay = max(0, self.next_slot - time.monotonic())
                self.next_slot = max(self.next_slot, time.monotonic()) + 0.125
                receipt = {"resource": resource, "parameters": clean, "attempt": attempt + 1, "started_at": now()}
                self.audit.append(receipt)
            time.sleep(delay)
            try:
                request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "ResearchLedger-CommentResearch/1.0"})
                with urllib.request.build_opener(NoRedirect()).open(request, timeout=20) as response:
                    body = response.read(8_000_001)
                    receipt["http_status"] = response.status
                if len(body) > 8_000_000:
                    raise Stop("BODY_LIMIT")
                receipt["response_sha256"] = hashlib.sha256(body).hexdigest()
                payload = json.loads(body)
                if not isinstance(payload, dict) or "error" in payload:
                    raise Stop("INVALID_RESPONSE")
                return payload
            except urllib.error.HTTPError as exc:
                receipt["http_status"] = exc.code
                reason = "HTTP_" + str(exc.code)
                try:
                    details = json.loads(exc.read(65536)).get("error", {}).get("errors", [])
                    candidate = details[0].get("reason", "") if details else ""
                    if candidate in {"commentsDisabled", "videoNotFound", "commentNotFound", "quotaExceeded", "dailyLimitExceeded", "forbidden"}:
                        reason = candidate
                except (ValueError, IndexError, AttributeError):
                    pass
                receipt["reason"] = reason
                if reason in {"quotaExceeded", "dailyLimitExceeded"}:
                    self.deadline = time.monotonic()
                if exc.code in {429, 500, 502, 503, 504} and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise Stop(reason) from None
            except (urllib.error.URLError, TimeoutError, OSError):
                receipt["reason"] = "TRANSPORT_ERROR"
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise Stop("TRANSPORT_ERROR") from None
            except (ValueError, UnicodeError):
                raise Stop("INVALID_JSON") from None
        raise Stop("RETRY_EXHAUSTED")

def pages(api, resource, params):
    token, seen = None, set()
    for _ in range(2000):
        if token in seen:
            raise Stop("PAGINATION_CYCLE")
        seen.add(token)
        payload = api(resource, {**params, "pageToken": token})
        rows = payload.get("items")
        if not isinstance(rows, list):
            raise Stop("INVALID_ITEMS")
        yield rows
        token = payload.get("nextPageToken")
        if not token:
            return
        if not isinstance(token, str):
            raise Stop("INVALID_TOKEN")
    raise Stop("PAGE_LIMIT")

def record(item, video_id, parent_id=None):
    snippet = item.get("snippet", {})
    text = snippet.get("textOriginal") or snippet.get("textDisplay") or ""
    author = snippet.get("authorChannelId") or {}
    return {
        "comment_id": item["id"], "video_id": video_id, "parent_id": parent_id,
        "creator": author.get("value") == CHANNEL,
        "creator_identity_known": bool(author.get("value")),
        "published_at": snippet.get("publishedAt"), "updated_at": snippet.get("updatedAt"),
        "text": text, "text_sha256": digest(text),
        "source_url": f"https://www.youtube.com/watch?v={video_id}&lc={item['id']}",
        "pinned": None, "hearted": None,
        "urls": sorted(set(URL_RE.findall(text))),
    }

def capture_video(api, video_id):
    records, threads, faults = {}, {}, []
    exhausted = False
    try:
        for batch in pages(api, "commentThreads", {"part": "snippet,replies", "videoId": video_id, "maxResults": 100, "order": "time", "textFormat": "plainText"}):
            for thread in batch:
                snippet = thread.get("snippet", {})
                top = snippet.get("topLevelComment") or {}
                cid = top.get("id")
                if not cid or snippet.get("videoId") != video_id:
                    faults.append("INVALID_TOP_LEVEL")
                    continue
                if cid in threads:
                    faults.append("DUPLICATE_THREAD")
                    continue
                records[cid] = record(top, video_id)
                embedded = (thread.get("replies") or {}).get("comments", [])
                reply_ids = set()
                for reply in embedded:
                    rid = reply.get("id")
                    if not rid or reply.get("snippet", {}).get("parentId") != cid:
                        faults.append("INVALID_EMBEDDED_REPLY")
                        continue
                    reply_ids.add(rid)
                    records[rid] = record(reply, video_id, cid)
                expected = snippet.get("totalReplyCount")
                valid_count = isinstance(expected, int) and not isinstance(expected, bool) and expected >= 0
                threads[cid] = {"parent_id": cid, "expected_replies": expected, "reply_ids": sorted(reply_ids), "route": "embedded", "complete": valid_count and len(reply_ids) == expected}
        exhausted = True
    except Stop as exc:
        faults.append(str(exc))
    for cid, thread in threads.items():
        if thread["complete"]:
            continue
        found = {}
        try:
            for batch in pages(api, "comments", {"part": "snippet", "parentId": cid, "maxResults": 100, "textFormat": "plainText"}):
                for reply in batch:
                    rid = reply.get("id")
                    if not rid or reply.get("snippet", {}).get("parentId") != cid:
                        raise Stop("REPLY_PARENT_MISMATCH")
                    if rid in found:
                        raise Stop("DUPLICATE_REPLY")
                    found[rid] = record(reply, video_id, cid)
            thread["complete"] = len(found) == thread["expected_replies"]
            thread["route"] = "comments.list_exhausted"
            if not thread["complete"]:
                faults.append("REPLY_COUNT_CHANGED_OR_INACCESSIBLE")
        except Stop as exc:
            thread["complete"] = False
            thread["route"] = "comments.list_partial"
            thread["error"] = str(exc)
            faults.append(str(exc))
        records.update(found)
        thread["reply_ids"] = sorted(set(thread["reply_ids"]) | set(found))
    summary = {
        "video_id": video_id, "top_level_comments": len(threads),
        "replies": sum(r["parent_id"] is not None for r in records.values()),
        "creator_comments": sum(r["creator"] for r in records.values()),
        "threads_exhausted": exhausted, "reply_gaps": sum(not t["complete"] for t in threads.values()),
        "enumeration_complete": exhausted and not faults and all(t["complete"] for t in threads.values()),
        "faults": sorted(set(faults)), "record_count": len(records),
    }
    return {"summary": summary, "threads": list(threads.values()), "comments": list(records.values())}

def chapter_lines(text):
    result = []
    for n, line in enumerate(text.splitlines(), 1):
        match = STAMP_RE.match(line)
        if match:
            result.append({"line": n, "timestamp": match[1], "title": match[2]})
    return result

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", default="docs/corpora/emergent-garden/data/youtube-channel-inventory-v1.json")
    parser.add_argument("--private", required=True)
    parser.add_argument("--public", required=True)
    parser.add_argument("--max-requests", type=int, default=6000)
    args = parser.parse_args()
    private, public = Path(args.private), Path(args.public)
    inventory = json.loads(Path(args.inventory).read_text())
    ids = [r["video_id"] for r in inventory["videos"]]
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r"[A-Za-z0-9_-]{11}", x) for x in ids):
        raise Stop("INVALID_INVENTORY")
    api = Client(os.environ.get("YOUTUBE_API_KEY", ""), args.max_requests)
    started = now()
    details = []
    for offset in range(0, len(ids), 50):
        payload = api("videos", {"part": "snippet,contentDetails,statistics", "id": ",".join(ids[offset:offset + 50])})
        for item in payload["items"]:
            snippet = item.get("snippet", {})
            if item["id"] not in ids or snippet.get("channelId") != CHANNEL:
                raise Stop("DETAIL_IDENTITY_MISMATCH")
            details.append({"video_id": item["id"], "title": snippet.get("title"), "description": snippet.get("description", ""), "caption_flag_raw": item.get("contentDetails", {}).get("caption"), "statistics": item.get("statistics", {})})
    write(private / "video-text-input.json", {"captured_at": started, "videos": details})
    summaries = []
    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(capture_video, api, vid): vid for vid in ids}
        for future in cf.as_completed(futures):
            vid = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {"summary": {"video_id": vid, "enumeration_complete": False, "faults": ["UNEXPECTED_" + type(exc).__name__]}, "threads": [], "comments": []}
            write(private / "comments" / (vid + ".json"), result)
            summaries.append(result["summary"])
            print(json.dumps(result["summary"]), flush=True)
    before = {r["video_id"]: r["statistics"].get("commentCount") for r in details}
    after = {}
    try:
        for offset in range(0, len(ids), 50):
            for item in api("videos", {"part": "statistics", "id": ",".join(ids[offset:offset+50])})["items"]:
                after[item["id"]] = item.get("statistics", {}).get("commentCount")
    except Stop:
        pass
    for row in summaries:
        b, a = before.get(row["video_id"]), after.get(row["video_id"])
        row["reported_count_before"], row["reported_count_after"] = b, a
        row["count_stable"] = b is not None and a == b
        row["reported_count_matches_capture"] = a is not None and str(row.get("record_count")) == str(a)
    summary = {
        "campaign_id": "eg-nested-corpus-2026-09", "started_at": started, "finished_at": now(),
        "scope": "API-visible published comments on the 74-video public-upload census; not an atomic snapshot or moderated/deleted history",
        "source_inventory_sha256": hashlib.sha256(Path(args.inventory).read_bytes()).hexdigest(),
        "api_requests": len(api.audit), "videos_attempted": len(ids),
        "videos_enumerated_without_faults": sum(x["enumeration_complete"] for x in summaries),
        "top_level_comments": sum(x.get("top_level_comments", 0) for x in summaries),
        "replies": sum(x.get("replies", 0) for x in summaries),
        "creator_comments": sum(x.get("creator_comments", 0) for x in summaries),
        "private_text_policy": "minimized text, IDs and creator-equality flag encrypted in short-lived artifact; no audience names, profiles or avatars; never execute source text",
        "pin_and_heart_state": "not_exposed_by_documented_API",
        "transcripts_acquired": 0,
        "description_chapter_candidates": [{"video_id": x["video_id"], "chapters": chapter_lines(x["description"])} for x in details if chapter_lines(x["description"])],
        "videos": sorted(summaries, key=lambda x: x["video_id"]),
    }
    write(private / "request-receipts.json", api.audit)
    write(public / "comment-coverage-v1.json", summary)
    write(private / "comment-coverage-v1.json", summary)
    for file in private.rglob("*.json"):
        if api.key in file.read_text():
            raise Stop("CREDENTIAL_IN_OUTPUT")
    print(json.dumps({k:v for k,v in summary.items() if k not in {"videos", "description_chapter_candidates"}}, indent=2))

if __name__ == "__main__":
    main()
