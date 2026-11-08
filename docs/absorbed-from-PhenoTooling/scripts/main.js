/* ============================================================
 *  Koosha Paridehpour — Phenotype Profile SPA
 *  Vanilla ES module. No frameworks, no backend, no socket.
 *  Renders 5 views: overview / product / engineer / phenotype / recruiter
 *  Pure DOM + SVG for the fighter-card radar (crisp, scalable, accessible).
 * ============================================================ */

import {
  IDENTITY,
  EDUCATION,
  ROLES,
  PERSONAS,
  PHENOTYPE,
  TIMELINE,
  RECRUITER_STATS,
  SOURCE,
  PUBLIC_RECORD,
} from "../data/phenotype.js";
import { PROJECTS, PROOF_POINTS } from "../data/projects.js";

/* ---------- tiny DOM helpers ---------- */
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const el = (tag, attrs = {}, ...children) => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v;
    else if (k === "html") n.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function")
      n.addEventListener(k.slice(2).toLowerCase(), v);
    else if (v != null) n.setAttribute(k, v);
  }
  for (const c of children.flat()) {
    if (c == null || c === false) continue;
    n.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return n;
};

/* ---------- view registry ---------- */
const VIEWS = {
  home: renderPortfolioHome,
  engineering: renderPortfolioEngineering,
  overview: renderOverview,
  product: renderPortfolioProduct,
  work: renderPortfolioWork,
  resume: renderPortfolioResume,
  contact: renderPortfolioContact,
  engineer: renderEngineer,
  phenotype: renderPhenotype,
  recruiter: renderRecruiter,
  "public-record": renderPublicRecord,
};

/* ---------- tab routing ---------- */
let currentView = "overview";

function bindTabs() {
  $$(".tab").forEach((t) => {
    t.addEventListener("click", (e) => {
      e.preventDefault();
      if (location.hash.replace("#", "") !== t.dataset.view) {
        location.hash = t.dataset.view;
      } else {
        navigate(t.dataset.view);
      }
    });
  });
}

