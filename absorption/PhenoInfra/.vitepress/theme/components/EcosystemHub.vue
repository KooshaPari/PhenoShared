<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface Project {
  id: string
  name: string
  tagline: string
  description: string
  stack: { label: string; color: string }[]
  port: number | null
  github: string
  category: 'app' | 'api' | 'docs' | 'lib'
  primary?: boolean
}

const projects: Project[] = [
  {
    id: 'agileplus',
    name: 'AgilePlus',
    tagline: 'Spec-driven project management',
    description: 'AI-native PM platform with CLI, API, gRPC, and Tauri desktop dashboard. Tracks all Phenotype work.',
    stack: [{ label: 'Rust', color: '#ce422b' }, { label: 'Tauri', color: '#24c8db' }, { label: 'gRPC', color: '#244c5a' }],
    port: 4101,
    github: 'https://github.com/KooshaPari/AgilePlus',
    category: 'app',
    primary: true,
  },
  {
    id: 'heliosapp',
    name: 'heliosApp',
    tagline: 'TypeScript runtime application',
    description: 'Full-stack web + Tauri desktop app. Hot-reload Vite frontend, Bun runtime, Vitest + Playwright.',
    stack: [{ label: 'TypeScript', color: '#3178c6' }, { label: 'Bun', color: '#fbf0df' }, { label: 'Tauri', color: '#24c8db' }],
    port: 4102,
    github: 'https://github.com/KooshaPari/heliosApp',
    category: 'app',
  },
  {
    id: 'trace',
    name: 'TraceRTM',
    tagline: 'Requirements traceability matrix',
    description: 'Full-stack RTM with Python FastAPI backend, Go service layer, and Vite frontend. process-compose orchestrated.',
    stack: [{ label: 'Python', color: '#3572A5' }, { label: 'Go', color: '#00ADD8' }, { label: 'TypeScript', color: '#3178c6' }],
    port: 4110,
    github: 'https://github.com/KooshaPari/trace',
    category: 'app',
  },
  {
    id: 'agentapi',
    name: 'agentapi-plusplus',
    tagline: 'Agent HTTP API server',
    description: 'Go HTTP API for agent orchestration. Chat service, command routing, internal packages.',
    stack: [{ label: 'Go', color: '#00ADD8' }],
    port: null,
    github: 'https://github.com/KooshaPari/agentapi-plusplus',
    category: 'api',
  },
  {
    id: 'cliproxy',
    name: 'cliproxyapi-plusplus',
    tagline: 'Multi-provider CLI proxy',
    description: 'Go proxy supporting Claude, OpenAI, Gemini. OAuth2/PKCE, rate limiting, structured auth.',
    stack: [{ label: 'Go', color: '#00ADD8' }],
    port: null,
    github: 'https://github.com/KooshaPari/cliproxyapi-plusplus',
    category: 'api',
  },
  {
    id: 'bifrost',
    name: 'bifrost-extensions',
    tagline: 'LLM gateway extension framework',
    description: 'Go extension library for the Bifrost LLM gateway. Plugin architecture, guard timeout handling.',
    stack: [{ label: 'Go', color: '#00ADD8' }],
    port: 4104,
    github: 'https://github.com/KooshaPari/bifrost-extensions',
    category: 'lib',
  },
  {
    id: 'thegent',
    name: 'thegent',
    tagline: 'Agent framework + dotfiles manager',
    description: 'Unified agent orchestration, dotfiles management, templates, governance. The system backbone.',
    stack: [{ label: 'TypeScript', color: '#3178c6' }, { label: 'Python', color: '#3572A5' }],
    port: 4103,
    github: 'https://github.com/KooshaPari/thegent',
    category: 'lib',
  },
  {
    id: 'civ',
    name: 'civ',
    tagline: 'Continuous integration validation',
    description: 'CI validation framework and doc site. Quality gate orchestration, compliance checks.',
    stack: [{ label: 'TypeScript', color: '#3178c6' }],
    port: 4105,
    github: 'https://github.com/KooshaPari/civ',
    category: 'docs',
  },
  {
    id: 'phenodesign',
    name: 'phenoDesign',
    tagline: 'Keycap design tokens + VitePress theme',
    description: '@phenotype/design package — shared CSS tokens, VitePress theme, glass recipes. Canonical design SSOT.',
    stack: [{ label: 'TypeScript', color: '#3178c6' }, { label: 'CSS', color: '#7ebab5' }],
    port: null,
    github: 'https://github.com/KooshaPari/phenoDesign',
    category: 'lib',
  },
  {
    id: 'registry',
    name: 'phenotype-registry',
    tagline: 'Ecosystem index (spine INDEX role)',
    description: 'Canonical live ecosystem map — ECOSYSTEM_MAP.md, repo roles, dependency graph. Spine authority for what exists.',
    stack: [{ label: 'YAML', color: '#cb171e' }, { label: 'Markdown', color: '#646cff' }],
    port: null,
    github: 'https://github.com/KooshaPari/phenotype-registry/blob/main/ECOSYSTEM_MAP.md',
    category: 'docs',
    primary: true,
  },
  {
    id: 'phenodocs',
    name: 'phenodocs',
    tagline: 'Ecosystem documentation hub',
    description: 'Shared VitePress theme + @phenotype/docs package. Single source of truth for all Phenotype docs.',
    stack: [{ label: 'TypeScript', color: '#3178c6' }, { label: 'Vue', color: '#41b883' }, { label: 'VitePress', color: '#646cff' }],
    port: 4100,
    github: 'https://github.com/KooshaPari/phenodocs',
    category: 'docs',
    primary: true,
  },
]

