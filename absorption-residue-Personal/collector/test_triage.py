import unittest
import triage

class TriageTests(unittest.TestCase):
    def test_la_vs_irvine(self):
        self.assertEqual(triage.region('Santa Monica, CA'), 'la_metro')
        self.assertEqual(triage.region('Irvine, CA'), 'rest_socal')
    def test_not_verified(self):
        r=triage.assess(('Example','Software Engineer I','Los Angeles','https://example.org','0-2 years','discovered'))
        self.assertEqual(r['verification_status'],'unverified')

if __name__ == '__main__': unittest.main()