function navigate(view) {
  setPageMetadata(view);
  if (view.startsWith("work/")) {
    currentView = "work";
    $$(".tab").forEach((t) => { const active = t.dataset.view === "work"; t.classList.toggle("active", active); t.setAttribute("aria-selected", active ? "true" : "false"); });
    const detailRoot = $("#view-root");
    detailRoot.innerHTML = "";
    renderProjectDetail(detailRoot, view.slice(5));
    return;
  }
  if (!VIEWS[view]) return;
  currentView = view;
  $$(".tab").forEach((t) => { const active = t.dataset.view === view; t.classList.toggle("active", active); t.setAttribute("aria-selected", active ? "true" : "false"); });
  const root = $("#view-root");
  root.classList.remove("fade-in");
  // force reflow to restart animation
  void root.offsetWidth;
  root.innerHTML = "";
  VIEWS[view](root);
  root.classList.add("fade-in");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function setPageMetadata(view) {
  const slug = view.startsWith('work/') ? view.slice(5) : null;
  const project = slug ? PROJECTS.find((p) => p.slug === slug) : null;
  const labels = { home:'Home', engineering:'Engineering work', product:'Product / Program work', work:'Selected work', resume:'Resume', contact:'Contact' };
  const title = project ? `${project.title} — Koosha Paridehpour` : `${labels[view] || 'Portfolio'} — Koosha Paridehpour`;
  const description = project?.summary || 'Koosha Paridehpour — software engineer and technical product/program leader across systems, agent infrastructure, and physical products.';
  document.title = title;
  const meta = document.querySelector('meta[name="description"]');
  if (meta) meta.setAttribute('content', description);
  const ogTitle = document.querySelector('meta[property="og:title"]');
  if (ogTitle) ogTitle.setAttribute('content', title);
  const ogDescription = document.querySelector('meta[property="og:description"]');
  if (ogDescription) ogDescription.setAttribute('content', description);
}

function projectCard(project) {
  const links = (project.links || []).map(([label, url]) => el('a', { href:url, target:'_blank', rel:'noreferrer' }, label));
  return el('article', { class:'project-card' },
    project.gallery?.[0] ? el('img', { class:'project-card-image', src:project.gallery[0], alt:`${project.title} project image`, loading:'lazy', width:'1200', height:'700' }) : null,
    el('div', { class:'project-card-top' }, el('span', { class:'eyebrow' }, project.category), el('span', { class:'status-pill' }, project.status)),
    el('h3', {}, el('a', { href:`#work/${project.slug}`, class:'card-title-link' }, project.title)), el('p', {}, project.summary),
    project.technologies?.length ? el('div', { class:'tag-row' }, project.technologies.map(t => el('span', { class:'tag' }, t))) : null,
    project.repo ? el('a', { href:project.repo, target:'_blank', rel:'noreferrer', class:'text-link' }, 'View repository') : null,
    links.length ? el('div', { class:'project-links' }, links) : null
  );
}

function renderPortfolioHome(root) {
  const featured = PROJECTS.filter(p => p.featured);
  root.append(el('section', { class:'view active portfolio-view' },
    el('div', { class:'portfolio-hero' }, el('p', { class:'eyebrow' }, 'KOOSHA PARIDEHPOUR'), el('h1', {}, 'Software systems and technical products, built with intent.'), el('p', { class:'lede' }, 'Software engineer and technical product/program leader working across distributed systems, agent and ML infrastructure, developer tooling, cloud platforms, and technically complex physical products.'), el('div', { class:'cta-row' }, el('a', { href:'#engineering', class:'cta cta-eng' }, 'Engineering work'), el('a', { href:'#product', class:'cta cta-prod' }, 'Product work'))),
    el('div', { class:'proof-grid' }, PROOF_POINTS.map(([value,label]) => el('div', { class:'proof-point' }, el('strong', {}, value), el('span', {}, label)))),
    el('div', { class:'section-head' }, el('div', {}, el('h2', { class:'section-title' }, 'Selected work'), el('p', { class:'section-sub' }, 'A curated set of systems and products.'))),
    el('div', { class:'project-grid' }, featured.map(projectCard))
  ));
}

function renderPortfolioEngineering(root) { renderPortfolioCollection(root, 'Engineering', PROJECTS.filter(p => p.lens.includes('engineering')), 'Systems, infrastructure, and developer tooling.'); }
function renderPortfolioProduct(root) { renderPortfolioCollection(root, 'Product / Program', PROJECTS.filter(p => p.lens.includes('product')), 'Physical products and technical programs, viewed through decisions and outcomes.'); }
function renderPortfolioCollection(root, title, projects, subtitle) { root.append(el('section', { class:'view active portfolio-view' }, el('p', { class:'eyebrow' }, title.toUpperCase()), el('h1', {}, title), el('p', { class:'lede' }, subtitle), el('div', { class:'project-grid' }, projects.map(projectCard)))); }
const WORK_FILTERS = [
  ['all', 'All work'],
  ['engineering', 'Engineering'],
  ['product', 'Product'],
  ['systems', 'Systems'],
  ['ai-ml', 'AI/ML'],
  ['developer-tools', 'Developer Tools'],
  ['cloud', 'Cloud'],
  ['physical-product', 'Physical Product'],
  ['historical', 'Historical'],
];

function workFilterMatches(project, filter) {
  if (filter === 'all') return true;
  if (filter === 'historical') return project.status === 'historical';
  if (filter === 'engineering' || filter === 'product') return project.lens.includes(filter);
  if (filter === 'ai-ml') return project.category === 'ai-ml' || project.category === 'ai-infrastructure';
  return project.category === filter;
}

function renderPortfolioWork(root) {
  const grid = el('div', { class:'project-grid', 'aria-live':'polite' });
  const count = el('span', { class:'work-filter-count', 'aria-live':'polite' });
  const buttons = WORK_FILTERS.map(([value, label], index) => el('button', {
    type:'button', class:'work-filter', 'data-filter':value, 'aria-pressed':index === 0 ? 'true' : 'false',
    onclick:() => {
      const projects = PROJECTS.filter((project) => workFilterMatches(project, value));
      grid.replaceChildren(...projects.map(projectCard));
      count.textContent = `${projects.length} ${projects.length === 1 ? 'project' : 'projects'}`;
      buttons.forEach((button) => button.setAttribute('aria-pressed', button === buttons[index] ? 'true' : 'false'));
    },
  }, label));
  const allProjects = PROJECTS.filter((project) => workFilterMatches(project, 'all'));
  grid.append(...allProjects.map(projectCard));
  count.textContent = `${allProjects.length} projects`;
  root.append(el('section', { class:'view active portfolio-view' },
    el('p', { class:'eyebrow' }, 'WORK'),
    el('h1', {}, 'Work'),
    el('p', { class:'lede' }, 'Curated projects across engineering, product, systems, AI/ML, cloud, and historical work.'),
    el('div', { class:'work-filter-bar' },
      el('div', { class:'work-filter-heading' }, el('span', { class:'section-sub' }, 'Filter by focus'), count),
      el('div', { class:'work-filters', role:'group', 'aria-label':'Filter work by focus' }, buttons),
    ),
    grid,
  ));
}
function renderProjectDetail(root, slug) {
  const project = PROJECTS.find((p) => p.slug === slug);
  if (!project) return renderPortfolioNotFound(root, slug);
  const metrics = project.metrics?.length ? el('div', { class:'metric-grid' }, project.metrics.map(([value,label,source]) => el('div', { class:'metric-card' }, el('strong', {}, value), el('span', {}, label), el('small', {}, source)))) : null;
  const compactSections = {
    byteport:[['Context','Declarative Go/AWS deployment tooling with a deliberately explicit boundary between current behavior and planned delivery.'],['Current boundary','The record does not claim Firecracker, microVM, or live public deployment delivery without repository evidence.'],['Why it matters','The useful contribution is making deployment intent reviewable before infrastructure is provisioned.']],
    tracera:[['Context','Traceability and audit infrastructure for software and agent workflows.'],['Focus','The project organizes provenance and operational evidence without claiming unsupported adoption or deployment scale.'],['Current boundary','Repository status is the source of truth; production rollout claims are intentionally omitted.']],
    'dss-cipher':[['Context','Historical keyset concept preserved as a compact visual/product entry.'],['Evidence','Renders, kitting, collaborations, and community-interest links are retained where captured.'],['Current boundary','Unavailable external destinations and limited outcome evidence keep this out of the full case-study tier.']],
    'cliproxyapi-plusplus':[['Context','A forked multi-provider AI proxy focused on routing, auth, quotas, diagnostics, and operational controls.'],['Upstream boundary','The project is attributed to router-for-me/CLIProxyAPI; only KooshaPari’s extension scope is presented here.'],['Current boundary','Upstream popularity is not imported as local adoption evidence.']],
    'agentapi-plusplus':[['Context','Agent API extension work built on an upstream agent interface.'],['Upstream boundary','The project is attributed to coder/agentapi; this entry describes extension scope only.'],['Current boundary','No unsupported deployment or adoption claim is made.']],
    mcpforge:[['Context','Historical MCP tooling entry preserved for provenance and archive discoverability.'],['Upstream boundary','Attribution to isaacphi/mcp-language-server remains visible.']],
    forgecode:[['Context','Historical agent-tooling entry retained as an archive record.'],['Upstream boundary','Attribution to tailcallhq/forgecode remains visible.']],
    frostify:[['Context','Historical, unmaintained Spicetify theme fork with transparent/frosted styling.'],['Evidence','GitHub records 3,350+ release-asset downloads; this is not a user count.'],['Upstream boundary','Fork attribution to gwennlbh/Frostify remains explicit.']],
  };
  const sections = project.caseStudy?.sections || compactSections[project.slug] || (project.category === 'physical-product' ? [['Context','A technically complex physical product shaped by constraints, suppliers, and real-world demand.'],['Decisions','The work is presented as an evidence-led product narrative; historical facts retain their qualifiers.'],['Outcome','Commercial and launch claims are labeled in the evidence ledger rather than inflated in prose.']] : [['Problem','A concrete engineering problem is framed before implementation details.'],['Architecture','The system boundary, runtime choices, and operational constraints are kept explicit.'],['Verification','Current status and limitations follow the reconciled GitHub evidence.']]);
  const overview = project.caseStudy?.overview ? el('div', { class:'case-section case-overview' }, el('h2', {}, 'Overview'), el('p', {}, project.caseStudy.overview)) : null;
  const diagram = project.caseStudy?.diagram ? el('div', { class:'case-section case-diagram' }, el('h2', {}, 'Architecture'), el('pre', {}, project.caseStudy.diagram)) : null;
  const disclosure = project.caseStudy?.disclosure ? el('div', { class:'case-section case-disclosure' }, el('h2', {}, 'AI-assistance disclosure'), el('p', {}, project.caseStudy.disclosure)) : null;
  const evidence = project.caseStudy?.evidenceRefs?.length ? el('div', { class:'case-section case-evidence' }, el('h2', {}, 'Evidence status'), project.caseStudy.evidenceRefs.map(ref => el('p', {}, ref))) : null;
  root.append(el('section', { class:'view active portfolio-view case-study' }, el('a', { href:'#work', class:'back-link' }, '← Back to work'), el('p', { class:'eyebrow' }, `${project.category} · ${project.status}`), el('h1', {}, project.title), el('p', { class:'lede' }, project.summary), metrics, project.gallery?.length ? el('div', { class:'case-gallery' }, project.gallery.map((src,i) => el('img', { src, alt:`${project.title} project image ${i+1}`, loading:'lazy', width:'1600', height:'900' }))) : null, el('div', { class:'case-copy' }, overview, diagram, sections.map(([heading,copy]) => el('div', { class:'case-section' }, el('h2', {}, heading), el('p', {}, copy))), disclosure, evidence, project.provenance ? el('p', {}, project.provenance) : null), project.repo ? el('a', { href:project.repo, target:'_blank', rel:'noreferrer', class:'text-link' }, 'View repository') : null));
}
function renderPortfolioNotFound(root, slug) { root.append(el('section', { class:'view active portfolio-view not-found' }, el('p', { class:'eyebrow' }, '404'), el('h1', {}, 'Project not found'), el('p', { class:'lede' }, `No curated project record exists for “${slug}”.`), el('a', { href:'#work', class:'cta cta-eng' }, 'Browse work'))); }
function renderPortfolioResume(root) { root.append(el('section', { class:'view active portfolio-view' }, el('p', { class:'eyebrow' }, 'RESUME'), el('h1', {}, 'Two ways to read the work'), el('div', { class:'resume-grid' }, el('article', { class:'resume-card' }, el('h2', {}, 'Engineering'), el('p', {}, 'Systems, agent infrastructure, runtimes, observability, and developer tooling.'), el('span', { class:'muted' }, 'Canonical PDF link pending')), el('article', { class:'resume-card' }, el('h2', {}, 'Product / Program'), el('p', {}, 'Technical products, commercialization, manufacturing, and cross-functional execution.'), el('span', { class:'muted' }, 'Canonical PDF link pending'))))); }
function renderPortfolioContact(root) { root.append(el('section', { class:'view active portfolio-view' }, el('p', { class:'eyebrow' }, 'CONTACT'), el('h1', {}, 'Let’s build something consequential.'), el('p', { class:'lede' }, 'For engineering, technical product, and program conversations:'), el('div', { class:'contact-links' }, el('a', { href:'mailto:inquiry@ramdesigns.xyz' }, 'Email'), el('a', { href:'https://github.com/KooshaPari', target:'_blank', rel:'noreferrer' }, 'GitHub'), el('a', { href:'https://www.linkedin.com/in/koosha-paridehpour-1079b61b5/', target:'_blank', rel:'noreferrer' }, 'LinkedIn')))); }

/* ---------- SVG radar chart ----------
   axes: [{label, score 0-100}, ...]
   opts: { rings: [label...], accent, polyClass, size }
   Returns an <svg> element.
----------------------------------------- */
function buildRadar(axes, opts = {}) {
  const { rings = [], accent = "var(--accent-pheno)", size = 520 } = opts;
  const cx = size / 2;
  const cy = size / 2;
  const radius = size * 0.38;
  const N = axes.length;
  const angleFor = (i) => -Math.PI / 2 + (i * 2 * Math.PI) / N;
  const pointFor = (value, i) => {
    const a = angleFor(i);
    const r = (value / 100) * radius;
    return [cx + Math.cos(a) * r, cy + Math.sin(a) * r];
  };
  const ringRadii = [0.25, 0.5, 0.75, 1].map((p) => p * radius);

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${size} ${size}`);
  svg.setAttribute("class", "radar");
  svg.setAttribute("role", "img");
  svg.setAttribute(
    "aria-label",
    `Skill radar across ${N} axes: ${axes.map((a) => `${a.label} ${a.score}`).join(", ")}`,
  );

  /* ----- background rings ----- */
  const ringGroup = document.createElementNS(svg.namespaceURI, "g");
  ringGroup.setAttribute("class", "radar-rings");
  ringRadii.forEach((r, idx) => {
    const ring = document.createElementNS(svg.namespaceURI, "polygon");
    const pts = [];
    for (let i = 0; i < N; i++) {
      const a = angleFor(i);
      pts.push(`${cx + Math.cos(a) * r},${cy + Math.sin(a) * r}`);
    }
    ring.setAttribute("points", pts.join(" "));
    ring.setAttribute("class", "radar-ring");
    ring.style.animationDelay = `${idx * 60}ms`;
    ringGroup.appendChild(ring);
  });
  /* ring tier labels (small, on top axis) */
  if (rings.length) {
    const lblGroup = document.createElementNS(svg.namespaceURI, "g");
    lblGroup.setAttribute("class", "radar-ring-labels");
    rings.forEach((label, idx) => {
      const r = (idx / Math.max(1, rings.length - 1)) * radius;
      const text = document.createElementNS(svg.namespaceURI, "text");
      text.setAttribute("x", cx + 4);
      text.setAttribute("y", cy - r);
      text.setAttribute("class", "radar-ring-label");
      text.textContent = label;
      lblGroup.appendChild(text);
    });
    ringGroup.appendChild(lblGroup);
  }
  svg.appendChild(ringGroup);

  /* ----- axes ----- */
  const axisGroup = document.createElementNS(svg.namespaceURI, "g");
  axisGroup.setAttribute("class", "radar-axes");
  axes.forEach((axis, i) => {
    const a = angleFor(i);
    const x2 = cx + Math.cos(a) * radius;
    const y2 = cy + Math.sin(a) * radius;
    const line = document.createElementNS(svg.namespaceURI, "line");
    line.setAttribute("x1", cx);
    line.setAttribute("y1", cy);
    line.setAttribute("x2", x2);
    line.setAttribute("y2", y2);
    line.setAttribute("class", "radar-axis");
    axisGroup.appendChild(line);

    /* axis label */
    const lx = cx + Math.cos(a) * (radius + 22);
    const ly = cy + Math.sin(a) * (radius + 22);
    const text = document.createElementNS(svg.namespaceURI, "text");
    text.setAttribute("x", lx);
    text.setAttribute("y", ly);
    text.setAttribute("class", "radar-axis-label");
    text.setAttribute("text-anchor", lx < cx - 2 ? "end" : lx > cx + 2 ? "start" : "middle");
    text.setAttribute("dominant-baseline", ly < cy - 2 ? "auto" : ly > cy + 2 ? "hanging" : "middle");
    text.textContent = axis.label;
    axisGroup.appendChild(text);

    /* score */
    const sx = cx + Math.cos(a) * (radius + 38);
    const sy = cy + Math.sin(a) * (radius + 38);
    const score = document.createElementNS(svg.namespaceURI, "text");
    score.setAttribute("x", sx);
    score.setAttribute("y", sy);
    score.setAttribute("class", "radar-axis-score");
    score.setAttribute("text-anchor", lx < cx - 2 ? "end" : lx > cx + 2 ? "start" : "middle");
    score.textContent = axis.score;
    axisGroup.appendChild(score);
  });
  svg.appendChild(axisGroup);

  /* ----- value polygon ----- */
  const poly = document.createElementNS(svg.namespaceURI, "polygon");
  const pts = axes
    .map((a, i) => pointFor(a.score, i).join(","))
    .join(" ");
  poly.setAttribute("points", pts);
  poly.setAttribute("class", "radar-poly");
  poly.style.stroke = accent;
  svg.appendChild(poly);

  /* ----- value vertex dots ----- */
  axes.forEach((axis, i) => {
    const [x, y] = pointFor(axis.score, i);
    const c = document.createElementNS(svg.namespaceURI, "circle");
    c.setAttribute("cx", x);
    c.setAttribute("cy", y);
    c.setAttribute("r", 4);
    c.setAttribute("class", "radar-dot");
    c.style.fill = accent;
    svg.appendChild(c);
  });

  /* grow-in animation: scale from center */
  poly.style.transformOrigin = `${cx}px ${cy}px`;
  poly.style.transform = "scale(0)";
  requestAnimationFrame(() => {
    poly.style.transition = "transform 900ms cubic-bezier(.2,.8,.2,1)";
    poly.style.transform = "scale(1)";
  });

  return svg;
}

/* ---------- bar chart ---------- */
function buildBars(items, { max = 100, accent = "var(--accent-pheno)" } = {}) {
  const wrap = el("div", { class: "bars" });
  for (const it of items) {
    const pct = Math.min(100, Math.max(0, (it.score / max) * 100));
    const row = el(
      "div",
      { class: "bar-row" },
      el("div", { class: "bar-label" }, it.label),
      el(
        "div",
        { class: "bar-track" },
        el("div", {
          class: "bar-fill",
          style: `width: 0%; background: linear-gradient(90deg, ${accent}, ${accent}); --target:${pct}%;`,
        }),
      ),
      el("div", { class: "bar-value" }, String(it.score)),
    );
    wrap.appendChild(row);
  }
  requestAnimationFrame(() => {
    $$(".bar-fill", wrap).forEach((b) => {
      const target = b.style.getPropertyValue("--target");
      b.style.transition = "width 1s cubic-bezier(.2,.8,.2,1)";
      b.style.width = target;
    });
  });
  return wrap;
}

/* ---------- tag factory ---------- */
const tag = (text, kind = "pheno") =>
  el("span", { class: `tag tag-${kind}` }, text);

/* ---------- KPI tile ---------- */
function kpi({ k, v, h, accent = "pheno" }) {
  return el(
    "div",
    { class: `kpi kpi-${accent}` },
    el("div", { class: "kpi-k" }, k),
    el("div", { class: "kpi-v" }, v),
    h ? el("div", { class: "kpi-h" }, h) : null,
  );
}

/* ============================================================
 *  VIEW: OVERVIEW
 * ============================================================ */
function renderOverview(root) {
  const c = RECRUITER_STATS;

  /* hero summary */
  const hero = el(
    "section",
    { class: "hero-card" },
    el(
      "div",
      { class: "hero-grid" },
      el(
        "div",
        { class: "hero-mark" },
        el("div", { class: "hero-eyebrow" }, "BLIND REVIEW · DERIVED PHENOTYPE"),
        el("h1", { class: "hero-name" }, IDENTITY.legalName),
        el("div", { class: "hero-handle" }, `@${IDENTITY.handle}`),
        el(
          "div",
          { class: "hero-meta" },
          el("span", { class: "dot dot-amber" }),
          IDENTITY.currentCity,
          el("span", { class: "sep" }, "·"),
          IDENTITY.inferredRegion,
        ),
      ),
      el(
        "div",
        { class: "hero-tags" },
        tag("Product", "prod"),
        tag("Engineering", "eng"),
        tag("Phenotype", "pheno"),
        tag("Founder-Operator", "pheno"),
        tag("Tech-Lead", "eng"),
        tag("TPM", "prod"),
      ),
      el(
        "div",
        { class: "hero-tldr" },
        el("div", { class: "kpi-k" }, "ONE-LINER"),
        el("div", { class: "hero-tldr-body" }, PHENOTYPE.oneLiner),
      ),
    ),
  );

  /* estimated age + YOE strip */
  const strip = el(
    "section",
    { class: "strip" },
    el(
      "div",
      { class: "strip-grid" },
      kpi({
        k: "ESTIMATED AGE",
        v: c.personal.estimatedAgeRangeYears,
        h: "yrs (mid ≈ 25)",
        accent: "pheno",
      }),
      kpi({
        k: "YEARS POST-SECONDARY EDU",
        v: `~${c.professional.yearsOfPostSecondaryEducation}`,
        h: `${EDUCATION.degrees.length} degrees · ${EDUCATION.honorsCollege}`,
        accent: "eng",
      }),
      kpi({
        k: "YEARS PROFESSIONAL EXP",
        v: `~${c.professional.yearsOfProfessionalExperienceApprox}`,
        h: "concurrent w/ study",
        accent: "prod",
      }),
      kpi({
        k: "CUM. GPA",
        v: c.professional.cumulativeGpa.toFixed(2),
        h: "ASU · Barrett Honors",
        accent: "eng",
      }),
    ),
  );

  /* combined mini-radar + wins */
  const axes = PHENOTYPE.axes.map((a) => ({ label: a.label, score: a.score }));
  const radarCard = el(
    "section",
    { class: "card card-pheno" },
    el(
      "div",
      { class: "card-head" },
      el("div", { class: "card-title" }, "Combined Phenotype · 10 axes"),
      el("div", { class: "card-sub" }, PHENOTYPE.tagline),
    ),
    buildRadar(axes, { rings: PHENOTYPE.rings, accent: PHENOTYPE.color, size: 480 }),
  );

  const winsCard = el(
    "section",
    { class: "card card-pheno" },
    el(
      "div",
      { class: "card-head" },
      el("div", { class: "card-title" }, "Signature Wins"),
      el("div", { class: "card-sub" }, "evidence-backed, no fluff"),
    ),
    el(
      "ol",
      { class: "win-list" },
      ...c.impactSignals.slice(0, 6).map((w, i) =>
        el(
          "li",
          {},
          el("div", { class: "win-metric" }, w.metric),
          el("div", { class: "win-value" }, w.value),
        ),
      ),
    ),
  );

  const recruitsCard = el(
    "section",
    { class: "card card-prod" },
    el(
      "div",
      { class: "card-head" },
      el("div", { class: "card-title" }, "Recruiter TL;DR"),
      el("div", { class: "card-sub" }, "what you'd flag in 60 seconds"),
    ),
    el(
      "ul",
      { class: "tldr" },
      el(
        "li",
        {},
        el("span", { class: "tldr-k" }, "Stage"),
        "Mid–Senior / Tech-Lead ↔ Founder-Operator",
      ),
      el(
        "li",
        {},
        el("span", { class: "tldr-k" }, "Comp"),
        "$432K in 30d, 40%+ cost reduction, 10-wk→3-wk compression",
      ),
      el(
        "li",
        {},
        el("span", { class: "tldr-k" }, "Geo"),
        "Santa Monica · open to Scottsdale / Tempe / Remote",
      ),
      el(
        "li",
        {},
        el("span", { class: "tldr-k" }, "Fit"),
        "Founding Eng / TPM-Eng / Staff platform / FIR studio",
      ),
      el(
        "li",
        {},
        el("span", { class: "tldr-k" }, "Risk"),
        "Founder in flight — clarify runway / equity asks early",
      ),
    ),
  );

  root.append(hero, strip);
  const grid = el("section", { class: "grid-3" }, radarCard, winsCard, recruitsCard);
  root.appendChild(grid);

  /* education strip */
  root.appendChild(
    el(
      "section",
      { class: "card card-eng" },
      el(
        "div",
        { class: "card-head" },
        el("div", { class: "card-title" }, "Education"),
        el("div", { class: "card-sub" }, EDUCATION.institution),
      ),
      el(
        "div",
        { class: "edu-grid" },
        ...EDUCATION.degrees.map((d) =>
          el(
            "div",
            { class: "edu-tile" },
            el("div", { class: "edu-kind" }, d.kind),
            el("div", { class: "edu-conf" }, d.conferral),
            el("div", { class: "edu-gpa" }, "Barrett Honors"),
          ),
        ),
        el(
          "div",
          { class: "edu-tile edu-honors" },
          el("div", { class: "edu-kind" }, "Honors"),
          el("div", { class: "edu-conf" }, EDUCATION.honorsCollege),
          el("div", { class: "edu-gpa" }, "Concurrent MS pathway"),
        ),
      ),
    ),
  );
}

/* ============================================================
 *  VIEW: PRODUCT PERSONA
 * ============================================================ */
function renderProduct(root) {
  const p = PERSONAS.product;
  root.appendChild(
    el(
      "section",
      { class: "persona-head persona-prod" },
      el(
        "div",
        { class: "persona-tag" },
        tag(p.tag.split("·")[0].trim(), "prod"),
        tag(p.tag.split("·")[1]?.trim() || "Discovery", "prod"),
        tag(p.tag.split("·")[2]?.trim() || "Lifecycle", "prod"),
      ),
      el("h1", { class: "persona-title" }, p.title),
      el("div", { class: "persona-archetype" }, p.archetype),
      el("p", { class: "persona-headline" }, p.headline),
      el(
        "div",
        { class: "persona-north" },
        el("span", { class: "north-k" }, "NORTH STAR"),
        el("span", { class: "north-v" }, p.northStar),
      ),
      el(
        "div",
        { class: "persona-source" },
        "source: ",
        el("code", {}, p.source),
      ),
    ),
  );

  const axes = p.competencies.map((c) => ({ label: c.axis, score: c.score }));
  const radarCard = el(
    "section",
    { class: "card card-prod" },
    el(
      "div",
      { class: "card-head" },
      el("div", { class: "card-title" }, "Product Competencies"),
      el("div", { class: "card-sub" }, "scored 0–100 from resume evidence"),
    ),
    el("div", { class: "radar-wrap" }, buildRadar(axes, { accent: p.color, size: 460 })),
  );

  const barsCard = el(
    "section",
    { class: "card card-prod" },
    el(
      "div",
      { class: "card-head" },
      el("div", { class: "card-title" }, "Breakdown"),
      el("div", { class: "card-sub" }, p.tag),
    ),
    buildBars(p.competencies, { accent: p.color }),
  );

  const winsCard = el(
    "section",
    { class: "card card-prod" },
    el(
      "div",
      { class: "card-head" },
      el("div", { class: "card-title" }, "Top Wins"),
      el("div", { class: "card-sub" }, "PM lens"),
    ),
    el(
      "ol",
      { class: "win-list win-list-prod" },
      ...p.wins.map((w, i) =>
        el("li", {}, el("div", { class: "win-idx" }, `#${i + 1}`), el("div", { class: "win-body" }, w)),
      ),
    ),
  );

  root.appendChild(el("section", { class: "grid-2-1" }, radarCard, barsCard, winsCard));

  /* product-flavored timeline */
  root.appendChild(
    el(
      "section",
      { class: "card card-prod" },
      el(
        "div",
        { class: "card-head" },
        el("div", { class: "card-title" }, "Roles · Product framing"),
        el("div", { class: "card-sub" }, "which bullets serve the PM persona"),
      ),
      el(
        "div",
        { class: "xp-lane" },
        ...ROLES.map((r, i) =>
          el(
            "div",
            { class: `xp-node ${i % 2 === 0 ? "" : "lime"}` },
            el("div", { class: "when" }, `${r.start} → ${r.end}`),
            el("div", { class: "what" }, r.title),
            el("div", { class: "where" }, `${r.company} · ${r.location}`),
            el(
              "div",
              { class: "blurb" },
              r.highlights.slice(0, 2).join(" "),
            ),
            el(
              "div",
              { class: "tagrow" },
              ...r.framing.map((f) => tag(f, f === "Engineering" ? "eng" : "prod")),
            ),
          ),
        ),
      ),
    ),
  );

  root.appendChild(
    el(
      "section",
      { class: "card card-prod" },
      el(
        "div",
        { class: "card-head" },
        el("div", { class: "card-title" }, "Voice"),
        el("div", { class: "card-sub" }, "vocabulary the product resume reaches for"),
      ),
      el("p", { class: "voice-line" }, p.voice),
    ),
  );
}