const portStatus = ref<Record<number, 'up' | 'checking' | 'down'>>({})

const checkPort = async (port: number) => {
  portStatus.value[port] = 'checking'
  try {
    const ctrl = new AbortController()
    const id = setTimeout(() => ctrl.abort(), 1200)
    await fetch(`http://localhost:${port}`, { mode: 'no-cors', signal: ctrl.signal })
    clearTimeout(id)
    portStatus.value[port] = 'up'
  } catch {
    portStatus.value[port] = 'down'
  }
}

onMounted(() => {
  projects.forEach(p => { if (p.port) checkPort(p.port) })
})

const categoryLabel = { app: 'Application', api: 'API Service', docs: 'Docs Site', lib: 'Library' }
const categoryColor = { app: '#7ebab5', api: '#00ADD8', docs: '#646cff', lib: '#ce422b' }

const categories = ['app', 'api', 'docs', 'lib'] as const
</script>

<template>
  <div class="hub">
    <!-- Header grid -->
    <div class="hub-header">
      <div class="hub-signal"></div>
      <div class="hub-title-block">
        <div class="hub-eyebrow">PHENOTYPE ECOSYSTEM</div>
        <h1 class="hub-headline">Platform Hub</h1>
        <p class="hub-sub">All services, docs, and APIs — live navigation and status.</p>
      </div>
      <div class="hub-meta">
        <a href="https://github.com/KooshaPari/phenotype-registry/blob/main/ECOSYSTEM_MAP.md" class="hub-meta-link" target="_blank">
          ECOSYSTEM_MAP
        </a>
        <span class="hub-dot">·</span>
        <a href="https://github.com/KooshaPari" class="hub-meta-link" target="_blank">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/></svg>
          KooshaPari
        </a>
        <span class="hub-dot">·</span>
        <span class="hub-count">{{ projects.length }} projects</span>
      </div>
    </div>

    <!-- Project grid by category -->
    <div v-for="cat in categories" :key="cat" class="hub-section">
      <div class="hub-section-header">
        <span class="hub-section-tag" :style="{ borderColor: categoryColor[cat], color: categoryColor[cat] }">
          {{ categoryLabel[cat] }}
        </span>
        <div class="hub-section-rule"></div>
      </div>

      <div class="hub-grid">
        <div
          v-for="p in projects.filter(x => x.category === cat)"
          :key="p.id"
          class="hub-card"
          :class="{ 'hub-card--primary': p.primary }"
        >
          <!-- Status dot -->
          <div class="hub-card-top">
            <div class="hub-card-name">{{ p.name }}</div>
            <div v-if="p.port" class="hub-status" :class="`hub-status--${portStatus[p.port] ?? 'checking'}`">
              <span class="hub-status-dot"></span>
              <span class="hub-status-label">{{ portStatus[p.port] === 'up' ? 'live' : portStatus[p.port] === 'down' ? 'down' : '…' }}</span>
            </div>
          </div>

          <div class="hub-card-tagline">{{ p.tagline }}</div>
          <p class="hub-card-desc">{{ p.description }}</p>

          <!-- Stack badges -->
          <div class="hub-stack">
            <span
              v-for="s in p.stack"
              :key="s.label"
              class="hub-badge"
              :style="{ '--badge-color': s.color }"
            >{{ s.label }}</span>
          </div>

          <!-- Links -->
          <div class="hub-card-links">
            <a v-if="p.port" :href="`http://localhost:${p.port}`" target="_blank" class="hub-link hub-link--primary">
              <span class="hub-link-icon">↗</span> :{{ p.port }}
            </a>
            <a :href="p.github" target="_blank" class="hub-link hub-link--ghost">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/></svg>
              GitHub
            </a>
          </div>
        </div>
      </div>
    </div>

    <!-- Port reference table -->
    <div class="hub-ports">
      <div class="hub-ports-header">
        <span class="hub-section-tag" style="border-color: #353a40; color: #6b7280">DEV PORTS</span>
        <div class="hub-section-rule"></div>
      </div>
      <div class="hub-ports-grid">
        <div v-for="p in projects.filter(x => x.port)" :key="p.id" class="hub-port-row">
          <span class="hub-port-num">:{{ p.port }}</span>
          <span class="hub-port-name">{{ p.name }}</span>
          <span class="hub-port-status" :class="`hub-port-status--${portStatus[p.port!] ?? 'checking'}`">
            {{ portStatus[p.port!] === 'up' ? '● live' : portStatus[p.port!] === 'down' ? '○ down' : '◌ …' }}
          </span>
          <a :href="`http://localhost:${p.port}`" target="_blank" class="hub-port-link">open ↗</a>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Edited 2026-05-04 (frontend-engineer task):
   Removed external Google Fonts @import (Space Mono / DM Sans). Render-blocking
   third-party CSS request 404s under strict CSP and offline previews. Use the
   system mono / sans stack — visually equivalent for hub cards. */

