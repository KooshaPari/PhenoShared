import unittest
from unittest.mock import patch
import official_probe as p

def row(company,title,ident):
    return {'canonical_id':'greenhouse:'+company.lower()+':'+str(ident),
      'company':company,'title':title,'official_url':'https://job-boards.greenhouse.io/'+company.lower()+'/jobs/'+str(ident),
      'region':'la_metro','review_flags':[]}

class OfficialProbeTests(unittest.TestCase):
 def test_senior_not_selected(self):
    data={'records':[row('Acme','Senior Software Engineer',1),row('Sample','Software Engineer, New Grad',2)]}
    data['records'][0]['review_flags'].append('seniority_title')
    got=p.select_candidates(data,limit=20)
    self.assertEqual(len(got),1)
    self.assertEqual(got[0]['company'],'Sample')
 def test_employer_diversification(self):
    data={'records':[row('Acme','Software Engineer I '+str(i),i) for i in range(10)]}
    self.assertEqual(len(p.select_candidates(data,limit=10,per_employer=2)),2)
 def test_greenhouse_exact_post_id(self):
    item=row('Acme','Software Engineer New Grad',123)
    with patch.object(p,'fetch',return_value=(200,'{"id":123,"title":"Software Engineer New Grad","content":"<p>0-2 years experience; 2026 graduation.</p>"}')):
        checked=p.official_check(item)
    self.assertEqual(checked['official_status'],'listed_on_official_ats')
    self.assertEqual(checked['verification_status'],'unverified')
    self.assertTrue(checked['description_signature'])
 def test_http_200_wrong_posting_fails(self):
    item=row('Acme','Software Engineer New Grad',123)
    with patch.object(p,'fetch',return_value=(200,'{"id":456,"content":"<p>Junior engineer</p>"}')):
        with self.assertRaises(ValueError):p.official_check(item)
 def test_whatnot_catalog_not_promoted(self):
    item=row('Acme','Software Engineer New Grad',123)
    item['canonical_id']='ashby:whatnot:00000000-0000-4000-8000-000000000000'
    got=p.official_check(item)
    self.assertEqual(got['official_status'],'catalog_observed_only')
    self.assertEqual(got['verification_status'],'unverified')

if __name__=='__main__':unittest.main()