/* ============================================================
 *  VIEW: ENGINEERING PERSONA
 * ============================================================ */
function renderEngineer(root) {
  const p = PERSONAS.engineering;
  root.appendChild(
    el(
      "section",
      { class: "persona-head persona-eng" },
      el(
        "div",
        { class: "persona-tag" },
        tag(p.tag.split("·")[0].trim(), "eng"),
        tag(p.tag.split("·")[1]?.trim() || "Performance", "eng"),
        tag(p.tag.split("·")[2]?.trim() || "Tooling", "eng"),
      ),
      el("h1", { class: "persona-title" }, p.title),
      el("div", { class: "persona-archetype" }, p.archetype),
      el("p", { class: "persona-headline" }, p.headline),
      el(
        "div",
        { class: "persona-north" },
        el("span", { class: "north-k" }, "NORTH STAR"),
        el("span", { class: "north-v" }, p.northStar),
      ),
      el(
        "div",
        { class: "persona-source" },
        "source: ",
        el("code", {}, p.source),
      ),
    ),
  );

  const axes = p.competencies.map((c) => ({ label: c.axis, score: c.score }));
  const radarCard = el(
    "section",
    { class: "card card-eng" },
    el(
      "div",
      { class: "card-head" },
      el("div", { class: "card-title" }, "Engineering Competencies"),
      el("div", { class: "card-sub" }, "scored 0–100 from resume evidence"),
    ),
    el("div", { class: "radar-wrap" }, buildRadar(axes, { accent: p.color, size: 460 })),
  );

  const barsCard = el(
    "section",
    { class: "card card-eng" },
    el(
      "div",
      { class: "card-head" },
      el("div", { class: "card-title" }, "Breakdown"),
      el("div", { class: "card-sub" }, p.tag),
    ),
    buildBars(p.competencies, { accent: p.color }),
  );

  const winsCard = el(
    "section",
    { class: "card card-eng" },
    el(
      "div",
      { class: "card-head" },
      el("div", { class: "card-title" }, "Top Wins"),
      el("div", { class: "card-sub" }, "engineering lens"),
    ),
    el(
      "ol",
      { class: "win-list win-list-eng" },
      ...p.wins.map((w, i) =>
        el("li", {}, el("div", { class: "win-idx" }, `#${i + 1}`), el("div", { class: "win-body" }, w)),
      ),
    ),
  );

  root.appendChild(el("section", { class: "grid-2-1" }, radarCard, barsCard, winsCard));

  root.appendChild(
    el(
      "section",
      { class: "card card-eng" },
      el(
        "div",
        { class: "card-head" },
        el("div", { class: "card-title" }, "Roles · Engineering framing"),
        el("div", { class: "card-sub" }, "which bullets serve the engineer persona"),
      ),
      el(
        "div",
        { class: "xp-lane" },
        ...ROLES.map((r, i) =>
          el(
            "div",
            { class: `xp-node ${i % 2 === 0 ? "blue" : "gray"}` },
            el("div", { class: "when" }, `${r.start} → ${r.end}`),
            el("div", { class: "what" }, r.title),
            el("div", { class: "where" }, `${r.company} · ${r.location}`),
            el("div", { class: "blurb" }, r.highlights.slice(0, 2).join(" ")),
            el(
              "div",
              { class: "tagrow" },
              ...r.framing.map((f) => tag(f, f === "Product" ? "prod" : "eng")),
            ),
          ),
        ),
      ),
    ),
  );

  root.appendChild(
    el(
      "section",
      { class: "card card-eng" },
      el(
        "div",
        { class: "card-head" },
        el("div", { class: "card-title" }, "Voice"),
        el("div", { class: "card-sub" }, "vocabulary the engineering resume reaches for"),
      ),
      el("p", { class: "voice-line" }, p.voice),
    ),
  );
}

