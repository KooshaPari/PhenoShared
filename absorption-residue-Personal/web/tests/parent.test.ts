import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseLegacyParent } from '../src/features/parent/read.ts';
import { cell, labels, reference, rows, summary } from '../src/features/parent/model.ts';
const html = (data: string) => `<html><script>const D=${data}; const unused=()=>{throw new Error('must not execute')};</script></html>`;
test('parent data is decoded literally with no execution or input rewriting', () => {
  const source = html('{updated:"raw time",asks:[["date","ask","run"]],results:[],open:[["him","tap","wait"],["me","review","open"]],sched:[],plat:[], extra:{negative:-2, flag:true, nil:null}}');
  const before = source, data = parseLegacyParent(source);
  assert.equal(data.updated, 'raw time'); assert.equal((data.extra as Record<string, unknown>).negative, -2);
  assert.deepEqual(summary(data).map(s => s.value), [1, 1, 1, 0]); assert.equal(source, before);
});
test('calls, references, computed keys, getters, spreads and duplicate keys are rejected', () => {
  for (const data of ['{asks:run()}', '{asks:window.data}', '{["asks"]:[]}', '{get asks(){return []}}',
    '{...other}', '{asks:[],asks:[]}', '{__proto__:{}}', '{constructor:{}}', '{a:`value ${run()}`}', '[1,2]'])
    assert.throws(() => parseLegacyParent(html(data)), data);
  assert.throws(() => parseLegacyParent('<script>const D={};</script><script>const D={};</script>'));
  assert.throws(() => parseLegacyParent('<script>const other={};</script>'));
  assert.throws(() => parseLegacyParent(html('{asks:[}')));
});
test('missing collections remain unavailable, while empty arrays really count as zero', () => {
  assert.equal(rows(null), null); assert.deepEqual(rows([]), []); assert.equal(cell(undefined), '—');
  assert.deepEqual(summary({}).map(s => s.value), [null, null, null, null]);
  assert.deepEqual(summary({ asks: [], open: [], results: [] }).map(s => s.value), [0, 0, 0, 0]);
  assert.equal(labels.wait, 'Waiting on you');
});
test('parent references cannot execute scripts or use non-web schemes', () => {
  assert.equal(reference('https://example.com/a'), 'https://example.com/a');
  for (const value of ['javascript:alert(1)', 'data:text/html,hello', '//example.com', {}, null]) assert.equal(reference(value), null);
});
