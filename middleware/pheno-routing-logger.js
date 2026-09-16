// Pheno routing decision metadata (feeds RL loop via headers + metadata)
const role = (context.metadata && context.metadata.pheno_role) || "patch";
const estIn = (context.metadata && context.metadata.pheno_est_input) || 0;
const comboId = (context.combo && context.combo.id) || context.combo || "Main";
const provider = (context.combo && context.combo.provider) || context.metadata?.provider || "unknown";
const model = context.model || "unknown";

context.metadata = context.metadata || {};
context.metadata.pheno_routing = {
  request_id: context.metadata.request_id || String(Date.now()),
  task_type: role,
  combo_id: comboId,
  provider_selected: provider,
  model_selected: model,
  score: null,
  factors: { est_input: estIn, pheno_hook: "pheno-routing-logger" },
  source: "middleware",
  ts: new Date().toISOString(),
};

return {
  headers: {
    "x-pheno-routing-logged": "true",
    "x-pheno-combo": String(comboId),
  },
};
