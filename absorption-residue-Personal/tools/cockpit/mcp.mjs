#!/usr/bin/env node
// Minimal MCP stdio server over the cockpit API. Same env as cockpit.mjs.
import fs from 'fs'; import os from 'os'; import readline from 'readline';
const base = (process.env.COCKPIT_URL || 'https://example.com') + '/api/v1';
let acc = {};
try { for (const l of fs.readFileSync(os.homedir() + '/.config/cockpit/access', 'utf8').split('\n')) { const i = l.indexOf('='); if (i > 0) acc[l.slice(0, i).trim()] = l.slice(i + 1).trim(); } } catch {}
const cfId = process.env.CF_ACCESS_CLIENT_ID || acc.CF_ACCESS_CLIENT_ID, cfSecret = process.env.CF_ACCESS_CLIENT_SECRET || acc.CF_ACCESS_CLIENT_SECRET;
const cfHdr = cfId && cfSecret ? { 'CF-Access-Client-Id': cfId, 'CF-Access-Client-Secret': cfSecret } : {};
let token = process.env.COCKPIT_TOKEN;
if (!token) { try { token = fs.readFileSync(os.homedir() + '/.config/cockpit/token', 'utf8').trim(); } catch {} }
const api = async (m, p, b) => { const r = await fetch(base + p, { method: m, headers: { ...cfHdr, 'content-type': 'application/json', authorization: 'Bearer ' + token }, body: b ? JSON.stringify(b) : undefined }); return { status: r.status, body: await r.json().catch(() => null) }; };
const tools = [
  { name: 'cockpit_list', description: 'List cockpit projects', inputSchema: { type: 'object', properties: {} } },
  { name: 'cockpit_get', description: 'Get one project by id', inputSchema: { type: 'object', properties: { id: { type: 'string' } }, required: ['id'] } },
  { name: 'cockpit_update', description: 'Update fields of a project (status, percent, detail, next, eta, blocker, usable, group, subgoals[])', inputSchema: { type: 'object', properties: { id: { type: 'string' }, fields: { type: 'object' } }, required: ['id', 'fields'] } },
  { name: 'cockpit_add', description: 'Create a project (name, group required)', inputSchema: { type: 'object', properties: { project: { type: 'object' } }, required: ['project'] } },
  { name: 'cockpit_archive', description: 'Archive (soft delete) a project', inputSchema: { type: 'object', properties: { id: { type: 'string' } }, required: ['id'] } },
];
async function run(name, a) {
  if (name === 'cockpit_list') return api('GET', '/projects');
  if (name === 'cockpit_get') return api('GET', '/projects/' + a.id);
  if (name === 'cockpit_update') return api('PATCH', '/projects/' + a.id, a.fields);
  if (name === 'cockpit_add') return api('POST', '/projects', a.project);
  if (name === 'cockpit_archive') return api('DELETE', '/projects/' + a.id);
  return { status: 400, body: { error: 'unknown tool' } };
}
const send = (o) => process.stdout.write(JSON.stringify(o) + '\n');
readline.createInterface({ input: process.stdin }).on('line', async (l) => {
  let m; try { m = JSON.parse(l); } catch { return; }
  if (m.method === 'initialize') send({ jsonrpc: '2.0', id: m.id, result: { protocolVersion: '2024-11-05', capabilities: { tools: {} }, serverInfo: { name: 'cockpit', version: '1.0.0' } } });
  else if (m.method === 'tools/list') send({ jsonrpc: '2.0', id: m.id, result: { tools } });
  else if (m.method === 'tools/call') { const r = await run(m.params.name, m.params.arguments || {}); send({ jsonrpc: '2.0', id: m.id, result: { content: [{ type: 'text', text: JSON.stringify(r.body) }], isError: r.status >= 400 } }); }
  else if (m.id !== undefined) send({ jsonrpc: '2.0', id: m.id, error: { code: -32601, message: 'method not found' } });
});
