"""Offline negative controls for official census completeness and key redaction."""
import copy
import io
import json
import unittest
import urllib.error
from unittest.mock import Mock, patch

import collect_emergent_garden_youtube_v2 as census


def vid(number):
    return f"v{number:010d}"


def playlist_row(number):
    return {"contentDetails": {"videoId": vid(number)}, "snippet": {"position": number}}


def detail(number):
    return {"id": vid(number), "snippet": {"channelId": census.CHANNEL_ID,
            "title": f"Fixture {number}", "description": "fixture", "publishedAt": "2026-01-01"},
            "contentDetails": {"duration": "PT1M", "caption": "true"},
            "status": {"privacyStatus": "public"}}


class FakeApi:
    def __init__(self, n=3):
        self.rows = [playlist_row(i) for i in range(n)]
        self.again = None
        self.details = {vid(i): detail(i) for i in range(n)}
        self.before_count = self.after_count = n
        self.channel_id = census.CHANNEL_ID
        self.playlist_id = census.UPLOADS_ID
        self.total_override = None
        self.channel_calls = self.passes = 0
        self.calls = []
        self.extra = None

    def __call__(self, resource, params):
        self.calls.append((resource, params))
        if resource == "channels":
            self.channel_calls += 1
            count = self.before_count if self.channel_calls == 1 else self.after_count
            return {"items": [{"id": self.channel_id,
                    "contentDetails": {"relatedPlaylists": {"uploads": self.playlist_id}},
                    "statistics": {} if count is None else {"videoCount": str(count)},
                    "snippet": {"title": "Fixture channel"}}]}
        if resource == "playlistItems":
            token = params.get("pageToken")
            if token is None:
                self.passes += 1
            rows = self.rows if self.passes == 1 or self.again is None else self.again
            offset = int(token or 0)
            response = {"items": copy.deepcopy(rows[offset:offset + 50]),
                        "pageInfo": {"totalResults": len(rows) if self.total_override is None
                                     else self.total_override}}
            if offset + 50 < len(rows):
                response["nextPageToken"] = str(offset + 50)
            return response
        rows = [copy.deepcopy(self.details[v]) for v in params["id"].split(",") if v in self.details]
        if self.extra is not None:
            rows.append(copy.deepcopy(self.extra))
        return {"items": rows}


def run(api):
    return census.collect(api, lambda text: {"fixture": text}, lambda value: 60)


