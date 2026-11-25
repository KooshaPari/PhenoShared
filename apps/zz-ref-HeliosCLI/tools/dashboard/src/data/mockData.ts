export interface ModelMetric {
  model: string;
  provider: string;
  costPer1kTokens: number; // USD
  qualityScore: number; // 0-100
  avgLatencyMs: number;
  routedRequests: number;
}

export interface RoutingDecision {
  id: string;
  timestamp: string;
  inputTokens: number;
  outputTokens: number;
  selectedModel: string;
  reason: string;
  latencyMs: number;
  costUsd: number;
  qualityScore: number;
}

export const modelMetrics: ModelMetric[] = [
  { model: "gpt-4o", provider: "OpenAI", costPer1kTokens: 5.0, qualityScore: 92, avgLatencyMs: 820, routedRequests: 1240 },
  { model: "gpt-4o-mini", provider: "OpenAI", costPer1kTokens: 0.15, qualityScore: 78, avgLatencyMs: 310, routedRequests: 4870 },
  { model: "claude-sonnet-4-6", provider: "Anthropic", costPer1kTokens: 3.0, qualityScore: 91, avgLatencyMs: 750, routedRequests: 2310 },
  { model: "claude-haiku-3-5", provider: "Anthropic", costPer1kTokens: 0.25, qualityScore: 74, avgLatencyMs: 280, routedRequests: 3920 },
  { model: "llama-3.3-70b", provider: "Groq", costPer1kTokens: 0.59, qualityScore: 80, avgLatencyMs: 190, routedRequests: 1870 },
  { model: "gemini-2.0-flash", provider: "Google", costPer1kTokens: 0.10, qualityScore: 76, avgLatencyMs: 340, routedRequests: 2640 },
  { model: "gemini-1.5-pro", provider: "Google", costPer1kTokens: 1.25, qualityScore: 85, avgLatencyMs: 520, routedRequests: 980 },
  { model: "deepseek-r1", provider: "DeepSeek", costPer1kTokens: 0.55, qualityScore: 88, avgLatencyMs: 1100, routedRequests: 760 },
];

export const routingDecisions: RoutingDecision[] = [
  { id: "r001", timestamp: "2026-05-31T14:23:01Z", inputTokens: 512, outputTokens: 128, selectedModel: "gpt-4o-mini", reason: "low complexity / budget cap", latencyMs: 298, costUsd: 0.000096, qualityScore: 78 },
  { id: "r002", timestamp: "2026-05-31T14:22:48Z", inputTokens: 2048, outputTokens: 512, selectedModel: "claude-sonnet-4-6", reason: "code generation task", latencyMs: 763, costUsd: 0.00768, qualityScore: 91 },
  { id: "r003", timestamp: "2026-05-31T14:22:30Z", inputTokens: 256, outputTokens: 64, selectedModel: "gemini-2.0-flash", reason: "high throughput / cost floor", latencyMs: 321, costUsd: 0.000032, qualityScore: 76 },
  { id: "r004", timestamp: "2026-05-31T14:22:15Z", inputTokens: 4096, outputTokens: 1024, selectedModel: "deepseek-r1", reason: "reasoning / math task", latencyMs: 1142, costUsd: 0.00275, qualityScore: 88 },
  { id: "r005", timestamp: "2026-05-31T14:22:02Z", inputTokens: 1024, outputTokens: 256, selectedModel: "llama-3.3-70b", reason: "latency-sensitive path", latencyMs: 185, costUsd: 0.000767, qualityScore: 80 },
  { id: "r006", timestamp: "2026-05-31T14:21:50Z", inputTokens: 768, outputTokens: 192, selectedModel: "claude-haiku-3-5", reason: "summarization / low stakes", latencyMs: 275, costUsd: 0.000240, qualityScore: 74 },
  { id: "r007", timestamp: "2026-05-31T14:21:38Z", inputTokens: 3072, outputTokens: 768, selectedModel: "gpt-4o", reason: "creative writing / quality max", latencyMs: 834, costUsd: 0.01920, qualityScore: 92 },
  { id: "r008", timestamp: "2026-05-31T14:21:25Z", inputTokens: 512, outputTokens: 128, selectedModel: "gemini-1.5-pro", reason: "multimodal context detected", latencyMs: 514, costUsd: 0.000800, qualityScore: 85 },
];

// Pareto-optimal models: not dominated on both cost AND quality
export function getParetoFrontier(models: ModelMetric[]): Set<string> {
  const pareto = new Set<string>();
  for (const m of models) {
    const dominated = models.some(
      (other) =>
        other.model !== m.model &&
        other.qualityScore >= m.qualityScore &&
        other.costPer1kTokens <= m.costPer1kTokens &&
        (other.qualityScore > m.qualityScore || other.costPer1kTokens < m.costPer1kTokens)
    );
    if (!dominated) pareto.add(m.model);
  }
  return pareto;
}
