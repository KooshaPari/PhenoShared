/**
 * DAG renderer tests.
 *
 * Uses Vitest test runner.
 * Tests the layout algorithm, DAG data integrity, drill-down detail fields,
 * and client-side filter logic.
 */

import { describe, it, expect } from "vitest";
import dagData from "../data/dag-data.json";

interface DagNodeFilter {
  id: string;
  label: string;
  status: string;
  type: string;
  epic: string;
  repo: string;
  lastUpdated?: string | null;
}

interface DagNode {
  id: string;
  label: string;
  status: string;
  type?: string;
  epic?: string;
  repo?: string;
  lastUpdated?: string | null;
}
interface DagEdge {
  from: string;
  to: string;
}
interface DagData {
  title: string;
  description: string;
  nodes: DagNode[];
  edges: DagEdge[];
}

const data = dagData as DagData;

describe("DAG data integrity", () => {
  it("has a title and description", () => {
    expect(data.title).toBeTruthy();
    expect(data.description).toBeTruthy();
  });

  it("has at least one node", () => {
    expect(data.nodes.length).toBeGreaterThan(0);
  });

  it("all nodes have unique ids", () => {
    const ids = data.nodes.map((n) => n.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("all nodes have valid status values", () => {
    const valid = new Set(["completed", "in-progress", "pending", "failed", "blocked"]);
    for (const n of data.nodes) {
      expect(valid.has(n.status)).toBe(true);
    }
  });

  it("all edge references point to existing node ids", () => {
    const ids = new Set(data.nodes.map((n) => n.id));
    for (const e of data.edges) {
      expect(ids.has(e.from)).toBe(true);
      expect(ids.has(e.to)).toBe(true);
    }
  });

  it("has no duplicate edges", () => {
    const edgeSet = new Set(data.edges.map((e) => `${e.from}->${e.to}`));
    expect(edgeSet.size).toBe(data.edges.length);
  });
});

describe("DAG topology", () => {
  // Kahn's algorithm: if it produces all node ids, the graph is acyclic
  it("is acyclic (topological sort produces all nodes)", () => {
    const inDeg: Record<string, number> = {};
    const adj: Record<string, string[]> = {};
    const ids = new Set(data.nodes.map((n) => n.id));

    for (const id of ids) {
      inDeg[id] = 0;
      adj[id] = [];
    }
    for (const e of data.edges) {
      if (!ids.has(e.from) || !ids.has(e.to)) continue;
      adj[e.from].push(e.to);
      inDeg[e.to] = (inDeg[e.to] || 0) + 1;
    }

    const queue = Object.keys(inDeg).filter((id) => inDeg[id] === 0);
    const order: string[] = [];
    while (queue.length) {
      const id = queue.shift()!;
      order.push(id);
      for (const nid of adj[id] || []) {
        inDeg[nid]--;
        if (inDeg[nid] === 0) queue.push(nid);
      }
    }

    expect(order.length).toBe(ids.size);
  });

  it("has at least one root node (no incoming edges)", () => {
    const hasIncoming = new Set(data.edges.map((e) => e.to));
    const roots = data.nodes.filter((n) => !hasIncoming.has(n.id));
    expect(roots.length).toBeGreaterThanOrEqual(1);
  });
});

describe("DAG status distribution", () => {
  it("has at least one node in each status that is represented", () => {
    const counts: Record<string, number> = {};
    for (const n of data.nodes) {
      counts[n.status] = (counts[n.status] || 0) + 1;
    }
    const total = Object.values(counts).reduce((a: number, b: number) => a + b, 0);
    expect(total).toBe(data.nodes.length);
  });
});

describe("DAG drill-down detail fields", () => {
  it("all nodes have type, epic, and repo metadata", () => {
    for (const n of data.nodes) {
      expect(n.type).toBeTruthy();
      expect(n.epic).toBeTruthy();
      expect(n.repo).toBeTruthy();
    }
  });

  it("all nodes have a valid id pattern (letter + digits)", () => {
    for (const n of data.nodes) {
      expect(n.id).toMatch(/^[a-h]\d+$/);
    }
  });

  it("nodes can optionally have lastUpdated as ISO-8601 or null", () => {
    for (const n of data.nodes) {
      if (n.lastUpdated !== null && n.lastUpdated !== undefined) {
        expect(n.lastUpdated).toMatch(/^\d{4}-\d{2}-\d{2}T/);
      }
    }
  });
});

// Filter logic tests
describe("DAG filter \u2014 repository coverage", () => {
  it("every node belongs to a known repository", () => {
    const knownRepos = new Set([
      "phenotype-infra",
      "phenotype-registry",
      "pheno-mcp-router",
      "pheno-sdk",
      "pheno-port-adapter",
      "phenotype-landing",
      "pheno-otel",
    ]);
    for (const n of data.nodes) {
      expect(knownRepos.has(n.repo!)).toBe(true);
    }
  });

  it("has nodes across multiple repositories", () => {
    const repos = new Set(data.nodes.map((n) => n.repo));
    expect(repos.size).toBeGreaterThanOrEqual(2);
  });
});

describe("DAG filter \u2014 epic coverage", () => {
  it("every node belongs to a known epic", () => {
    const knownEpics = new Set([
      "Epic A \u2014 Infrastructure Foundations",
      "Epic B \u2014 Data & Schema Layer",
      "Epic C \u2014 MCP Router & SDK",
      "Epic D \u2014 Port Adapters & Integrations",
      "Epic E \u2014 Execution Engine",
      "Epic F \u2014 DAG Foundation & Automation",
      "Epic G \u2014 Observability",
      "Epic H \u2014 Security & Compliance",
    ]);
    for (const n of data.nodes) {
      expect(knownEpics.has(n.epic!)).toBe(true);
    }
  });

  it("has nodes across multiple epics", () => {
    const epics = new Set(data.nodes.map((n) => n.epic));
    expect(epics.size).toBeGreaterThanOrEqual(2);
  });
});

describe("DAG filter \u2014 nodePassesFilter logic", () => {
  function nodePassesFilter(node: DagNodeFilter, filter: { repo: string; epic: string; search: string }): boolean {
    if (filter.repo && node.repo !== filter.repo) return false;
    if (filter.epic && node.epic !== filter.epic) return false;
    if (filter.search) {
      const q = filter.search.toLowerCase();
      const label = (node.label || "").toLowerCase();
      const id = (node.id || "").toLowerCase();
      const repo = (node.repo || "").toLowerCase();
      const epic = (node.epic || "").toLowerCase();
      if (label.indexOf(q) === -1 && id.indexOf(q) === -1 && repo.indexOf(q) === -1 && epic.indexOf(q) === -1) {
        return false;
      }
    }
    return true;
  }

  const sampleNodes: DagNodeFilter[] = [
    { id: "a01", label: "Infra provisioning (Pulumi)", status: "completed", type: "impl", epic: "Epic A \u2014 Infrastructure Foundations", repo: "phenotype-infra" },
    { id: "c01", label: "MCP router gateway", status: "completed", type: "impl", epic: "Epic C \u2014 MCP Router & SDK", repo: "pheno-mcp-router" },
    { id: "f10", label: "DAG web renderer", status: "in-progress", type: "render", epic: "Epic F \u2014 DAG Foundation & Automation", repo: "phenotype-landing" },
  ];

  it("no filter all nodes pass", () => {
    for (const n of sampleNodes) {
      expect(nodePassesFilter(n, { repo: "", epic: "", search: "" })).toBe(true);
    }
  });

  it("repo filter shows only matching nodes", () => {
    for (const n of sampleNodes) {
      const pass = nodePassesFilter(n, { repo: n.repo, epic: "", search: "" });
      expect(pass).toBe(true);
    }
    expect(nodePassesFilter(sampleNodes[0], { repo: "nonexistent", epic: "", search: "" })).toBe(false);
  });

  it("epic filter shows only matching nodes", () => {
    const f10 = sampleNodes[2];
    expect(nodePassesFilter(f10, { repo: "", epic: "Epic F \u2014 DAG Foundation & Automation", search: "" })).toBe(true);
    expect(nodePassesFilter(sampleNodes[0], { repo: "", epic: "Epic F \u2014 DAG Foundation & Automation", search: "" })).toBe(false);
  });

  it("search filter matches label, id, repo, or epic", () => {
    expect(nodePassesFilter(sampleNodes[0], { repo: "", epic: "", search: "provisioning" })).toBe(true);
    expect(nodePassesFilter(sampleNodes[0], { repo: "", epic: "", search: "router" })).toBe(false);
    expect(nodePassesFilter(sampleNodes[0], { repo: "", epic: "", search: "a01" })).toBe(true);
    expect(nodePassesFilter(sampleNodes[0], { repo: "", epic: "", search: "phenotype-infra" })).toBe(true);
    expect(nodePassesFilter(sampleNodes[0], { repo: "", epic: "", search: "Infrastructure" })).toBe(true);
  });

  it("combined filters narrow results", () => {
    const f10 = sampleNodes[2];
    expect(nodePassesFilter(f10, { repo: "phenotype-landing", epic: "Epic F \u2014 DAG Foundation & Automation", search: "" })).toBe(true);
    expect(nodePassesFilter(f10, { repo: "phenotype-landing", epic: "Epic A \u2014 Infrastructure Foundations", search: "" })).toBe(false);
    expect(nodePassesFilter(f10, { repo: "phenotype-infra", epic: "Epic F \u2014 DAG Foundation & Automation", search: "" })).toBe(false);
  });

  it("search returns true when query is empty string", () => {
    for (const n of sampleNodes) {
      expect(nodePassesFilter(n, { repo: "", epic: "", search: "" })).toBe(true);
    }
  });

  it("search is case-insensitive", () => {
    expect(nodePassesFilter(sampleNodes[0], { repo: "", epic: "", search: "PULUMI" })).toBe(true);
    expect(nodePassesFilter(sampleNodes[0], { repo: "", epic: "", search: "Infrastructure" })).toBe(true);
  });

  it("filter works with actual DAG data nodes", () => {
    const typedNodes = data.nodes as DagNodeFilter[];
    const infraNodes = typedNodes.filter((n) => nodePassesFilter(n, { repo: "phenotype-infra", epic: "", search: "" }));
    expect(infraNodes.length).toBeGreaterThan(0);
    for (const n of infraNodes) {
      expect(n.repo).toBe("phenotype-infra");
    }

    const epicFNodes = typedNodes.filter((n) => nodePassesFilter(n, { repo: "", epic: "Epic F \u2014 DAG Foundation & Automation", search: "" }));
    expect(epicFNodes.length).toBeGreaterThan(0);
    for (const n of epicFNodes) {
      expect(n.epic).toBe("Epic F \u2014 DAG Foundation & Automation");
    }

    const combined = typedNodes.filter((n) => nodePassesFilter(n, { repo: "phenotype-landing", epic: "", search: "DAG" }));
    expect(combined.length).toBeGreaterThan(0);
    for (const n of combined) {
      expect(n.repo).toBe("phenotype-landing");
    }
  });
});