.hub {
  --teal: #7ebab5;
  --teal-dim: #4a8a85;
  --midnight: #090a0c;
  --surface: #111316;
  --surface-2: #181b1f;
  --border: #1e2227;
  --border-bright: #2a2f37;
  --text-1: #f0efee;
  --text-2: #8a9099;
  --text-3: #4a5060;
  --mono: 'Space Mono', ui-monospace, monospace;
  --sans: 'DM Sans', system-ui, sans-serif;

  font-family: var(--sans);
  max-width: 1100px;
  margin: 0 auto;
  padding: 3rem 1.5rem 5rem;
}

/* ── Header ──────────────────────────────── */
.hub-header {
  display: grid;
  grid-template-columns: 3px 1fr auto;
  gap: 0 1.5rem;
  align-items: start;
  margin-bottom: 4rem;
  padding-bottom: 2rem;
  border-bottom: 1px solid var(--border);
}

.hub-signal {
  width: 3px;
  height: 100%;
  background: linear-gradient(to bottom, var(--teal), transparent);
  border-radius: 2px;
}

.hub-eyebrow {
  font-family: var(--mono);
  font-size: 0.65rem;
  letter-spacing: 0.2em;
  color: var(--teal);
  margin-bottom: 0.6rem;
  text-transform: uppercase;
}

.hub-headline {
  font-family: var(--sans);
  font-size: clamp(2rem, 5vw, 3.5rem);
  font-weight: 300;
  color: var(--text-1);
  line-height: 1.05;
  margin: 0 0 0.75rem;
  letter-spacing: -0.03em;
}

.hub-sub {
  color: var(--text-2);
  font-size: 1rem;
  font-weight: 300;
  margin: 0;
}

.hub-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: var(--mono);
  font-size: 0.72rem;
  color: var(--text-3);
  padding-top: 0.25rem;
  white-space: nowrap;
}

.hub-meta-link {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--text-2);
  text-decoration: none;
  transition: color 0.15s;
}
.hub-meta-link:hover { color: var(--teal); }
.hub-dot { color: var(--border-bright); }

/* ── Section headers ─────────────────────── */
.hub-section { margin-bottom: 3rem; }

.hub-section-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.25rem;
}

.hub-section-tag {
  font-family: var(--mono);
  font-size: 0.62rem;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  border: 1px solid;
  border-radius: 2px;
  padding: 0.2em 0.6em;
  white-space: nowrap;
}

