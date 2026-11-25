// kilo-bridge: Discord plane -> Kilo Cloud Agent webhook trigger.
// Authored by Instinct. Disabled until KILO_TRIGGER_URL is set.
//
// Flow: the Discord relay POSTs {requester_id, channel_id, repo, task} here with
// header X-Bridge-Token. The bridge checks the token, the requester allowlist and
// the repo allowlist, then forwards a FIXED-shape JSON body to the Kilo trigger URL.
// The Kilo trigger prompt template must treat {{bodyJson}} as data, not instructions.
//
// Env (Worker secrets/vars): BRIDGE_TOKEN, KILO_TRIGGER_URL, KILO_TRIGGER_SECRET (optional),
// ALLOWED_REQUESTERS (comma Discord user ids), ALLOWED_REPOS (comma owner/name).
export default {
  async fetch(req, env) {
    if (req.method !== "POST") return new Response("method", { status: 405 });
    if (!env.KILO_TRIGGER_URL) return new Response("kilo trigger not configured", { status: 503 });
    if (req.headers.get("X-Bridge-Token") !== env.BRIDGE_TOKEN || !env.BRIDGE_TOKEN)
      return new Response("unauthorized", { status: 401 });
    let b;
    try { b = await req.json(); } catch { return new Response("bad json", { status: 400 }); }
    const list = (s) => (s || "").split(",").map((x) => x.trim()).filter(Boolean);
    if (!list(env.ALLOWED_REQUESTERS).includes(String(b.requester_id))) return new Response("requester not allowed", { status: 403 });
    if (!list(env.ALLOWED_REPOS).includes(String(b.repo))) return new Response("repo not allowed", { status: 403 });
    const task = String(b.task || "").slice(0, 4000);
    if (!task) return new Response("empty task", { status: 400 });
    const headers = { "content-type": "application/json" };
    if (env.KILO_TRIGGER_SECRET) headers["authorization"] = "Bearer " + env.KILO_TRIGGER_SECRET;
    const r = await fetch(env.KILO_TRIGGER_URL, {
      method: "POST",
      headers,
      body: JSON.stringify({ source: "discord-plane", repo: b.repo, requester_id: String(b.requester_id), channel_id: String(b.channel_id || ""), task }),
    });
    return new Response(JSON.stringify({ forwarded: r.status }), { status: r.ok ? 202 : 502, headers: { "content-type": "application/json" } });
  },
};
