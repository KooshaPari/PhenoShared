# Cards & Pipeline

## Doc Type Cards

Grid layout for document type galleries.

<div class="doc-type-grid">
  <div class="doc-type-card">
    <div class="card-title">Specification</div>
    <div class="card-desc">Feature specs with requirements, scenarios,
      and success criteria.</div>
  </div>
  <div class="doc-type-card">
    <div class="card-title">Architecture Decision</div>
    <div class="card-desc">ADRs capturing technical decisions with context and rationale.</div>
  </div>
  <div class="doc-type-card">
    <div class="card-title">Retrospective</div>
    <div class="card-desc">Post-feature reflections on process, metrics, and improvements.</div>
  </div>
</div>

```html
<div class="doc-type-grid">
  <div class="doc-type-card">
    <div class="card-title">Title</div>
    <div class="card-desc">Description text.</div>
  </div>
</div>
```

## Pipeline Visualization

Horizontal flow for workflow stages.

<div class="pipeline">
  <span class="stage">specify</span>
  <span class="arrow">→</span>
  <span class="stage">plan</span>
  <span class="arrow">→</span>
  <span class="stage">implement</span>
  <span class="arrow">→</span>
  <span class="stage">ship</span>
</div>

```html
<div class="pipeline">
  <span class="stage">specify</span>
  <span class="arrow">→</span>
  <span class="stage">plan</span>
  <span class="arrow">→</span>
  <span class="stage">ship</span>
</div>
```

Stages highlight on hover with the accent teal.
