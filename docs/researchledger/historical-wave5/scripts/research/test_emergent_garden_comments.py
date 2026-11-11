import unittest
from collect_emergent_garden_comments import CHANNEL, Stop, capture_video, chapter_lines, pages, record

def comment(cid, parent=None, creator=False):
    return {'id': cid, 'snippet': {'parentId': parent, 'textDisplay': 'untrusted text', 'authorChannelId': {'value': CHANNEL if creator else 'audience'}, 'authorDisplayName': 'must not retain'}}

def thread(replies, embedded):
    return {'snippet': {'videoId': 'video', 'topLevelComment': comment('top'), 'totalReplyCount': replies}, 'replies': {'comments': embedded}}

class CommentsTests(unittest.TestCase):
    def test_missing_replies_paginated(self):
        calls = []
        def api(resource, params):
            calls.append((resource, params))
            if resource == 'commentThreads':
                return {'items': [thread(3, [comment('r1','top')])]}
            if not params.get('pageToken'):
                return {'items': [comment('r1','top'), comment('r2','top', True)], 'nextPageToken':'two'}
            return {'items': [comment('r3','top')]}
        result = capture_video(api, 'video')
        self.assertEqual(result['summary']['replies'], 3)
        self.assertEqual(result['summary']['creator_comments'], 1)
        self.assertTrue(result['summary']['enumeration_complete'])
        self.assertEqual(len(calls), 3)

    def test_complete_embedded_does_not_refetch(self):
        def api(resource, params):
            self.assertEqual(resource, 'commentThreads')
            return {'items': [thread(1, [comment('r1','top')])]}
        self.assertTrue(capture_video(api, 'video')['summary']['enumeration_complete'])

    def test_count_mismatch_is_gap(self):
        def api(resource, params):
            return {'items': [thread(3, [])]} if resource == 'commentThreads' else {'items': [comment('r1','top')]}
        result = capture_video(api, 'video')['summary']
        self.assertFalse(result['enumeration_complete'])
        self.assertEqual(result['reply_gaps'], 1)

    def test_disabled_not_empty_success(self):
        def api(resource, params):
            raise Stop('commentsDisabled')
        result = capture_video(api, 'video')['summary']
        self.assertFalse(result['enumeration_complete'])
        self.assertIn('commentsDisabled', result['faults'])

    def test_cycle_stops(self):
        def api(resource, params):
            return {'items': [], 'nextPageToken': 'cycle'}
        with self.assertRaises(Stop):
            list(pages(api, 'comments', {}))

    def test_names_not_persisted(self):
        result = record(comment('x', creator=True), 'video')
        self.assertTrue(result['creator'])
        self.assertNotIn('authorDisplayName', result)
        self.assertNotIn('authorChannelId', result)
        self.assertIsNone(result['pinned'])

    def test_wrong_reply_parent_blocks(self):
        def api(resource, params):
            return {'items': [thread(1, [])]} if resource == 'commentThreads' else {'items': [comment('r1', 'wrong')]}
        self.assertFalse(capture_video(api, 'video')['summary']['enumeration_complete'])

    def test_duplicate_thread_blocks(self):
        def api(resource, params):
            return {'items': [thread(0, []), thread(0, [])]}
        self.assertFalse(capture_video(api, 'video')['summary']['enumeration_complete'])

    def test_chapters(self):
        self.assertEqual(len(chapter_lines('00:00 Intro\n- 02:34 - Tests\n1:20:00 Results')), 3)

if __name__ == '__main__':
    unittest.main()