/* ============================================================
 *  VIEW: COMBINED PHENOTYPE (the fighter card)
 * ============================================================ */

/* Axis provenance — additive footnote table below the radar.
   Each row maps a composite axis to the published framework(s)
   that informed its name + scoring band. */
const AXIS_PROVENANCE = [
  { axis: "systems_thinking",      source: "Larson \u201Cbig-picture thinking\u201D + Reilly \u201Csetting technical direction\u201D" },
  { axis: "execution_speed",       source: "Larson \u201Cexecution\u201D + AWS Skill Builder \u201CMethod\u201D" },
  { axis: "product_judgment",      source: "Fournier \u201Ctechnical judgment\u201D + AWS \u201CPurpose\u201D" },
  { axis: "ai_native",             source: "(Author addition — no published framework yet)" },
  { axis: "production_discipline", source: "Charity Majors \u201Cproduction triangle\u201D + AWS \u201CProcess\u201D" },
  { axis: "leadership_no_authority", source: "Larson \u201Cinfluence\u201D + Reilly \u201Ccatalyzing action\u201D" },
  { axis: "ambiguity_tolerance",   source: "Reilly \u201Cdriving consensus in ambiguous situations\u201D" },
  { axis: "learning_velocity",     source: "Charity Majors \u201Cfailure as data\u201D + SFIA \u201CPersonal & Professional Development\u201D" },
];