class ReconciliationTests(unittest.TestCase):
    def test_matching_multi_page_inventory_passes(self):
        api = FakeApi(74)
        result = run(api)
        self.assertTrue(result["inventory_complete"])
        self.assertEqual(len(result["videos"]), 74)
        self.assertEqual(len(result["reconciliation"]["first_pass_pages"]), 2)
        self.assertEqual(len(api.calls), 8)
        self.assertTrue(all(len(p["id"].split(",")) <= 50 for r, p in api.calls if r == "videos"))

    def test_missing_detail_never_passes(self):
        api = FakeApi()
        del api.details[vid(1)]
        result = run(api)
        self.assertFalse(result["inventory_complete"])
        self.assertEqual(result["missing_video_details"], [vid(1)])

    def test_count_mismatch_never_passes(self):
        api = FakeApi()
        api.before_count = api.after_count = 4
        self.assertFalse(run(api)["inventory_complete"])

    def test_duplicate_ids_are_deduplicated_but_block_completion(self):
        api = FakeApi()
        api.rows.append(playlist_row(1))
        result = run(api)
        self.assertFalse(result["inventory_complete"])
        self.assertEqual(len(result["videos"]), 3)
        self.assertEqual(result["reconciliation"]["first_pass"]["duplicates"], {vid(1): 2})

    def test_missing_row_id_remains_explicit(self):
        api = FakeApi()
        api.rows.append({"snippet": {"title": "Unavailable"}})
        result = run(api)
        self.assertFalse(result["inventory_complete"])
        self.assertEqual(len(result["reconciliation"]["first_pass"]["invalid_rows"]), 1)

    def test_missing_count_cannot_be_assumed(self):
        api = FakeApi()
        api.before_count = api.after_count = None
        self.assertFalse(run(api)["inventory_complete"])

    def test_count_change_during_capture_blocks(self):
        api = FakeApi()
        api.after_count = 4
        self.assertFalse(run(api)["inventory_complete"])

    def test_same_count_membership_change_blocks(self):
        api = FakeApi()
        api.again = [playlist_row(0), playlist_row(1), playlist_row(9)]
        self.assertFalse(run(api)["inventory_complete"])

    def test_second_pass_duplicate_blocks(self):
        api = FakeApi()
        api.again = api.rows + [playlist_row(1)]
        self.assertFalse(run(api)["inventory_complete"])

    def test_playlist_reported_total_mismatch_blocks(self):
        api = FakeApi()
        api.total_override = 100
        self.assertFalse(run(api)["inventory_complete"])

    def test_wrong_owner_and_nonpublic_details_block(self):
        for field, value in (("owner", "OTHER"), ("visibility", "private")):
            api = FakeApi()
            if field == "owner":
                api.details[vid(1)]["snippet"]["channelId"] = value
            else:
                api.details[vid(1)]["status"]["privacyStatus"] = value
            self.assertFalse(run(api)["inventory_complete"])

    def test_unrequested_and_duplicate_details_block(self):
        for number in (1, 99):
            api = FakeApi()
            api.extra = detail(number)
            self.assertFalse(run(api)["inventory_complete"])

    def test_identity_mismatch_fails_closed(self):
        for field in ("channel_id", "playlist_id"):
            api = FakeApi()
            setattr(api, field, "WRONG")
            with self.assertRaises(census.AcquisitionError):
                run(api)

    def test_cyclic_pagination_stops(self):
        api = Mock(return_value={"items": [], "pageInfo": {"totalResults": 2}, "nextPageToken": "loop"})
        with self.assertRaisesRegex(census.AcquisitionError, "TOKEN_CYCLE"):
            census.enumerate_uploads(api)
        self.assertEqual(api.call_count, 2)

    def test_page_budget_stops(self):
        calls = []
        def api(resource, params):
            calls.append(1)
            return {"items": [], "nextPageToken": str(len(calls))}
        with patch.object(census, "MAX_PAGES", 2):
            with self.assertRaisesRegex(census.AcquisitionError, "PAGE_BUDGET"):
                census.enumerate_uploads(api)
        self.assertEqual(len(calls), 2)

    def test_empty_channel_with_zero_count_can_pass(self):
        self.assertTrue(run(FakeApi(0))["inventory_complete"])

    def test_absent_caption_is_unknown(self):
        api = FakeApi()
        del api.details[vid(1)]["contentDetails"]["caption"]
        rows = {row["video_id"]: row for row in run(api)["videos"]}
        self.assertIsNone(rows[vid(1)]["caption_available"])


class TransportTests(unittest.TestCase):
    def test_http_error_does_not_disclose_key(self):
        client = census.ApiClient("SYNTHETIC_SECRET_SENTINEL")
        error = urllib.error.HTTPError("https://example.test/?key=SYNTHETIC_SECRET_SENTINEL", 403,
                                       "SYNTHETIC_SECRET_SENTINEL", {}, io.BytesIO(b"secret"))
        client.opener = Mock()
        client.opener.open.side_effect = error
        with self.assertRaises(census.AcquisitionError) as caught:
            client("channels", {"part": "statistics"})
        combined = str(caught.exception) + json.dumps(client.audit)
        self.assertNotIn("SYNTHETIC_SECRET_SENTINEL", combined)
        self.assertEqual(str(caught.exception), "API_HTTP_403")

    def test_missing_key_fails_closed(self):
        with self.assertRaisesRegex(census.AcquisitionError, "API_KEY_MISSING"):
            census.ApiClient("")

    def test_redirects_refused(self):
        with self.assertRaisesRegex(census.AcquisitionError, "REDIRECT_REFUSED"):
            census.NoRedirect().redirect_request(None, None, 302, "", {}, "https://elsewhere.test")

    def test_request_budget_and_resource_allowlist(self):
        client = census.ApiClient("SYNTHETIC")
        with self.assertRaisesRegex(census.AcquisitionError, "RESOURCE_NOT_ALLOWED"):
            client("../unapproved", {})
        with patch.object(census, "MAX_REQUESTS", 0):
            with self.assertRaisesRegex(census.AcquisitionError, "REQUEST_BUDGET"):
                client("channels", {})


if __name__ == "__main__":
    unittest.main()
