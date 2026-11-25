import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeSnapshot } from '../src/features/dispensary/data/adapters.ts';
import { buildChart, paletteFor } from '../src/features/dispensary/model/chart.ts';

test('30 vendor encodings are distinct, stable under sorting and filtering', () => {
  const slugs = Array.from({length:30},(_,i)=>`vendor-${i}`);
  assert.equal(new Set(slugs.map(s=>JSON.stringify(paletteFor(s)))).size,30);
  const snapshot=normalizeSnapshot({stores:slugs.map(slug=>({slug,items:[]}))},'2026-10-09');
  const a=buildChart([snapshot],'saleShare'), b=buildChart([{...snapshot,stores:[...snapshot.stores].reverse()}],'saleShare',()=>false);
  assert.deepEqual(a.series.map(s=>[s.slug,s.color,s.marker,s.dash]),b.series.map(s=>[s.slug,s.color,s.marker,s.dash]));
});
test('missing values remain null; zero prices survive; ml is not grams', () => {
  const snapshot=normalizeSnapshot({stores:[{slug:'one',items:[{name:'cart 1g',listed:0,after_tax:0},{name:'cart 2ml',listed:1,after_tax:1}]},{slug:'missing',items:[{name:'cart 1g'}]}]},'2026-10-09');
  const bySlug=(metric: Parameters<typeof buildChart>[1],predicate?: Parameters<typeof buildChart>[2])=>Object.fromEntries(buildChart([snapshot],metric,predicate).series.map(s=>[s.slug,s.values]));
  assert.deepEqual(bySlug('basePerGram'),{missing:[null],one:[0]});
  assert.deepEqual(bySlug('afterTaxPerGram',i=>i.volumeSize),{missing:[null],one:[null]});
  assert.deepEqual(bySlug('saleShare'),{missing:[null],one:[0]});
  assert.deepEqual(bySlug('discountPercent'),{missing:[null],one:[null]});
});
test('dates align, filters change metrics, and sale discounts use original prices', () => {
  const a=normalizeSnapshot({stores:[{slug:'a',listing:{name:'Old name'},items:[{name:'cart 1g',original:20,listed:10,after_tax:12},{name:'pod 1g',original:20,listed:20}]}]},'2026-10-08');
  const b=normalizeSnapshot({stores:[{slug:'a',listing:{name:'New name'},items:[{name:'cart 1g',listed:8}]}]},'2026-10-09');
  const share=buildChart([b,a],'saleShare');assert.deepEqual(share.dates,['2026-10-08','2026-10-09']);
  assert.equal(share.series[0].name,'New name');assert.deepEqual(share.series[0].values,[50,0]);
  assert.deepEqual(buildChart([a,b],'discountPercent',i=>i.type==='cart').series[0].values,[50,null]);
  assert.deepEqual(buildChart([a,b],'afterTaxPerGram',()=>false).series[0].values,[null,null]);
  assert.deepEqual(buildChart([normalizeSnapshot({stores:[{items:[]}]},'2026-10-09')],'saleShare').series,[]);
});
test('overflowing derived per-gram values remain missing', () => {
  const snapshot=normalizeSnapshot({stores:[{slug:'overflow',items:[{name:'cart 0.1g',listed:Number.MAX_VALUE,after_tax:Number.MAX_VALUE}]}]},'2026-10-09');
  assert.deepEqual(buildChart([snapshot],'basePerGram').series[0].values,[null]);
  assert.deepEqual(buildChart([snapshot],'afterTaxPerGram').series[0].values,[null]);
});
