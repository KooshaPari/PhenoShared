import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { modelMetrics, getParetoFrontier } from "../data/mockData";

const PROVIDER_COLORS: Record<string, string> = {
  OpenAI: "#10b981",
  Anthropic: "#f59e0b",
  Google: "#3b82f6",
  Groq: "#8b5cf6",
  DeepSeek: "#ef4444",
};

const frontier = getParetoFrontier(modelMetrics);

const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: Array<{ payload: typeof modelMetrics[0] }> }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div style={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8, padding: "10px 14px", color: "#e2e8f0", fontSize: 13 }}>
      <div style={{ fontWeight: 700, marginBottom: 4 }}>{d.model}</div>
      <div>Provider: {d.provider}</div>
      <div>Cost: ${d.costPer1kTokens.toFixed(2)} / 1k tokens</div>
      <div>Quality: {d.qualityScore}/100</div>
      <div>Avg Latency: {d.avgLatencyMs}ms</div>
      <div>Routed Reqs: {d.routedRequests.toLocaleString()}</div>
      {frontier.has(d.model) && <div style={{ color: "#f59e0b", marginTop: 4 }}>★ Pareto-optimal</div>}
    </div>
  );
};

export default function ParetoChart() {
  return (
    <div style={{ background: "#0f172a", borderRadius: 12, padding: "24px", border: "1px solid #1e293b" }}>
      <h2 style={{ color: "#f1f5f9", marginBottom: 4, fontSize: 18, fontWeight: 700 }}>Pareto Frontier: Cost vs Quality</h2>
      <p style={{ color: "#94a3b8", marginBottom: 20, fontSize: 13 }}>
        Gold ring = Pareto-optimal. Lower cost + higher quality = better position.
      </p>
      <ResponsiveContainer width="100%" height={340}>
        <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            type="number"
            dataKey="costPer1kTokens"
            name="Cost ($/1k tokens)"
            label={{ value: "Cost per 1k tokens (USD)", position: "insideBottom", offset: -12, fill: "#64748b", fontSize: 12 }}
            tick={{ fill: "#64748b", fontSize: 11 }}
            tickFormatter={(v) => `$${v}`}
          />
          <YAxis
            type="number"
            dataKey="qualityScore"
            name="Quality Score"
            domain={[60, 100]}
            label={{ value: "Quality Score", angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 12 }}
            tick={{ fill: "#64748b", fontSize: 11 }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Scatter data={modelMetrics} name="Models">
            {modelMetrics.map((entry) => (
              <Cell
                key={entry.model}
                fill={PROVIDER_COLORS[entry.provider] ?? "#94a3b8"}
                stroke={frontier.has(entry.model) ? "#f59e0b" : "transparent"}
                strokeWidth={frontier.has(entry.model) ? 3 : 0}
                r={frontier.has(entry.model) ? 10 : 7}
              />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginTop: 12 }}>
        {Object.entries(PROVIDER_COLORS).map(([p, c]) => (
          <span key={p} style={{ display: "flex", alignItems: "center", gap: 6, color: "#94a3b8", fontSize: 12 }}>
            <span style={{ width: 10, height: 10, borderRadius: "50%", background: c, display: "inline-block" }} />
            {p}
          </span>
        ))}
      </div>
    </div>
  );
}
