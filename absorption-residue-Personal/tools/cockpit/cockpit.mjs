#!/usr/bin/env node
// cockpit CLI. Env: COCKPIT_URL (default https://example.com), COCKPIT_TOKEN or ~/.config/cockpit/token
import fs from 'fs'; import os from 'os';
const base = (process.env.COCKPIT_URL || 'https://example.com') + '/api/v1';
let acc = {};
try { for (const l of fs.readFileSync(os.homedir() + '/.config/cockpit/access', 'utf8').split('\n')) { const i = l.indexOf('='); if (i > 0) acc[l.slice(0, i).trim()] = l.slice(i + 1).trim(); } } catch {}
const cfId = process.env.CF_ACCESS_CLIENT_ID || acc.CF_ACCESS_CLIENT_ID, cfSecret = process.env.CF_ACCESS_CLIENT_SECRET || acc.CF_ACCESS_CLIENT_SECRET;
const cfHdr = cfId && cfSecret ? { 'CF-Access-Client-Id': cfId, 'CF-Access-Client-Secret': cfSecret } : {};
let token = process.env.COCKPIT_TOKEN;
if (!token) { try { token = fs.readFileSync(os.homedir() + '/.config/cockpit/token', 'utf8').trim(); } catch {} }
const hdr = { ...cfHdr, 'content-type': 'application/json', ...(token ? { authorization: 'Bearer ' + token } : {}) };
async function call(m, p, b) {
  const r = await fetch(base + p, { method: m, headers: hdr, body: b ? JSON.stringify(b) : undefined });
  const t = await r.text(); if (!r.ok) { console.error(r.status, t); process.exit(1); } return JSON.parse(t);
}
const [cmd, id, ...rest] = process.argv.slice(2);
const kv = Object.fromEntries(rest.map((a) => { const i = a.indexOf('='); return [a.slice(0, i), a.slice(i + 1)]; }));
if (kv.percent !== undefined) kv.percent = kv.percent === '' ? null : Number(kv.percent);
if (kv.subgoals) kv.subgoals = JSON.parse(kv.subgoals);
if (cmd === 'list') console.log((await call('GET', '/projects')).projects.map((p) => `${p.id}\t${p.status}\t${p.percent ?? '-'}\t${p.name}`).join('\n'));
else if (cmd === 'get') console.log(JSON.stringify(await call('GET', '/projects/' + id), null, 2));
else if (cmd === 'set') console.log(JSON.stringify(await call('PATCH', '/projects/' + id, kv), null, 2));
else if (cmd === 'add') console.log(JSON.stringify(await call('POST', '/projects', { name: id, ...kv }), null, 2));
else if (cmd === 'archive') console.log(JSON.stringify(await call('DELETE', '/projects/' + id)));
else if (cmd === 'events') console.log(JSON.stringify((await call('GET', '/events')).events.slice(0, 20), null, 1));
else { console.error('usage: cockpit list | get <id> | set <id> key=value... (status,percent,detail,next,eta,blocker,usable,group,subgoals=<json>) | add <name> group=.. | archive <id> | events'); process.exit(2); }
