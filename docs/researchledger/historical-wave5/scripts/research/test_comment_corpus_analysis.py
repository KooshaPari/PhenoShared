import unittest

from analyze_comment_corpus import canonical_url, markers, primitive_check
from check_activation_parameterization import run


class AnalysisTests(unittest.TestCase):
    def test_parentheses(self):
        result = markers('(0:00) Intro\n(1:20) Next\n(2:40) End', 200)
        self.assertEqual(len(result['markers']), 3)
        self.assertTrue(result['chapter_sequence_candidate'])

    def test_plain(self):
        self.assertEqual(len(markers('0:00 Intro\n- 1:23 - Next', 200)['markers']), 2)

    def test_hms(self):
        self.assertEqual(markers('(1:03:55) A', 4000)['markers'][0]['seconds'], 3835)

    def test_range(self):
        self.assertEqual(markers('Explanation: 0:00 - 2:39', 300)['markers'][0]['seconds'], 0)

    def test_no_zero(self):
        self.assertFalse(markers('(0:25) A\n(1:00) B\n(2:00) C', 200)['chapter_sequence_candidate'])

    def test_nonmonotonic(self):
        self.assertTrue(markers('(0:00) A\n(1:00) B\n(0:30) C', 100)['issues'])

    def test_end_bounds(self):
        self.assertEqual(markers('(2:00) End', 120)['markers'], [])

    def test_invalid_minutes(self):
        self.assertTrue(markers('(1:70:20) Wrong', 10000)['issues'])

    def test_urls_not_chapters(self):
        self.assertEqual(markers('https://example.com/path?t=1:20', 1000)['markers'], [])

    def test_youtube_alias(self):
        self.assertEqual(canonical_url('https://youtu.be/0HqUYpGQIfs?t=33'), 'https://www.youtube.com/watch?v=0HqUYpGQIfs')

    def test_comment_is_distinct(self):
        self.assertIn('&lc=hello', canonical_url('https://youtube.com/watch?v=0HqUYpGQIfs&lc=hello'))

    def test_unknown_queries_remain_distinct(self):
        self.assertNotEqual(canonical_url('https://a.test/?x=1'), canonical_url('https://a.test/?x=2'))

    def test_untrusted_schemes_and_userinfo_rejected(self):
        self.assertIsNone(canonical_url('javascript:alert(1)'))
        self.assertIsNone(canonical_url('https://user:password@a.test/'))

    def test_identity(self):
        self.assertTrue(primitive_check()['passed'])

    def test_matched_parameterization(self):
        self.assertLess(run()['maximum_mapped_prediction_difference'], 1e-12)

    def test_equal_rate_negative_control(self):
        self.assertGreater(run()['same_rate_control_final_prediction_difference'], 1e-3)


if __name__ == '__main__':
    unittest.main()
