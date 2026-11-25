import PostalMime from 'postal-mime';
export const agents = new Set(['dot', 'instinct', 'jcode', 'hermes', 'codex', 'chatgpt', 'paperclip']);
export function recipient(address) {
  const match = /^([^@]+)@agents\.example\.com$/i.exec(address);
  return match && agents.has(match[1].toLowerCase()) ? match[1].toLowerCase() : null;
}
// Intake retry policy. A retry is only safe because the relay dedupes on message_id
// (relay.py deliver_local), so repeating the same request stores once. Without a message
// identity a repeat could store twice, so a single attempt is all we may make. The whole
// phase keeps the previous single-attempt ceiling of 25 s, so this adds resilience without
// extending how long Email Routing waits on us.
const INTAKE_BUDGET_MS = 25000;
const INTAKE_ATTEMPTS = 3;
const INTAKE_BACKOFF_MS = [300, 900];
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const transientStatus = (status) => status === 408 || status === 425 || status === 429 || status >= 500;
const acknowledged = (result) =>
  Array.isArray(result.ids) && result.ids.some((id) => typeof id === 'string' && id);
export async function email(message, env, fetcher = fetch) {
  const agent = recipient(message.to);
  if (!agent) { message.setReject('Unknown agent recipient'); return; }
  if (message.rawSize > 2 * 1024 * 1024) { message.setReject('Message exceeds 2 MiB'); return; }
  for (const key of ['CF_ACCESS_CLIENT_ID', 'CF_ACCESS_CLIENT_SECRET', 'INTAKE_TOKEN']) {
    if (!env[key]) throw new Error('Missing bridge secret: ' + key);
  }
  if (env.RELAY_URL !== 'https://example.com/v1/intake') {
    throw new Error('Unexpected relay endpoint');
  }
  const parsed = await PostalMime.parse(await new Response(message.raw).arrayBuffer());
  const text = (parsed.text || (parsed.html || '').replace(/<[^>]*>/g, ' ')).slice(0, 10000);
  // Stable message identity. Cloudflare Email Routing retries a failing handler and a
  // retry is the same message, so the relay can store it once instead of once per
  // attempt. postal-mime exposes headers as a Headers-like object; fall back to the
  // platform message headers when the MIME parse has none.
  const headerValue = (source, name) => {
    try {
      // postal-mime returns headers as an array of {key, originalKey, value}.
      if (Array.isArray(source)) {
        const target = String(name).toLowerCase();
        const found = source.find(h => String(h.key || h.name || '').toLowerCase() === target);
        return found ? found.value : null;
      }
      if (source && typeof source.get === 'function') return source.get(name);
      if (source && typeof source === 'object' && name in source) return source[name];
    } catch (_) { /* unreadable header source */ }
    return null;
  };
  const messageId = String(headerValue(parsed.headers, 'message-id')
    || headerValue(message.headers, 'message-id') || '').trim().slice(0, 300);
  // message.from is the SMTP envelope sender, which for mail routed through Resend is a
  // per-message SES VERP address and names nobody. Prefer the header From.
  const sender = String((parsed.from && parsed.from.address) || message.from || '').slice(0, 300);
  // One attempt per iteration, bounded by a shared deadline. A redirect means Cloudflare
  // Access rejected Service Auth and a 4xx means a bad request or token: neither becomes
  // true by waiting, so those surface immediately. Network faults, 408/425/429 and 5xx are
  // the transient classes worth a second try.
  const deadline = Date.now() + INTAKE_BUDGET_MS;
  const attempts = messageId ? INTAKE_ATTEMPTS : 1;
  let lastError = null;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    if (attempt > 0) {
      const wait = INTAKE_BACKOFF_MS[Math.min(attempt - 1, INTAKE_BACKOFF_MS.length - 1)];
      if (Date.now() + wait >= deadline) break;
      await sleep(wait);
    }
    const remaining = deadline - Date.now();
    if (remaining <= 0) break;
    let response;
    try {
      response = await fetcher(env.RELAY_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'CF-Access-Client-Id': env.CF_ACCESS_CLIENT_ID,
          'CF-Access-Client-Secret': env.CF_ACCESS_CLIENT_SECRET,
          Authorization: 'Bearer ' + env.INTAKE_TOKEN,
          ...(messageId ? { 'X-Message-Id': messageId } : {}),
        },
        // Workers rejects redirect:'error' at runtime (TypeError before the request is
        // sent, which silently dropped every inbound message). 'manual' lets us detect a
        // Cloudflare Access login redirect as an opaqueredirect and report it.
        redirect: 'manual',
        signal: AbortSignal.timeout(remaining),
        body: JSON.stringify({ from: sender, to: [agent + '@example.com'],
          subject: (parsed.subject || '').slice(0, 500), text,
          ...(messageId ? { message_id: messageId } : {}) }),
      });
    } catch (error) {
      lastError = error; // transport fault or abort: the retryable class
      continue;
    }
    if (response.type === 'opaqueredirect' || (response.status >= 300 && response.status < 400)) {
      throw new Error('Relay intake redirected (Service Auth rejected by Cloudflare Access)');
    }
    if (!response.ok) {
      const failure = new Error('Relay intake HTTP ' + response.status);
      if (!transientStatus(response.status)) throw failure;
      lastError = failure;
      continue;
    }
    const result = await response.json();
    if (!acknowledged(result)) {
      lastError = new Error('Relay did not acknowledge inbox storage');
      continue;
    }
    return;
  }
  throw lastError || new Error('Relay intake failed');
}
export default {
  email(message, env) { return email(message, env); },
  fetch(request) {
    return new URL(request.url).pathname === '/healthz'
      ? Response.json({ ok: true, service: 'agents-email-bridge' })
      : new Response('Not found', { status: 404 });
  },
};
