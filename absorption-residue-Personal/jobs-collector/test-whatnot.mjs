import test from 'node:test';
import assert from 'node:assert/strict';
import { parseWhatnotCareers } from './index.js';

function sampleCards() {
  return Array.from({length:21},(_,i) => {
    const id='00000000-0000-0000-0000-'+i.toString(16).padStart(12,'0');
    const title=i===0?'Software Engineer, 2027 New Grad':('Role '+i);
    const location=i===0?'Los Angeles, CA':(i===1?'Seattle, WA':'London, UK');
    return '<section><a href="/careers/roles/'+id+'"><p>'+title+'</p></a><div><strong>'+location+'</strong></div><a href="/careers/roles/'+id+'">View Job</a></section>';
  }).join('');
}

test('deduplicates official role links and associates local location',()=>{
  const rows=parseWhatnotCareers(sampleCards());
  assert.equal(rows.length,21);
  assert.equal(rows[0].title,'Software Engineer, 2027 New Grad');
  assert.equal(rows[0].loc,'Los Angeles, CA');
  assert.match(rows[0].url,/whatnot.com\/careers\/roles\/00000000/);
  assert.equal(rows[1].loc,'Seattle, WA');
  assert.doesNotMatch(rows[1].loc,/Los Angeles/);
});
test('rejects a broken or empty employer career feed',()=>{
  assert.throws(()=>parseWhatnotCareers('<html>empty</html>'),/too few linked roles/);
});