function renderPhenotype(root) {
  root.appendChild(
    el(
      "section",
      { class: "pheno-hero" },
      el("div", { class: "pheno-eyebrow" }, "DERIVED · BLIND REVIEW"),
      el("h1", { class: "pheno-title" }, PHENOTYPE.title),
      el("div", { class: "pheno-tagline" }, PHENOTYPE.tagline),
      el("p", { class: "pheno-one" }, PHENOTYPE.oneLiner),
    ),
  );

  /* big radar w/ ring scale */
  const axes = PHENOTYPE.axes.map((a) => ({ label: a.label, score: a.score }));
  const radarCard = el(
    "section",
    { class: "pheno-card" },
    el(
      "div",
      { class: "pheno-card-head" },
      el("div", { class: "pheno-card-title" }, "Fighter Card · Skill Composite"),
      el("div", { class: "pheno-card-sub" }, PHENOTYPE.selectedTier),
    ),
    el(
      "div",
      { class: "pheno-radar-wrap" },
      buildRadar(axes, {
        rings: PHENOTYPE.rings,
        accent: PHENOTYPE.color,
        size: 620,
      }),
    ),
  );
  root.appendChild(radarCard);

  /* scoring methodology + axis provenance — additive footnote.
     Anchors the radar to published frameworks so the composite is
     auditable rather than vibes-based. */
  root.appendChild(
    el(
      "section",
      { class: "pheno-card" },
      el(
        "div",
        { class: "pheno-card-head" },
        el("div", { class: "pheno-card-title" }, "Scoring Methodology"),
        el("div", { class: "pheno-card-sub" }, "audit-grade footnote"),
      ),
      el(
        "div",
        { class: "callout", html:
          "<p style=\"margin:0 0 10px;\"><strong>Scoring model.</strong> Axis scores (0–10) are anchored to the Dreyfus model of skill acquisition (Dreyfus &amp; Dreyfus, <em>Mind Over Machine</em>, 1986) — 0–2 Novice, 3–4 Advanced Beginner, 5–6 Competent, 7–8 Proficient, 9–10 Expert — and cross-referenced to <a href=\"https://sfia-online.org/en/sfia-8-framework\" target=\"_blank\" rel=\"noopener\">SFIA 8 levels</a> (SFIA 3 = 4–5, SFIA 4 = 6–7, SFIA 5 = 8, SFIA 6 = 9, SFIA 7 = 10). Axis names follow Larson (2021) and Reilly (2022) Staff-Engineer competency frameworks; <code>ai_native</code> is an author addition (no published builder-IC framework yet covers this axis).</p>" +
          "<h4 class=\"pheno-mini-h\">Axis provenance</h4>" +
          "<table class=\"cite-table cite-table-compact\">" +
            "<thead><tr><th>Axis</th><th>Source framework</th></tr></thead>" +
            "<tbody>" +
              AXIS_PROVENANCE.map((a) =>
                `<tr><td><code>${a.axis}</code></td><td>${a.source}</td></tr>`
              ).join("") +
            "</tbody>" +
          "</table>"
        }
      ),
    ),
  );

  /* superpowers */
  root.appendChild(
    el(
      "section",
      { class: "pheno-section" },
      el(
        "div",
        { class: "pheno-section-head" },
        el("div", { class: "pheno-section-title" }, "Superpowers"),
        el("div", { class: "pheno-section-sub" }, "what's hard to replace"),
      ),
      el(
        "div",
        { class: "pheno-grid" },
        ...PHENOTYPE.superpowers.map((s) =>
          el(
            "div",
            { class: "power-card" },
            el("div", { class: "power-num" }, "★"),
            el("div", { class: "power-name" }, s.name),
            el("div", { class: "power-detail" }, s.detail),
          ),
        ),
      ),
    ),
  );

  /* friction points */
  root.appendChild(
    el(
      "section",
      { class: "pheno-section" },
      el(
        "div",
        { class: "pheno-section-head" },
        el("div", { class: "pheno-section-title" }, "Friction Points"),
        el("div", { class: "pheno-section-sub" }, "honest deltas — what could bite"),
      ),
      el(
        "ul",
        { class: "friction-list" },
        ...PHENOTYPE.frictionPoints.map((f) =>
          el("li", {}, el("span", { class: "friction-bullet" }, "⚠"), el("span", {}, f)),
        ),
      ),
    ),
  );

  /* tier ladder */
  root.appendChild(
    el(
      "section",
      { class: "pheno-section" },
      el(
        "div",
        { class: "pheno-section-head" },
        el("div", { class: "pheno-section-title" }, "Tier Ladder"),
        el("div", { class: "pheno-section-sub" }, "where the composite lands"),
      ),
      el(
        "div",
        { class: "tier-ladder" },
        ...PHENOTYPE.rings.map((r, i) => {
          const filled = i <= 3; // mark filled for the tier
          return el(
            "div",
            { class: `tier ${filled ? "tier-on" : ""} ${i === 3 ? "tier-here" : ""}` },
            el("div", { class: "tier-idx" }, `0${i + 1}`),
            el("div", { class: "tier-name" }, r),
            i === 3 ? el("div", { class: "tier-pin" }, "← here") : null,
          );
        }),
      ),
    ),
  );
}

/* ============================================================
 *  VIEW: RECRUITER
 * ============================================================ */

/* Citation anchors for the role-fit chips (additive — see sources card).
   match is a substring of the chip label in data/phenotype.js; marker is
   the superscript rendered on the chip + cited row in the table. */
const ROLE_FIT_CITATIONS = [
  {
    match: "Senior-track",
    label: "Senior-Track in Platform / Dev-Tools",
    title: "Will Larson — staffeng.com",
    url: "https://staffeng.com/",
    marker: "1",
  },
  {
    match: "Founding Engineer",
    label: "Founding Engineer / #2",
    title: "Harj Taggar — \u201CBuild the #2 at a Startup\u201D",
    url: "https://www.harjtaggar.com/build-the-2-at-a-startup/",
    marker: "2",
  },
  {
    match: "TPM-Eng",
    label: "TPM-Eng Hybrid",
    title: "Google Careers — Technical Program Management",
    url: "https://www.google.com/about/careers/teams/engineering/technical-program-management/",
    marker: "3",
  },
  {
    match: "Founder-in-Residence",
    label: "Founder-in-Residence (FiR)",
    title: "Antler — Founder in Residence program",
    url: "https://www.antler.co/program/founder-in-residence",
    marker: "4",
  },
];

