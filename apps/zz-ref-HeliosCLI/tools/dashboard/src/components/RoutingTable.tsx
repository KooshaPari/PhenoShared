import { routingDecisions } from "../data/mockData";

function formatTs(ts: string) {
  return new Date(ts).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

const QUALITY_COLOR = (q: number) => q >= 88 ? "#10b981" : q >= 78 ? "#f59e0b" : "#94a3b8";

export default function RoutingTable() {
  return (
    <div style={{ background: "#0f172a", borderRadius: 12, padding: "24px", border: "1px solid #1e293b" }}>
      <h2 style={{ color: "#f1f5f9", marginBottom: 4, fontSize: 18, fontWeight: 700 }}>Routing Decisions</h2>
      <p style={{ color: "#94a3b8", marginBottom: 20, fontSize: 13 }}>Last 8 routing decisions (mock). Wire to /api/decisions for live data.</p>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, color: "#cbd5e1" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #334155" }}>
              {["Time", "Model", "Tokens (in/out)", "Latency", "Cost", "Quality", "Reason"].map((h) => (
                <th key={h} style={{ textAlign: "left", padding: "8px 12px", color: "#64748b", fontWeight: 600, whiteSpace: "nowrap" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {routingDecisions.map((r, i) => (
              <tr key={r.id} style={{ borderBottom: "1px solid #1e293b", background: i % 2 === 0 ? "transparent" : "#0a0f1a" }}>
                <td style={{ padding: "9px 12px", whiteSpace: "nowrap", fontFamily: "monospace" }}>{formatTs(r.timestamp)}</td>
                <td style={{ padding: "9px 12px", fontWeight: 600, color: "#e2e8f0" }}>{r.selectedModel}</td>
                <td style={{ padding: "9px 12px", fontFamily: "monospace" }}>{r.inputTokens} / {r.outputTokens}</td>
                <td style={{ padding: "9px 12px", fontFamily: "monospace" }}>{r.latencyMs}ms</td>
                <td style={{ padding: "9px 12px", fontFamily: "monospace" }}>${r.costUsd.toFixed(5)}</td>
                <td style={{ padding: "9px 12px" }}>
                  <span style={{ color: QUALITY_COLOR(r.qualityScore), fontWeight: 700 }}>{r.qualityScore}</span>
                </td>
                <td style={{ padding: "9px 12px", color: "#94a3b8", fontStyle: "italic" }}>{r.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
