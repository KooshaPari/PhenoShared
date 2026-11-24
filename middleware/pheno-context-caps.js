// Pheno context caps + cloud giant gate (OmniRoute pre-request middleware)
// Hook body runs inside: Function("context", "return (async () => { ... })();")
// Return { headers?, body?, response? } — not wrapped in "mutations".

const CAPS = {
  route: { maxContext: 2048, maxOutput: 128 },
  retrieve: { maxContext: 8192, maxOutput: 256 },
  rank: { maxContext: 8192, maxOutput: 256 },
  plan: { maxContext: 16384, maxOutput: 512 },
  debug: { maxContext: 24576, maxOutput: 768 },
  patch: { maxContext: 32768, maxOutput: 1200 },
  fallback_12b: { maxContext: 65536, maxOutput: 1200 },
  fallback_30b: { maxContext: 65536, maxOutput: 1200 },
  emergency: { maxContext: 65536, maxOutput: 4096 },
};

const CLOUD_PROVIDERS = new Set(["openai", "anthropic", "claude", "codex", "minimax", "kimi", "google"]);
const CLOUD_HARD_CAP = 32768;

function inferRole(ctx) {
  const hdr = (ctx.headers && (ctx.headers["x-pheno-role"] || ctx.headers["X-Pheno-Role"])) || "";
  if (hdr) return String(hdr).toLowerCase();
  const model = String(ctx.model || "").toLowerCase();
  if (model.includes("opus") || model.includes("5.5")) return "emergency";
  if (model.includes("codex") || model.includes("spark")) return "patch";
  if (model.includes("mini")) return "debug";
  if (model.includes("4b") || model.includes("qwen")) return "patch";
  return "patch";
}

function estTokens(messages) {
  if (!Array.isArray(messages)) return 0;
  let n = 0;
  for (const m of messages) {
    const c = m && m.content;
    if (typeof c === "string") n += Math.ceil(c.length / 4);
    else if (Array.isArray(c)) {
      for (const p of c) {
        if (p && typeof p.text === "string") n += Math.ceil(p.text.length / 4);
      }
    }
  }
  return n;
}

function isCloud(ctx) {
  const p = String((ctx.combo && ctx.combo.provider) || ctx.metadata?.provider || "").toLowerCase();
  if (CLOUD_PROVIDERS.has(p)) return true;
  const m = String(ctx.model || "").toLowerCase();
  return m.includes("gpt-") || m.includes("claude") || m.includes("codex") || m.includes("minimax") || m.includes("kimi");
}

function budgetOverride(ctx, body) {
  const hdr = ctx.headers?.["x-needs-more-budget"] || ctx.headers?.["X-Needs-More-Budget"];
  if (hdr === "true") return true;
  if (body && (body.needs_more_budget === true || body.needs_more_budget === "true")) return true;
  return false;
}

const role = inferRole(context);
const caps = CAPS[role] || CAPS.patch;
const body = context.body || {};
const messages = body.messages || [];
const estIn = estTokens(messages);
const maxOut = body.max_tokens ?? body.max_completion_tokens ?? caps.maxOutput;

context.metadata = context.metadata || {};
context.metadata.pheno_role = role;
context.metadata.pheno_est_input = estIn;

const result = {
  headers: {
    "x-pheno-role": role,
    "x-pheno-est-input": String(estIn),
  },
};

if (maxOut > caps.maxOutput) {
  const nextBody = { ...body };
  if (nextBody.max_completion_tokens != null) nextBody.max_completion_tokens = caps.maxOutput;
  else nextBody.max_tokens = caps.maxOutput;
  result.body = nextBody;
}

if (isCloud(context) && estIn > CLOUD_HARD_CAP) {
  if (!budgetOverride(context, body)) {
    context.log.warn("pheno-context-caps", `Blocked cloud call est=${estIn} role=${role}`);
    return {
      response: {
        status: 413,
        body: {
          error: {
            message: "Context exceeds 32k cloud cap. Set header x-needs-more-budget: true or use local/compiled context.",
            type: "context_budget_exceeded",
            estimated_input_tokens: estIn,
            role,
          },
        },
      },
    };
  }
}

if (estIn > caps.maxContext && !isCloud(context)) {
  context.log.warn("pheno-context-caps", `Local context ${estIn} > cap ${caps.maxContext} role=${role}`);
  result.headers["x-pheno-context-over-cap"] = "true";
}

return result;
