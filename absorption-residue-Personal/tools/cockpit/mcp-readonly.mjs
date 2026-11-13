#!/usr/bin/env node
// Read-only MCP stdio server over the cockpit API.
//
// Issue #70 section 5: tools/cockpit/mcp.mjs advertises cockpit_list, cockpit_get,
// cockpit_update, cockpit_add and cockpit_archive. Three of those mutate state, so it
// is a writable client and cannot serve as the separate read-only deployment that
// section asks for. This file is that read-only surface.
//
// Safety model, in order of enforcement:
//   1. The tool list contains no mutating tool, so a compliant client never sees one.
//   2. run() refuses any name outside READ_ONLY before any fetch is constructed, so
//      a client that ignores the list and calls cockpit_update anyway is rejected.
//   3. Only GET is ever issued. There is no code path here that can send PATCH,
//      POST or DELETE, so a rejection bug cannot escalate into a mutation.
//
// Read-only is a property of this process, not of a flag someone can flip.
//
// Same env as mcp.mjs: COCKPIT_URL, COCKPIT_TOKEN, CF_ACCESS_CLIENT_ID,
// CF_ACCESS_CLIENT_SECRET, and the ~/.config/cockpit fallbacks.
import fs from 'fs';
import os from 'os';
import readline from 'readline';

const base = (process.env.COCKPIT_URL || 'https://example.com') + '/api/v1';
let acc = {};
try {
  for (const l of fs.readFileSync(os.homedir() + '/.config/cockpit/access', 'utf8').split('\n')) {
    const i = l.indexOf('=');
    if (i > 0) acc[l.slice(0, i).trim()] = l.slice(i + 1).trim();
  }
} catch {}
const cfId = process.env.CF_ACCESS_CLIENT_ID || acc.CF_ACCESS_CLIENT_ID;
const cfSecret = process.env.CF_ACCESS_CLIENT_SECRET || acc.CF_ACCESS_CLIENT_SECRET;
const cfHdr = cfId && cfSecret ? { 'CF-Access-Client-Id': cfId, 'CF-Access-Client-Secret': cfSecret } : {};
let token = process.env.COCKPIT_TOKEN;
if (!token) { try { token = fs.readFileSync(os.homedir() + '/.config/cockpit/token', 'utf8').trim(); } catch {} }

// GET is the only verb this module can emit.
const api = async (p) => {
  try {
    const r = await fetch(base + p, {
      method: 'GET',
      headers: { ...cfHdr, 'content-type': 'application/json', authorization: 'Bearer ' + token },
    });
    return { status: r.status, body: await r.json().catch(() => null) };
  } catch (e) {
    // A transport failure must surface as a tool error, not an unhandled
    // rejection that takes the stdio server down mid-session.
    return { status: 502, body: { error: 'cockpit API unreachable: ' + (e && e.message ? e.message : String(e)), readOnly: true } };
  }
};

export const READ_ONLY = new Set(['cockpit_list', 'cockpit_get']);

// Kept only so a client that ignores tools/list gets a refusal naming the reason,
// never a call. Listed here is NOT what makes it safe - the guard in run() is.
const REFUSED = new Set(['cockpit_update', 'cockpit_add', 'cockpit_archive']);

const tools = [
  { name: 'cockpit_list', description: 'List cockpit projects (read-only)', inputSchema: { type: 'object', properties: {} } },
  { name: 'cockpit_get', description: 'Get one project by id (read-only)', inputSchema: { type: 'object', properties: { id: { type: 'string' } }, required: ['id'] } },
];

async function run(name, a) {
  if (REFUSED.has(name)) {
    // Refused before any request is built. This is the load-bearing check.
    return { status: 403, body: { error: 'read-only server: ' + name + ' is not available here', readOnly: true } };
  }
  if (!READ_ONLY.has(name)) {
    return { status: 400, body: { error: 'unknown tool', readOnly: true } };
  }
  if (name === 'cockpit_list') return api('/projects');
  if (name === 'cockpit_get') return api('/projects/' + encodeURIComponent(a.id));
  return { status: 400, body: { error: 'unreachable', readOnly: true } };
}

const send = (o) => process.stdout.write(JSON.stringify(o) + '\n');
readline.createInterface({ input: process.stdin }).on('line', async (l) => {
  let m;
  try { m = JSON.parse(l); } catch { return; }
  if (m.method === 'initialize') {
    send({ jsonrpc: '2.0', id: m.id, result: { protocolVersion: '2024-11-05', capabilities: { tools: {} }, serverInfo: { name: 'cockpit-readonly', version: '1.0.0' } } });
  } else if (m.method === 'tools/list') {
    send({ jsonrpc: '2.0', id: m.id, result: { tools } });
  } else if (m.method === 'tools/call') {
    const r = await run(m.params.name, m.params.arguments || {});
    send({ jsonrpc: '2.0', id: m.id, result: { content: [{ type: 'text', text: JSON.stringify(r.body) }], isError: r.status >= 400 } });
  } else if (m.id !== undefined) {
    send({ jsonrpc: '2.0', id: m.id, error: { code: -32601, message: 'method not found' } });
  }
});
