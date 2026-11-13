import unittest
import whatnot

class WhatnotSourceTests(unittest.TestCase):
    def test_nested_cards_and_dedupe(self):
        raw = '''<main><a href="/careers/roles/00000000-0000-4000-8000-000000000000">
        <div><p>Software Engineer, 2027 New Grad</p><img src="logo.png"><strong>Los Angeles, CA</strong></div>
        <span>View Job</span></a>
        <a href="/careers/roles/00000000-0000-4000-8000-000000000000">Software Engineer, 2027 New Grad</a>
        <a href="/careers/roles/00000000-0000-4000-8000-000000000000">Backend Engineer</a>
        </main>'''
        rows=whatnot.parse(raw)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["title"],"Software Engineer, 2027 New Grad")
        self.assertEqual(rows[0]["id"],"00000000-0000-4000-8000-000000000000")
        self.assertIn("whatnot.com/careers/roles/",rows[0]["official_url"])
    def test_only_employer_role_links(self):
        raw='''<a href="https://example.com/jobs/123">Other</a>
        <a href="/careers/roles/not-a-uuid">Invalid</a>
        <a href="/careers/roles/00000000-0000-4000-8000-000000000000">Platform Engineer</a>'''
        self.assertEqual(len(whatnot.parse(raw)),1)

if __name__ == "__main__":
    unittest.main()