function renderRecruiter(root) {
  const c = RECRUITER_STATS;
  /* personal */
  root.appendChild(
    el(
      "section",
      { class: "rec-section" },
      el(
        "div",
        { class: "rec-section-head" },
        el("div", { class: "rec-eyebrow" }, "PERSONAL · blind inference"),
        el("h2", { class: "rec-title" }, "Who is this person?"),
      ),
      el(
        "div",
        { class: "rec-grid-2" },
        el(
          "div",
          { class: "card card-pheno" },
          el("div", { class: "kpi-k" }, "ESTIMATED AGE"),
          el("div", { class: "rec-big" }, c.personal.estimatedAgeRangeYears),
          el("div", { class: "rec-h" }, "yrs · mid ≈ 25"),
          el("p", { class: "rec-reason" }, c.personal.ageReasoning),
        ),
        el(
          "div",
          { class: "card card-eng" },
          el("div", { class: "kpi-k" }, "LOCATION SIGNAL"),
          el("div", { class: "rec-big" }, "Santa Monica"),
          el("div", { class: "rec-h" }, "CA · 424 area code"),
          el("p", { class: "rec-reason" }, c.personal.locationSignal),
        ),
        el(
          "div",
          { class: "card card-prod" },
          el("div", { class: "kpi-k" }, "LIFESTYLE SIGNAL"),
          el("div", { class: "rec-big" }, "Founder-mode"),
          el("div", { class: "rec-h" }, "while finishing MS"),
          el("p", { class: "rec-reason" }, c.personal.lifestyleSignal),
        ),
      ),
    ),
  );

  /* corporate vehicle — recruiter needs to know the legal entity + IP status
     of a founder's brand before reaching out about IP, contracts, or comp. */
  const id = IDENTITY;
  const tm = id.trademark || {};
  root.appendChild(
    el(
      "section",
      { class: "rec-section" },
      el(
        "div",
        { class: "rec-section-head" },
        el("div", { class: "rec-eyebrow" }, "CORPORATE VEHICLE & IP"),
        el("h2", { class: "rec-title" }, "How to refer to this company"),
      ),
      el(
        "div",
        { class: "rec-grid-2" },
        el(
          "div",
          { class: "card card-pheno" },
          el("div", { class: "kpi-k" }, "DOING-BUSINESS-AS"),
          el("div", { class: "rec-big" }, id.legalName || id.brand),
          el("div", { class: "rec-h" }, id.location || ""),
          el("p", { class: "rec-reason" }, id.legalEntity
            ? `Legal entity: ${id.legalEntity}`
            : "Legal entity disclosed in outreach."),
        ),
        el(
          "div",
          { class: "card card-eng" },
          el("div", { class: "kpi-k" }, "INTELLECTUAL PROPERTY"),
          el(
            "div",
            { class: "rec-big" },
            tm.status || "USPTO Trademark",
          ),
          el("div", { class: "rec-h" }, tm.mark || id.legalName || ""),
          el(
            "p",
            { class: "rec-reason" },
            tm.note ||
              `Trademark status confirmed for "${id.legalName || id.brand}".`,
          ),
        ),
      ),
      tm.source
        ? el(
            "p",
            { class: "cite-foot" },
            "Source: ",
            el("a", { href: tm.source, target: "_blank", rel: "noopener" }, tm.source),
            tm.status ? ` · status as of contact` : "",
          )
        : null,
    ),
  );

  /* professional */
  root.appendChild(
    el(
      "section",
      { class: "rec-section" },
      el(
        "div",
        { class: "rec-section-head" },
        el("div", { class: "rec-eyebrow" }, "PROFESSIONAL"),
        el("h2", { class: "rec-title" }, "Track record"),
      ),
      el(
        "div",
        { class: "rec-grid-4" },
        kpi({
          k: "YRS POST-SECONDARY EDU",
          v: `~${c.professional.yearsOfPostSecondaryEducation}`,
          h: `${EDUCATION.degrees.length} degrees`,
          accent: "eng",
        }),
        kpi({
          k: "YRS PROFESSIONAL EXP",
          v: `~${c.professional.yearsOfProfessionalExperienceApprox}`,
          h: "concurrent w/ study",
          accent: "prod",
        }),
        kpi({
          k: "CUM. GPA",
          v: c.professional.cumulativeGpa.toFixed(2),
          h: "ASU · Barrett Honors",
          accent: "eng",
        }),
        kpi({
          k: "HONORS TRACK",
          v: "Barrett",
          h: EDUCATION.honorsCollege,
          accent: "pheno",
        }),
      ),
      el(
        "div",
        { class: "rec-detail" },
        el(
          "div",
          { class: "rec-detail-row" },
          el("div", { class: "rec-detail-k" }, "Experience reasoning"),
          el("div", { class: "rec-detail-v" }, c.professional.experienceReasoning),
        ),
        el(
          "div",
          { class: "rec-detail-row" },
          el("div", { class: "rec-detail-k" }, "Concurrent roles"),
          el("div", { class: "rec-detail-v" }, c.professional.concurrentRoles),
        ),
        el(
          "div",
          { class: "rec-detail-row" },
          el("div", { class: "rec-detail-k" }, "Role diversity"),
          el("div", { class: "rec-detail-v" }, c.professional.roleSpanDiversity),
        ),
        el(
          "div",
          { class: "rec-detail-row" },
          el("div", { class: "rec-detail-k" }, "Industry diversity"),
          el("div", { class: "rec-detail-v" }, c.professional.industryDiversity),
        ),
        el(
          "div",
          { class: "rec-detail-row" },
          el("div", { class: "rec-detail-k" }, "Geo flexibility"),
          el("div", { class: "rec-detail-v" }, c.professional.geoFlex),
        ),
      ),
    ),
  );

  /* impact signals grid */
  root.appendChild(
    el(
      "section",
      { class: "rec-section" },
      el(
        "div",
        { class: "rec-section-head" },
        el("div", { class: "rec-eyebrow" }, "IMPACT"),
        el("h2", { class: "rec-title" }, "Numbers recruiters ask for"),
      ),
      el(
        "div",
        { class: "impact-grid" },
        ...c.impactSignals.map((s) =>
          el(
            "div",
            { class: "impact-card" },
            el("div", { class: "impact-metric" }, s.metric),
            el("div", { class: "impact-value" }, s.value),
          ),
        ),
      ),
    ),
  );

  /* stack */
  root.appendChild(
    el(
      "section",
      { class: "rec-section" },
      el(
        "div",
        { class: "rec-section-head" },
        el("div", { class: "rec-eyebrow" }, "STACK"),
        el("h2", { class: "rec-title" }, "Languages, ranked"),
      ),
      el(
        "div",
        { class: "stack-tiers" },
        ...[1, 2, 3].map((tier) =>
          el(
            "div",
            { class: "stack-tier" },
            el("div", { class: "stack-tier-k" }, `Tier ${tier}`),
            el(
              "div",
              { class: "stack-tier-v" },
              ...c.stack
                .filter((s) => s.tier === tier)
                .map((s) => el("span", { class: "stack-pill" }, s.label)),
            ),
          ),
        ),
      ),
    ),
  );

  /* fit profiles */
  root.appendChild(
    el(
      "section",
      { class: "rec-section" },
      el(
        "div",
        { class: "rec-section-head" },
        el("div", { class: "rec-eyebrow" }, "FIT PROFILES"),
        el("h2", { class: "rec-title" }, "Roles that match this phenotype"),
      ),
      el(
        "ul",
        { class: "fit-list" },
        ...c.fitProfiles.map((f) => {
          const cite = ROLE_FIT_CITATIONS.find((c) => f.includes(c.match));
          const sup = cite
            ? el("sup", { class: "fit-cite", title: cite.title }, cite.marker)
            : null;
          return el(
            "li",
            {},
            el("span", { class: "fit-bullet" }, "→"),
            el("span", {}, f),
            sup,
          );
        }),
      ),
    ),
  );

  /* methodology / sources — additive citation card for recruiters */
  root.appendChild(
    el(
      "section",
      { class: "rec-section" },
      el(
        "div",
        { class: "rec-section-head" },
        el("div", { class: "rec-eyebrow" }, "METHODOLOGY · SOURCES"),
        el("h2", { class: "rec-title" }, "Why these role-fits?"),
      ),
      el(
        "div",
        { class: "callout", html:
          "<p style=\"margin:0 0 10px;\"><strong>Why these role-fits?</strong> Each chip above links to the strongest published framework or builder essay that anchors the claim. Citations are additive — the phenotype itself is derived from the candidate's actual artifacts, not the cited sources.</p>" +
          "<table class=\"cite-table\">" +
            "<thead><tr><th>Role-Fit</th><th>Citation</th><th>URL</th></tr></thead>" +
            "<tbody>" +
              ROLE_FIT_CITATIONS.map((c) =>
                `<tr><td>${c.label}<sup>${c.marker}</sup></td><td>${c.title}</td><td><a href="${c.url}" target="_blank" rel="noopener">${c.url.replace(/^https?:\/\//, "")}</a></td></tr>`
              ).join("") +
            "</tbody>" +
          "</table>"
        }
      ),
    ),
  );

  /* timeline-h at bottom */
  root.appendChild(
    el(
      "section",
      { class: "rec-section" },
      el(
        "div",
        { class: "rec-section-head" },
        el("div", { class: "rec-eyebrow" }, "TIMELINE"),
        el("h2", { class: "rec-title" }, "Career so far"),
      ),
      el(
        "div",
        { class: "timeline-h" },
        ...ROLES.map((r, i) => {
          const cls = i === 0 ? "amber" : i === 1 ? "blue" : i === 2 ? "lime" : "blue";
          return el(
            "div",
            { class: `col ${cls}` },
            el("div", { class: "k" }, r.company),
            el("div", { class: "v" }, r.span),
            el("div", { class: "h" }, `${r.start} → ${r.end} · ${r.title}`),
          );
        }),
      ),
    ),
  );

  /* footer */
  root.appendChild(
    el(
      "footer",
      { class: "rec-footer" },
      "Generated ",
      el("code", {}, new Date(SOURCE.generated).toLocaleString()),
      " · Sources: ",
      el("code", {}, SOURCE.product),
      " · ",
      el("code", {}, SOURCE.engineering),
    ),
  );
}

