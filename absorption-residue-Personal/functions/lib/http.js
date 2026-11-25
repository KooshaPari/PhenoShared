// Shared helpers for the cockpit Pages Functions (api/v1, api/answers).
// Extracted verbatim from functions/api/v1/[[path]].js so both routes use one copy.
export const J = (o, s = 200, h = {}) => new Response(JSON.stringify(o), { status: s, headers: { 'content-type': 'application/json', 'cache-control': 'no-store', ...h } });

// Outage hardening: a D1 failure becomes JSON 503 + Retry-After, never a bare
// worker exception page. Quota-shaped errors reset at midnight UTC (the D1
// daily window), anything else gets a short retry.
export function retryAfterSeconds(e) {
  const m = String((e && e.message) || e || '');
  if (/limit|quota|7500|D1_ERROR/i.test(m)) {
    const n = new Date();
    return Math.max(60, Math.ceil((Date.UTC(n.getUTCFullYear(), n.getUTCMonth(), n.getUTCDate() + 1) - n.getTime()) / 1000));
  }
  return 30;
}
export const unavailable = (e) =>
  J({ error: 'store_unavailable', detail: String((e && e.message) || e || 'unknown').slice(0, 300) }, 503, { 'retry-after': String(retryAfterSeconds(e)) });

export async function sha256(s) {
  const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s));
  return [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, '0')).join('');
}
export async function actorFor(req, env) {
  const m = /^Bearer\s+(.+)$/.exec(req.headers.get('authorization') || '');
  if (!m) return null;
  const h = await sha256(m[1]);
  const r = await env.COCKPIT_DB.prepare('SELECT actor FROM tokens WHERE sha256=? AND revoked=0').bind(h).first();
  return r ? r.actor : null;
}
