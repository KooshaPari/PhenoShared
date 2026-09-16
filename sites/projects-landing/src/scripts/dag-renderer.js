/**
 * DAG Renderer — Vanilla JS interactive directed acyclic graph renderer.
 *
 * Draws an SVG graph from a JSON dag-data definition with:
 *  - Automatic layered layout (longest-path layering)
 *  - Drag-to-pan and wheel-to-zoom
 *  - Click-to-select nodes
 *  - Status-based colour coding
 */

(function () {
  "use strict";

  // ── constants ──────────────────────────────────────────────────────────────
  const NODE_W = 180;
  const NODE_H = 48;
  const LAYER_GAP = 100;
  const NODE_GAP = 24;
  const PAD = 60;
  const ARROW_SIZE = 8;

  const STATUS_COLORS = {
    completed: { fill: "#16a34a", stroke: "#15803d", text: "#fff", bg: "#052e16" },
    "in-progress": { fill: "#2563eb", stroke: "#1d4ed8", text: "#fff", bg: "#172554" },
    pending: { fill: "#6b7280", stroke: "#4b5563", text: "#fff", bg: "#1f2937" },
    failed: { fill: "#dc2626", stroke: "#b91c1c", text: "#fff", bg: "#450a0a" },
  };
  const DEFAULT_STATUS = "pending";

  // ── state ───────────────────────────────────────────────────────────────────
  let svg, gMain, gEdges, gNodes;
  let panX = 0, panY = 0;
  let scale = 1;
  let isPanning = false;
  let panStart = { x: 0, y: 0 };
  let selectedId = null;
  let nodeRects = new Map(); // id -> {cx, cy, x, y, w, h}

  // ── filter state ────────────────────────────────────────────────────────────
  let currentFilter = { repo: "", epic: "", search: "" };

  // ── dag helpers ─────────────────────────────────────────────────────────────

  function topoSort(nodes, edges) {
    const inDeg = new Map();
    const adj = new Map();
    const idSet = new Set(nodes.map((n) => n.id));

    for (const id of idSet) {
      inDeg.set(id, 0);
      adj.set(id, []);
    }
    for (const e of edges) {
      if (!idSet.has(e.from) || !idSet.has(e.to)) continue;
      adj.get(e.from).push(e.to);
      inDeg.set(e.to, (inDeg.get(e.to) || 0) + 1);
    }

    const queue = [];
    for (const [id, deg] of inDeg) {
      if (deg === 0) queue.push(id);
    }

    const order = [];
    while (queue.length) {
      const id = queue.shift();
      order.push(id);
      for (const n of adj.get(id) || []) {
        const d = inDeg.get(n) - 1;
        inDeg.set(n, d);
        if (d === 0) queue.push(n);
      }
    }
    return order;
  }

  function assignLayers(nodes, edges) {
    const order = topoSort(nodes, edges);
    const layer = new Map();
    const adj = new Map();
    const idSet = new Set(nodes.map((n) => n.id));

    for (const id of idSet) layer.set(id, 0);
    for (const e of edges) {
      if (!idSet.has(e.from) || !idSet.has(e.to)) continue;
      if (!adj.has(e.from)) adj.set(e.from, []);
      adj.get(e.from).push(e.to);
    }

    // longest-path layering
    for (const id of order) {
      const l = layer.get(id) || 0;
      for (const n of adj.get(id) || []) {
        layer.set(n, Math.max(layer.get(n) || 0, l + 1));
      }
    }

    // group nodes by layer
    const byLayer = new Map();
    for (const n of nodes) {
      const l = layer.get(n.id) || 0;
      if (!byLayer.has(l)) byLayer.set(l, []);
      byLayer.get(l).push(n);
    }
    return { byLayer, layer };
  }

  function computePositions(nodes, edges) {
    const { byLayer, layer } = assignLayers(nodes, edges);
    const positions = new Map();
    const sortedLayers = [...byLayer.keys()].sort((a, b) => a - b);

    let maxW = 0;
    for (const [l, ns] of byLayer) {
      const totalW = ns.length * NODE_W + (ns.length - 1) * NODE_GAP;
      if (totalW > maxW) maxW = totalW;
    }

    for (const l of sortedLayers) {
      const ns = byLayer.get(l);
      const totalW = ns.length * NODE_W + (ns.length - 1) * NODE_GAP;
      const startX = (maxW - totalW) / 2;

      ns.forEach((n, i) => {
        const x = startX + i * (NODE_W + NODE_GAP);
        const y = l * (NODE_H + LAYER_GAP);
        positions.set(n.id, { x: PAD + x, y: PAD + y, cx: PAD + x + NODE_W / 2, cy: PAD + y + NODE_H / 2 });
      });
    }
    return positions;
  }

  function routeEdge(x1, y1, x2, y2) {
    const xOff = Math.abs(x2 - x1) / 2;
    const cp1x = x1;
    const cp1y = y1 + LAYER_GAP / 2;
    const cp2x = x2;
    const cp2y = y2 - LAYER_GAP / 2;
    return `M ${x1} ${y1} C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${x2} ${y2}`;
  }

  function getAvailableRepos(dagData) {
    const repos = new Set();
    for (const n of dagData.nodes) {
      if (n.repo) repos.add(n.repo);
    }
    return [...repos].sort();
  }

  function getAvailableEpics(dagData) {
    const epics = new Set();
    for (const n of dagData.nodes) {
      if (n.epic) epics.add(n.epic);
    }
    return [...epics].sort();
  }

  function nodePassesFilter(node, filter) {
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

  function applyFilter(dagData, filter) {
    currentFilter = { repo: filter.repo || "", epic: filter.epic || "", search: filter.search || "" };
    if (!gNodes) return;
    const allGroups = gNodes.querySelectorAll("g[data-id]");
    const visibleIds = new Set();
    for (const g of allGroups) {
      const nid = g.getAttribute("data-id");
      const node = dagData.nodes.find((x) => x.id === nid);
      if (node && nodePassesFilter(node, currentFilter)) {
        g.style.display = "";
        visibleIds.add(nid);
      } else {
        g.style.display = "none";
      }
    }
    const edges = gEdges.querySelectorAll("path[data-from][data-to]");
    for (const p of edges) {
      const from = p.getAttribute("data-from");
      const to = p.getAttribute("data-to");
      if (visibleIds.has(from) && visibleIds.has(to)) {
        p.style.display = "";
      } else {
        p.style.display = "none";
      }
    }
    updateFilterBadge(dagData);
  }

  function getActiveFilterCount() {
    let count = 0;
    if (currentFilter.repo) count++;
    if (currentFilter.epic) count++;
    if (currentFilter.search) count++;
    return count;
  }

  function updateFilterBadge(dagData) {
    const badge = document.getElementById("dag-filter-count");
    const clearBtn = document.getElementById("dag-filter-clear");
    if (!badge) return;
    const count = getActiveFilterCount();
    if (count > 0) {
      badge.textContent = String(count);
      badge.classList.remove("hidden");
      if (clearBtn) clearBtn.classList.remove("hidden");
    } else {
      badge.classList.add("hidden");
      if (clearBtn) clearBtn.classList.add("hidden");
    }
    if (gNodes) {
      const allGroups = gNodes.querySelectorAll("g[data-id]");
      let visible = 0;
      for (const g of allGroups) {
        if (g.style.display !== "none") visible++;
      }
      const visibleSpan = document.getElementById("dag-filter-visible-count");
      if (visibleSpan) {
        visibleSpan.textContent = visible + " / " + dagData.nodes.length + " nodes";
      }
    }
  }

  function getFilterState() {
    return { ...currentFilter };
  }

  function getFilterOptions(dagData) {
    return {
      repos: getAvailableRepos(dagData),
      epics: getAvailableEpics(dagData),
    };
  }

  // ── render ──────────────────────────────────────────────────────────────────

  function render(dagData, container) {
    // create SVG
    svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("width", "100%");
    svg.setAttribute("height", "100%");
    svg.style.display = "block";
    svg.style.cursor = "grab";
    container.innerHTML = "";
    container.appendChild(svg);

    // defs
    const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    const marker = document.createElementNS("http://www.w3.org/2000/svg", "marker");
    marker.setAttribute("id", "dag-arrow");
    marker.setAttribute("viewBox", "0 0 10 10");
    marker.setAttribute("refX", "10");
    marker.setAttribute("refY", "5");
    marker.setAttribute("markerWidth", ARROW_SIZE);
    marker.setAttribute("markerHeight", ARROW_SIZE);
    marker.setAttribute("orient", "auto-start-reverse");
    const arrowPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
    arrowPath.setAttribute("d", "M 0 0 L 10 5 L 0 10 z");
    arrowPath.setAttribute("fill", "#4b5563");
    marker.appendChild(arrowPath);
    defs.appendChild(marker);
    svg.appendChild(defs);

    // main group (pan/zoom target)
    gMain = document.createElementNS("http://www.w3.org/2000/svg", "g");
    gEdges = document.createElementNS("http://www.w3.org/2000/svg", "g");
    gNodes = document.createElementNS("http://www.w3.org/2000/svg", "g");
    gMain.appendChild(gEdges);
    gMain.appendChild(gNodes);
    svg.appendChild(gMain);

    // compute layout
    const pos = computePositions(dagData.nodes, dagData.edges);
    nodeRects = pos;

    // draw edges
    for (const e of dagData.edges) {
      const from = pos.get(e.from);
      const to = pos.get(e.to);
      if (!from || !to) continue;

      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      const d = routeEdge(from.cx, from.y + NODE_H, to.cx, to.y);
      path.setAttribute("d", d);
      path.setAttribute("fill", "none");
      path.setAttribute("stroke", "#4b5563");
      path.setAttribute("stroke-width", "2");
      path.setAttribute("marker-end", "url(#dag-arrow)");
      path.setAttribute("data-from", e.from);
      path.setAttribute("data-to", e.to);
      gEdges.appendChild(path);
    }

    // draw nodes
    for (const n of dagData.nodes) {
      const p = pos.get(n.id);
      if (!p) continue;
      const st = STATUS_COLORS[n.status] || STATUS_COLORS[DEFAULT_STATUS];

      const grp = document.createElementNS("http://www.w3.org/2000/svg", "g");
      grp.setAttribute("data-id", n.id);
      grp.style.cursor = "pointer";

      const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      rect.setAttribute("x", p.x);
      rect.setAttribute("y", p.y);
      rect.setAttribute("width", NODE_W);
      rect.setAttribute("height", NODE_H);
      rect.setAttribute("rx", "6");
      rect.setAttribute("fill", st.bg);
      rect.setAttribute("stroke", st.stroke);
      rect.setAttribute("stroke-width", "2");
      rect.classList.add("dag-node-rect");
      grp.appendChild(rect);

      const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
      text.setAttribute("x", p.cx);
      text.setAttribute("y", p.cy + 1);
      text.setAttribute("text-anchor", "middle");
      text.setAttribute("dominant-baseline", "middle");
      text.setAttribute("fill", st.text);
      text.setAttribute("font-size", "12");
      text.setAttribute("font-family", "ui-monospace, SFMono-Regular, monospace");
      text.textContent = n.label;
      grp.appendChild(text);

      // status badge
      const badge = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      badge.setAttribute("cx", p.x + 12);
      badge.setAttribute("cy", p.y + NODE_H / 2);
      badge.setAttribute("r", "5");
      badge.setAttribute("fill", st.fill);
      grp.appendChild(badge);

      grp.addEventListener("click", () => selectNode(n.id, dagData));
      gNodes.appendChild(grp);
    }

    applyTransform();

    // ── pan handlers ──
    svg.addEventListener("mousedown", (ev) => {
      if (ev.target !== svg && ev.target.tagName !== "svg") return;
      isPanning = true;
      panStart = { x: ev.clientX - panX, y: ev.clientY - panY };
      svg.style.cursor = "grabbing";
    });

    window.addEventListener("mousemove", (ev) => {
      if (!isPanning) return;
      panX = ev.clientX - panStart.x;
      panY = ev.clientY - panStart.y;
      applyTransform();
    });

    window.addEventListener("mouseup", () => {
      if (isPanning) {
        isPanning = false;
        svg.style.cursor = "grab";
      }
    });

    // ── zoom handlers ──
    svg.addEventListener("wheel", (ev) => {
      ev.preventDefault();
      const delta = ev.deltaY > 0 ? 0.92 : 1.08;
      scale = Math.max(0.2, Math.min(5, scale * delta));
      applyTransform();
    }, { passive: false });

    // tap info
    updateInfo(null, dagData);
  }

  function applyTransform() {
    gMain.setAttribute("transform", `translate(${panX},${panY}) scale(${scale})`);
  }

  function selectNode(id, dagData) {
    selectedId = id;
    const allRects = gNodes.querySelectorAll(".dag-node-rect");
    allRects.forEach((r) => {
      const g = r.closest("g") || r.parentElement;
      const nid = g.getAttribute("data-id");
      const n = dagData.nodes.find((x) => x.id === nid);
      const st = STATUS_COLORS[n?.status] || STATUS_COLORS[DEFAULT_STATUS];
      if (nid === id) {
        r.setAttribute("stroke", "#fbbf24");
        r.setAttribute("stroke-width", "3");
      } else {
        r.setAttribute("stroke", st.stroke);
        r.setAttribute("stroke-width", "2");
      }
    });
    updateInfo(id, dagData);
  }

  function updateInfo(selectedId, dagData) {
    const info = document.getElementById("dag-info");
    if (!info) return;
    if (!selectedId) {
      info.innerHTML = `<span class="text-[var(--muted)] text-sm">Click a node to see details</span>`;
      return;
    }
    const n = dagData.nodes.find((x) => x.id === selectedId);
    if (!n) return;
    const deps = dagData.edges.filter((e) => e.to === n.id).map((e) => {
      const src = dagData.nodes.find((x) => x.id === e.from);
      return src ? src.label : e.from;
    });
    const dependents = dagData.edges.filter((e) => e.from === n.id).map((e) => {
      const tgt = dagData.nodes.find((x) => x.id === e.to);
      return tgt ? tgt.label : e.to;
    });
    info.innerHTML = `
      <div class="flex items-center gap-2 mb-1">
        <span class="font-bold text-sm">${n.label}</span>
        <span class="mono text-xs px-2 py-0.5 rounded" style="background:${(STATUS_COLORS[n.status] || STATUS_COLORS[DEFAULT_STATUS]).fill};color:#fff">${n.status}</span>
      </div>
      ${deps.length ? `<p class="text-xs text-[var(--muted)] mt-1">Depends on: ${deps.join(", ")}</p>` : `<p class="text-xs text-[var(--muted)] mt-1">No dependencies (root node)</p>`}
      ${dependents.length ? `<p class="text-xs text-[var(--muted)] mt-1">Required by: ${dependents.join(", ")}</p>` : `<p class="text-xs text-[var(--muted)] mt-1">No dependents (leaf node)</p>`}
    `;
  }

  function getStatusSummary(dagData) {
    const counts = { completed: 0, "in-progress": 0, pending: 0, failed: 0 };
    for (const n of dagData.nodes) {
      counts[n.status] = (counts[n.status] || 0) + 1;
    }
    return counts;
  }

  // ── public api ──────────────────────────────────────────────────────────────
  window.DagRenderer = {
    render,
    getStatusSummary,
    applyFilter,
    getFilterState,
    getFilterOptions,
    getActiveFilterCount,
  };
})();
