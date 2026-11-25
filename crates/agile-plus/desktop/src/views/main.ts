/**
 * Renderer-side bootstrap for the main view.
 */

import Electrobun, { Electroview } from "electrobun/view";

interface SpecRow {
  id: string;
  title: string;
  state: string;
  path: string;
}
interface AdrRow {
  id: string;
  title: string;
  status: string;
  path: string;
}
interface TraceRow {
  id: string;
  kind: string;
  path: string;
}
interface RepoState {
  repoRoot: string;
  specs: SpecRow[];
  adrs: AdrRow[];
  traces: TraceRow[];
}

type RepoRPC = {
  bun: {
    requests: {
      getRepoState: { params: Record<string, never>; response: RepoState };
    };
    messages: Record<string, never>;
  };
  webview: {
    requests: Record<string, never>;
    messages: Record<string, never>;
  };
};

const rpc = Electroview.defineRPC<RepoRPC>({
  maxRequestTime: 5000,
  handlers: { requests: {}, messages: {} },
});

const electrobun = new Electrobun.Electroview({ rpc });

const $ = <T extends HTMLElement = HTMLElement>(sel: string) =>
  document.querySelector(sel) as T;

function setRepoRoot(label: string): void {
  $("#repo-root").textContent = label;
}

function renderSpecs(specs: SpecRow[]): void {
  const ul = $("#spec-list");
  ul.innerHTML = "";
  for (const s of specs) {
    const li = document.createElement("li");
    li.innerHTML = `<span>${escapeHtml(s.id)}</span><span class="meta">${escapeHtml(s.state)}</span>`;
    ul.appendChild(li);
  }
}

function renderAdrs(adrs: AdrRow[]): void {
  const ul = $("#adr-list");
  ul.innerHTML = "";
  for (const a of adrs) {
    const li = document.createElement("li");
    li.innerHTML = `<span>${escapeHtml(a.id)}</span><span class="meta">${escapeHtml(a.status)}</span>`;
    ul.appendChild(li);
  }
}

function renderTraces(traces: TraceRow[]): void {
  const ul = $("#trace-list");
  ul.innerHTML = "";
  for (const t of traces) {
    const li = document.createElement("li");
    li.innerHTML = `<span>${escapeHtml(t.id)}</span><span class="meta">${escapeHtml(t.kind)}</span>`;
    ul.appendChild(li);
  }
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function wireTabs(): void {
  const tabs = document.querySelectorAll<HTMLButtonElement>(".tab");
  const panels = document.querySelectorAll<HTMLElement>(".panel");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.tab;
      tabs.forEach((t) => t.setAttribute("aria-selected", String(t === tab)));
      panels.forEach((p) => (p.hidden = p.dataset.panel !== target));
    });
  });
}

async function bootstrap(): Promise<void> {
  wireTabs();
  const state = await electrobun.rpc!.request.getRepoState({});
  setRepoRoot(state.repoRoot);
  renderSpecs(state.specs);
  renderAdrs(state.adrs);
  renderTraces(state.traces);
}

bootstrap().catch((err) => {
  console.error("agileplus-desktop bootstrap failed", err);
  setRepoRoot("error: " + String(err));
});
