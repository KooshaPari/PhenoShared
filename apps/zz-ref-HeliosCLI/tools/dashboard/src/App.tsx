import ParetoChart from "./components/ParetoChart";
import RoutingTable from "./components/RoutingTable";
import { modelMetrics, routingDecisions } from "./data/mockData";

const totalRequests = modelMetrics.reduce((s, m) => s + m.routedRequests, 0);
const totalCost = routingDecisions.reduce((s, r) => s + r.costUsd, 0);
const avgLatency = Math.round(
  routingDecisions.reduce((s, r) => s + r.latencyMs, 0) / routingDecisions.length
);

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 10, padding: "16px 24px", flex: "1 1 160px" }}>
      <div style={{ color: "#64748b", fontSize: 12, marginBottom: 4 }}>{label}</div>
      <div style={{ color: "#f1f5f9", fontSize: 24, fontWeight: 700 }}>{value}</div>
    </div>
  );
}

function App() {
  return (
    <div style={{ minHeight: "100vh", background: "#020817", fontFamily: "'Inter', system-ui, sans-serif", padding: "32px 40px" }}>
      <div style={{ marginBottom: 32, display: "flex", alignItems: "center", gap: 14 }}>
        <div style={{ width: 36, height: 36, background: "linear-gradient(135deg,#f59e0b,#ef4444)", borderRadius: 8 }} />
        <div>
          <h1 style={{ color: "#f1f5f9", fontSize: 22, fontWeight: 800, margin: 0 }}>Helios Router</h1>
          <div style={{ color: "#64748b", fontSize: 13 }}>LLM Routing Dashboard — sample data</div>
        </div>
      </div>
      <div style={{ display: "flex", gap: 16, marginBottom: 28, flexWrap: "wrap" }}>
        <StatCard label="Total Routed Requests" value={totalRequests.toLocaleString()} />
        <StatCard label="Models Tracked" value={String(modelMetrics.length)} />
        <StatCard label="Avg Latency (recent)" value={`${avgLatency}ms`} />
        <StatCard label="Total Cost (recent)" value={`$${totalCost.toFixed(4)}`} />
      </div>
      <div style={{ marginBottom: 24 }}>
        <ParetoChart />
      </div>
      <RoutingTable />
    </div>
  );
}

export default App