.hub-section-rule {
  flex: 1;
  height: 1px;
  background: var(--border);
}

/* ── Project grid ────────────────────────── */
.hub-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1px;
  background: var(--border);
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
}

.hub-card {
  background: var(--surface);
  padding: 1.4rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  transition: background 0.15s;
  position: relative;
}

.hub-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, var(--teal) 0%, transparent 60%);
  opacity: 0;
  transition: opacity 0.2s;
  pointer-events: none;
}

.hub-card:hover { background: var(--surface-2); }
.hub-card:hover::before { opacity: 0.03; }

.hub-card--primary {
  border-left: 2px solid var(--teal);
}

.hub-card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
}

.hub-card-name {
  font-family: var(--mono);
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--text-1);
  letter-spacing: -0.01em;
}

.hub-card-tagline {
  font-size: 0.78rem;
  color: var(--teal);
  font-weight: 500;
  letter-spacing: 0.01em;
}

.hub-card-desc {
  font-size: 0.82rem;
  color: var(--text-2);
  line-height: 1.6;
  margin: 0;
  flex: 1;
}

/* ── Status dot ──────────────────────────── */
.hub-status {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-family: var(--mono);
  font-size: 0.62rem;
  flex-shrink: 0;
}

.hub-status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-3);
}

.hub-status--up .hub-status-dot {
  background: #4ade80;
  box-shadow: 0 0 6px #4ade8066;
  animation: pulse 2s ease-in-out infinite;
}
.hub-status--down .hub-status-dot { background: #f87171; }
.hub-status--checking .hub-status-dot { background: #fbbf24; animation: blink 1s step-end infinite; }

.hub-status--up .hub-status-label { color: #4ade80; }
.hub-status--down .hub-status-label { color: #f87171; }
.hub-status--checking .hub-status-label { color: #fbbf24; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* ── Stack badges ────────────────────────── */
.hub-stack {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-top: 0.25rem;
}

.hub-badge {
  font-family: var(--mono);
  font-size: 0.6rem;
  letter-spacing: 0.05em;
  padding: 0.18em 0.55em;
  border-radius: 2px;
  border: 1px solid color-mix(in srgb, var(--badge-color) 40%, transparent);
  color: color-mix(in srgb, var(--badge-color) 90%, white);
  background: color-mix(in srgb, var(--badge-color) 8%, transparent);
}

/* ── Card links ──────────────────────────── */
.hub-card-links {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.hub-link {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-family: var(--mono);
  font-size: 0.68rem;
  text-decoration: none;
  padding: 0.3em 0.75em;
  border-radius: 3px;
  transition: all 0.15s;
}

.hub-link--primary {
  background: color-mix(in srgb, var(--teal) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--teal) 35%, transparent);
  color: var(--teal);
}
.hub-link--primary:hover {
  background: color-mix(in srgb, var(--teal) 20%, transparent);
  border-color: var(--teal);
}

.hub-link--ghost {
  border: 1px solid var(--border-bright);
  color: var(--text-2);
}
.hub-link--ghost:hover {
  border-color: var(--text-3);
  color: var(--text-1);
}

/* ── Port table ──────────────────────────── */
.hub-ports {
  margin-top: 3rem;
}

.hub-ports-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.hub-ports-grid {
  font-family: var(--mono);
  font-size: 0.75rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
}

.hub-port-row {
  display: grid;
  grid-template-columns: 5rem 1fr auto auto;
  align-items: center;
  gap: 1rem;
  padding: 0.65rem 1.25rem;
  border-bottom: 1px solid var(--border);
  transition: background 0.1s;
}
.hub-port-row:last-child { border-bottom: none; }
.hub-port-row:hover { background: var(--surface-2); }

.hub-port-num {
  color: var(--teal);
  font-weight: 700;
}

.hub-port-name { color: var(--text-1); }

.hub-port-status { font-size: 0.65rem; }
.hub-port-status--up { color: #4ade80; }
.hub-port-status--down { color: #f87171; }
.hub-port-status--checking { color: #fbbf24; }

.hub-port-link {
  color: var(--text-3);
  text-decoration: none;
  font-size: 0.68rem;
  transition: color 0.15s;
}
.hub-port-link:hover { color: var(--teal); }

/* ── Dark mode overrides (VitePress uses .dark class on html) ── */
:global(.dark) .hub {
  color: var(--text-1);
}
</style>
