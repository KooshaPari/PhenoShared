import { test, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, readdir, mkdir, writeFile, rm } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import ts from 'typescript';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { normalizeSnapshot } from '../src/features/dispensary/data/adapters.ts';
import { buildChart } from '../src/features/dispensary/model/chart.ts';
import { loadDispensary } from '../src/features/dispensary/data/load.ts';
// Node's type stripping does not handle JSX. Transpile into a disposable tree
// beneath node_modules so React resolves normally; production sources stay intact.
const source = path.resolve('src/features/dispensary');
const temp = await mkdtemp(path.resolve('node_modules/.cockpit-component-test-'));
after(() => rm(temp, { recursive: true, force: true }));
async function compile(relative = '') {
  for (const entry of await readdir(path.join(source, relative), { withFileTypes: true })) {
    const name = path.join(relative, entry.name);
    if (entry.isDirectory()) { await compile(name); continue; }
    if (!/\.tsx?$/.test(name)) continue;
    const code = await readFile(path.join(source, name), 'utf8');
    const output = ts.transpileModule(code, { compilerOptions: {
      target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext, jsx: ts.JsxEmit.ReactJSX,
    } }).outputText.replace(/(['"])([^'"]+)\.tsx?\1/g, '$1$2.mjs$1').replace(/import ['"][^'"]+\.css['"];?/g, '');
    const destination = path.join(temp, name.replace(/\.tsx?$/, '.mjs'));
    await mkdir(path.dirname(destination), { recursive: true }); await writeFile(destination, output);
  }
}
await compile();
const { SortableTable } = await import(pathToFileURL(path.join(temp, 'components/SortableTable.mjs')).href);
const { TrendChart } = await import(pathToFileURL(path.join(temp, 'components/TrendChart.mjs')).href);
const { Insights } = await import(pathToFileURL(path.join(temp, 'components/Insights.mjs')).href);
test('table emits sortable headers, escaped content, details and bounded first page', () => {
  const rows = Array.from({ length: 30 }, (_, i) => ({ id: String(i), value: i === 0 ? '<script>alert(1)</script>' : String(i) }));
  const html = renderToStaticMarkup(createElement(SortableTable, { rows, columns: [{ key: 'value', label: 'Item', value: (r: typeof rows[number]) => r.value }],
    rowKey: (r: typeof rows[number]) => r.id, caption: 'Menu', detail: () => 'Captured data' }));
  assert.match(html, /aria-sort="ascending"/); assert.match(html, /&lt;script&gt;/); assert(!html.includes('<script>'));
  assert.match(html, /1–25 of 30/); assert.equal((html.match(/<summary>View item<\/summary>/g) ?? []).length, 25);
  assert.match(html, /role="region"/);
});
test('30-vendor legend is complete and charts include exact accessible values', () => {
  const snapshot = normalizeSnapshot({ date: '2026-10-09', stores: Array.from({ length: 30 }, (_, i) => ({ slug: 'v' + i,
    listing: { name: 'Very long vendor name ' + i }, items: [{ name: 'Cart 1g', after_tax: 10 + i }] })) }, '2026-10-09');
  const html = renderToStaticMarkup(createElement(TrendChart, { data: buildChart([snapshot], 'afterTaxPerGram') }));
  assert.equal((html.match(/class="d-legend-button"/g) ?? []).length, 30);
  assert.match(html, /Exact chart data \(30 vendors\)/); assert.match(html, /\$10.00\/g/);
  assert.equal((html.match(/aria-pressed="true"/g) ?? []).length, 4);
});
test('unavailable learned sources never render a zero registry count', async () => {
  const data = await loadDispensary({ fetcher: async () => new Response('', { status: 404 }) });
  const html = renderToStaticMarkup(createElement(Insights, { data, filters: { search: '', store: '', type: '', minSize: 0,
    includeLowThc: false, access: 'all', saleOnly: false, dropsOnly: false } }));
  assert.match(html, /Registry source unavailable/); assert(!html.includes('0 tracked entries'));
  assert.match(html, /Source unavailable; records are unknown/);
});
