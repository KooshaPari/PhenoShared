# Agents inbound email bridge

Receiving Worker for explicit example.com addresses: dot, instinct,
jcode, hermes, codex, chatgpt, paperclip. No public HTTP intake endpoint.

Run `npm ci --ignore-scripts` and `npm test`. Deploy with `wrangler deploy`.
Provision CF_ACCESS_CLIENT_ID, CF_ACCESS_CLIENT_SECRET and INTAKE_TOKEN using
`wrangler secret put NAME`, piping values privately from the existing secret
source. Never put credentials in wrangler.toml or .dev.vars committed to Git.

Before switching Email Routing rules, verify authenticated public relay health
and intake storage. The Worker requires returned inbox IDs and throws on a
relay failure. Do not replace existing forwarding rules while intake is down.
Rules must match each explicit recipient and use worker agents-email-bridge.

Acceptance: send an external email with a unique subject to dot@, then find the
matching relay inbox record with source=worker and compute latency from the
sender timestamp to the stored timestamp. Local tests and /healthz do not prove
SMTP delivery. Attachments are not relayed; body text is capped at 10,000 chars.