/* ---------- public-record view ---------- */
/* honest, citation-backed view contrasting the polished resume (PDFs)
 * with the messy public record: GitHub bio, phenotype.us hardware brand,
 * patents-public-record check, social handles with confidence ratings. */
function renderPublicRecord(root) {
  const PR = PUBLIC_RECORD;

  const linkAnchor = (url, label) =>
    el(
      "a",
      { href: url, target: "_blank", rel: "noopener noreferrer" },
      label || url,
    );
  const linkHost = (url) => url.replace(/^https?:\/\//, "").replace(/\/$/, "");
  const verdictClass = (v) => {
    if (v === "matches") return "pr-verdict-matches";
    if (v === "contradicts") return "pr-verdict-contradicts";
    return "pr-verdict-unverified";
  };
  const confClass = (c) => {
    const k = String(c || "").toLowerCase();
    if (k === "high" || k === "medium-high") return "pr-conf-high";
    if (k === "medium") return "pr-conf-medium";
    if (k === "not found") return "pr-conf-notfound";
    return "pr-conf-low";
  };

  /* 1. Top honesty callout */
  root.appendChild(
    el(
      "section",
      { class: "section pr-callout" },
      el("div", { class: "section-head" },
        el("div", { class: "eyebrow" }, "PUBLIC RECORD · HONEST FRAMING"),
        el("h1", { class: "section-title" }, "Resume vs. Public-Record"),
      ),
      el("p", { class: "pr-callout-body" },
        "The resume describes Koosha as a senior software engineer and founder at Phenotype. ",
        "Public records tell a more complicated story — same person, two product surfaces (hardware keyboard brand + software portfolio), ",
        "and a GitHub bio that openly disclaims the polished resume voice (\u201CAI Slop Post ~Apr 2025\u201D). ",
        "What\u2019s below is what the public web actually shows, with citations."
      ),
      el("div", { class: "pr-callout-meta" },
        el("span", {}, "Generated "),
        el("code", {}, PR.generatedAt),
        el("span", {}, " · "),
        el("span", {}, PR.generatedBy),
      ),
    ),
  );

  /* 2. Resume vs Public-Record table */
  const verdictRows = PR.resumeVsPublic.map((row) =>
    el(
      "tr",
      {},
      el("td", { class: "pr-col-claim" }, row.claim),
      el("td", { class: "pr-col-resume" }, row.resumeSays),
      el("td", { class: "pr-col-pub" }, row.publicRecord),
      el("td", { class: `pr-col-verdict ${verdictClass(row.verdict)}` }, row.verdict),
      el("td", { class: "pr-col-cite" },
        ...row.citations.map((u) => linkAnchor(u, linkHost(u))),
      ),
    ),
  );

  root.appendChild(
    el(
      "section",
      { class: "section" },
      el("div", { class: "section-head" },
        el("div", { class: "eyebrow" }, "TABLE 1"),
        el("h2", { class: "section-title" }, "Resume vs. Public-Record"),
      ),
      el("div", { class: "card" },
        el("div", { class: "table-wrap" },
          el("table", { class: "pr-table" },
            el("thead", {},
              el("tr", {},
                el("th", {}, "Claim"),
                el("th", {}, "Resume says"),
                el("th", {}, "Public record"),
                el("th", {}, "Verdict"),
                el("th", {}, "Citations"),
              ),
            ),
            el("tbody", {}, ...verdictRows),
          ),
        ),
      ),
    ),
  );

  /* 3. GitHub card */
  const gh = PR.github;
  const ghCounts = [
    ["repos", gh.repos],
    ["stars", gh.stars],
    ["followers", gh.followers],
    ["following", gh.following],
  ];
  root.appendChild(
    el(
      "section",
      { class: "section" },
      el("div", { class: "section-head" },
        el("div", { class: "eyebrow" }, "PROFILE · GITHUB"),
        el("h2", { class: "section-title" },
          el("a", { href: gh.url, target: "_blank", rel: "noopener noreferrer" }, "@" + gh.handle),
        ),
        el("div", { class: "section-sub" },
          "user_id " + gh.userId + " · ",
          linkAnchor(gh.url + "?tab=repositories", "repos"),
          " · ",
          linkAnchor(gh.url + "?tab=stars", "stars"),
        ),
      ),
      el("div", { class: "grid-3 pr-gh-grid" },
        ...ghCounts.map(([k, v]) =>
          el("div", { class: "card pr-stat" },
            el("div", { class: "pr-stat-k" }, k),
            el("div", { class: "pr-stat-v" }, String(v)),
          ),
        ),
      ),
      el("div", { class: "card pr-quote-card" },
        el("div", { class: "eyebrow" }, "BIO · VERBATIM"),
        el("blockquote", { class: "pr-quote" }, gh.bio),
        el("div", { class: "pr-quote-cite" }, "— github.com/" + gh.handle + " profile"),
      ),
      el("div", { class: "card" },
        el("div", { class: "eyebrow" }, "TOP REPOS"),
        el("ul", { class: "list" },
          ...gh.topRepos.map((r) =>
            el("li", { class: "list-item" },
              el("div", { class: "pr-repo-row" },
                el("a", { href: r.url, target: "_blank", rel: "noopener noreferrer", class: "pr-repo-name" }, r.name),
                el("span", { class: "pr-repo-stars" },
                  r.stars != null ? "\u2605 " + r.stars : "\u2605 —",
                ),
                el("span", { class: "pr-repo-note" }, r.note),
              ),
            ),
          ),
        ),
        el("div", { class: "eyebrow pr-starlist-eyebrow" }, "CURATED STAR LISTS"),
        el("div", { class: "tag-row" },
          ...gh.starLists.map((s) => el("span", { class: "tag" }, s)),
        ),
      ),
    ),
  );

  /* 4. Phenotype brand disambiguation (hardware vs software) */
  const hw = PR.phenotypeBrand.hardware;
  const sw = PR.phenotypeBrand.software;
  root.appendChild(
    el(
      "section",
      { class: "section" },
      el("div", { class: "section-head" },
        el("div", { class: "eyebrow" }, "DISAMBIGUATION · PHENOTYPE"),
        el("h2", { class: "section-title" }, "One DBA, Two Product Surfaces"),
      ),
      el("div", { class: "grid-2" },
        el("div", { class: "card" },
          el("div", { class: "eyebrow" }, "HARDWARE · STOREFRONT"),
          el("h3", { class: "pr-side-title" },
            el("a", { href: hw.storeUrl, target: "_blank", rel: "noopener noreferrer" }, "phenotype.us"),
          ),
          el("p", { class: "pr-side-desc" }, hw.description),
          el("div", { class: "pr-side-meta" },
            el("div", {}, el("strong", {}, "Legal footer: "), hw.footerConfirmedLegal),
            el("div", {}, el("strong", {}, "Phone: "), hw.phone),
          ),
          el("div", { class: "eyebrow pr-mini-eyebrow" }, "KEYCAP SETS"),
          el("div", { class: "tag-row" },
            ...hw.products.map((p) => el("span", { class: "tag" }, p)),
          ),
        ),
        el("div", { class: "card" },
          el("div", { class: "eyebrow" }, "SOFTWARE · PORTFOLIO"),
          el("h3", { class: "pr-side-title" },
            el("a", { href: sw.portfolioUrl, target: "_blank", rel: "noopener noreferrer" }, "projects.kooshapari.com"),
          ),
          el("p", { class: "pr-side-desc" },
            sw.projectCount + " repos · " + sw.generatedBy,
          ),
          el("div", { class: "eyebrow pr-mini-eyebrow" }, "FLAGSHIP REPOS"),
          el("div", { class: "tag-row pr-flagships" },
            ...sw.flagshipRepos.map((r) =>
              el("a", {
                href: "https://github.com/KooshaPari/" + r,
                target: "_blank",
                rel: "noopener noreferrer",
                class: "tag pr-flagship",
              }, r),
            ),
          ),
        ),
      ),
      el("div", { class: "callout pr-disambig-callout" },
        PR.phenotypeBrand.disambiguation,
      ),
    ),
  );

  /* 5. Confirmed social handles table */
  const socialRows = PR.socialHandles.map((s) => {
    const cls = confClass(s.confidence);
    const handleCell = s.url
      ? linkAnchor(s.url, s.handle)
      : el("span", { class: "pr-handle-none" }, s.handle);
    return el(
      "tr",
      {},
      el("td", { class: "pr-col-platform" }, s.platform),
      el("td", { class: "pr-col-handle" }, handleCell),
      el("td", { class: `pr-col-conf ${cls}` }, s.confidence),
      el("td", { class: "pr-col-cite" }, s.url ? linkHost(s.url) : "\u2014"),
    );
  });
  root.appendChild(
    el(
      "section",
      { class: "section" },
      el("div", { class: "section-head" },
        el("div", { class: "eyebrow" }, "TABLE 2"),
        el("h2", { class: "section-title" }, "Social Handles & Confidence"),
      ),
      el("div", { class: "card" },
        el("div", { class: "table-wrap" },
          el("table", { class: "pr-table" },
            el("thead", {},
              el("tr", {},
                el("th", {}, "Platform"),
                el("th", {}, "Handle"),
                el("th", {}, "Confidence"),
                el("th", {}, "URL"),
              ),
            ),
            el("tbody", {}, ...socialRows),
          ),
        ),
      ),
    ),
  );

  /* 6. Legal entity + trademark */
  const le = PR.legalEntity;
  const tm = PR.trademark;
  root.appendChild(
    el(
      "section",
      { class: "section" },
      el("div", { class: "section-head" },
        el("div", { class: "eyebrow" }, "CORPORATE · IP"),
        el("h2", { class: "section-title" }, "Legal Entity + Trademark"),
      ),
      el("div", { class: "grid-2" },
        el("div", { class: "card" },
          el("div", { class: "eyebrow" }, "LEGAL ENTITY"),
          el("h3", { class: "pr-side-title" }, le.name),
          el("dl", { class: "pr-kv" },
            el("dt", {}, "State"), el("dd", {}, le.state),
            el("dt", {}, "Status"), el("dd", {}, le.status),
            el("dt", {}, "Formed"), el("dd", {}, le.formed),
            el("dt", {}, "Source"),
            el("dd", {}, linkAnchor(le.bizapediaUrl, linkHost(le.bizapediaUrl))),
          ),
        ),
        el("div", { class: "card" },
          el("div", { class: "eyebrow" }, "TRADEMARK"),
          el("h3", { class: "pr-side-title" }, tm.mark),
          el("dl", { class: "pr-kv" },
            el("dt", {}, "Owner"), el("dd", {}, tm.owner),
            el("dt", {}, "Goods / services"), el("dd", {}, tm.goodsServices),
            el("dt", {}, "First use in commerce"), el("dd", {}, tm.firstUseInCommerce),
            el("dt", {}, "Verification"),
            el("dd", {}, tm.verificationStatus),
          ),
          el("div", { class: "pr-mini-cite" },
            "Cited: ",
            ...tm.citations.map((u, i) => [
              i > 0 ? " · " : "",
              linkAnchor(u, linkHost(u)),
            ]),
          ),
        ),
      ),
    ),
  );

  /* 7. Patents (honest) */
  const pat = PR.patents;
  root.appendChild(
    el(
      "section",
      { class: "section" },
      el("div", { class: "section-head" },
        el("div", { class: "eyebrow" }, "IP · PATENTS"),
        el("h2", { class: "section-title" }, "Patents (Honest Check)"),
      ),
      el("div", { class: "card pr-patent-card" },
        el("div", { class: "pr-patent-zero" },
          el("div", { class: "pr-patent-zero-num" }, "0"),
          el("div", { class: "pr-patent-zero-label" }, "public results"),
        ),
        el("div", { class: "pr-patent-body" },
          el("p", {}, el("strong", {}, "Claimed in PDFs: "), pat.claimed),
          el("p", { class: "pr-patent-finding" },
            el("strong", {}, "Public search result: "),
            pat.publicSearchResult,
          ),
          el("p", {}, el("strong", {}, "Confidence: "), pat.confidence),
          el("p", {}, el("strong", {}, "Recommended next search: "), pat.recommendedNextSearch),
          el("p", { class: "pr-patent-cite" },
            "Source: ",
            linkAnchor(pat.citations[0], linkHost(pat.citations[0])),
          ),
        ),
      ),
    ),
  );

  /* 8. Writing (Medium) */
  root.appendChild(
    el(
      "section",
      { class: "section" },
      el("div", { class: "section-head" },
        el("div", { class: "eyebrow" }, "WRITING"),
        el("h2", { class: "section-title" }, "Medium Articles (Titles Only)"),
      ),
      el("div", { class: "card" },
        el("ul", { class: "list" },
          ...PR.writing.map((w) =>
            el("li", { class: "list-item" },
              el("a", { href: w.url, target: "_blank", rel: "noopener noreferrer", class: "pr-write-title" }, w.title),
              el("div", { class: "pr-write-meta" }, w.confidence),
            ),
          ),
        ),
      ),
    ),
  );

  /* 9. Personal domains */
  root.appendChild(
    el(
      "section",
      { class: "section" },
      el("div", { class: "section-head" },
        el("div", { class: "eyebrow" }, "PERSONAL DOMAINS"),
        el("h2", { class: "section-title" }, "Owned URLs"),
      ),
      el("div", { class: "card" },
        el("ul", { class: "list" },
          ...PR.personalDomains.map((d) =>
            el("li", { class: "list-item" },
              el("a", { href: d.url, target: "_blank", rel: "noopener noreferrer" }, d.url),
              el("div", { class: "pr-write-meta" }, d.note),
            ),
          ),
        ),
      ),
    ),
  );

  /* 10. NOT FOUND (dim) */
  root.appendChild(
    el(
      "section",
      { class: "section pr-dim" },
      el("div", { class: "section-head" },
        el("div", { class: "eyebrow" }, "NEGATIVE SPACE · NOT FOUND"),
        el("h2", { class: "section-title" }, "What the Public Record Does NOT Contain"),
      ),
      el("div", { class: "card" },
        el("ul", { class: "list" },
          ...PR.notFound.map((n) =>
            el("li", { class: "list-item pr-notfound-item" }, n),
          ),
        ),
      ),
    ),
  );

  /* 11. Sources footer — every cited URL */
  const allUrls = new Set();
  const collect = (arr) => {
    if (!arr) return;
    for (const x of arr) {
      if (typeof x === "string") allUrls.add(x);
    }
  };
  collect(PR.github && PR.github.citations);
  collect(PR.phenotypeBrand.hardware.citations);
  collect(PR.phenotypeBrand.software.citations);
  collect(PR.legalEntity.citations);
  collect(PR.trademark.citations);
  collect(PR.patents.citations);
  PR.resumeVsPublic.forEach((r) => collect(r.citations));
  PR.socialHandles.forEach((s) => { if (s.url) allUrls.add(s.url); });

  const sortedUrls = Array.from(allUrls).sort();
  root.appendChild(
    el(
      "section",
      { class: "section" },
      el("div", { class: "section-head" },
        el("div", { class: "eyebrow" }, "SOURCES"),
        el("h2", { class: "section-title" }, "All Cited URLs (" + sortedUrls.length + ")"),
      ),
      el("div", { class: "card" },
        el("ul", { class: "list pr-sources-list" },
          ...sortedUrls.map((u) =>
            el("li", { class: "list-item" },
              linkAnchor(u, linkHost(u)),
              el("span", { class: "pr-sources-full" }, u),
            ),
          ),
        ),
      ),
    ),
  );
}

/* ---------- init ---------- */
const VALID_VIEWS = ["home", "engineering", "product", "work", "resume", "contact"];
function initialView() {
  const h = (location.hash || "").replace("#", "");
  return VALID_VIEWS.includes(h) || h.startsWith("work/") ? h : "home";
}
document.addEventListener("DOMContentLoaded", () => {
  bindTabs();
  navigate(initialView());
  window.addEventListener("hashchange", () => navigate(initialView()));
  /* keyboard nav */
  document.addEventListener("keydown", (e) => {
    const map = { "1": "home", "2": "engineering", "3": "product", "4": "work", "5": "resume", "6": "contact" };
    if (map[e.key] && !e.metaKey && !e.ctrlKey && !e.altKey) {
      navigate(map[e.key]);
    }
  });
});
