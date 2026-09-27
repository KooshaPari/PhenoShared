# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for PhenoDocs following the [MADR](https://adr.github.io/madr/) format.

---

# ADR-001: Build-Time Federation Over Runtime Federation

## Status

- **Status**: Accepted
- **Date**: 2026-04-04
- **Deciders**: PhenoDocs Core Team

## Context and Problem Statement

PhenoDocs must aggregate documentation from multiple Phenotype repositories into a unified hub. The federation approach significantly impacts:

1. **Search Quality**: Can users search across all documentation?
2. **SEO**: Are pages discoverable via search engines?
3. **Build Complexity**: How complex is the CI/CD pipeline?
4. **Update Latency**: How quickly do changes propagate?
5. **Offline Capability**: Does the documentation work without network?

The core question: Should we federate at build-time (static aggregation) or runtime (client-side composition)?

## Decision Drivers

- Must support 10+ source repositories
- Must provide unified full-text search
- Must work on GitHub Pages (no server-side logic)
- Must maintain SEO for all content
- Must support fast iteration (changes visible quickly)

## Considered Options

### Option 1: Build-Time Federation (Selected)

Aggregate all documentation during the build process, producing a single static site.

**Implementation**:
```
Source Repos → HubGenerator → VitePress Build → Static Site
```

### Option 2: Runtime Federation via Module Federation

Load documentation modules at runtime using webpack Module Federation or similar.

**Implementation**:
```
Shell App ──► Lazy loads ──► Remote Documentation Modules
```

### Option 3: Client-Side Proxy Pattern

Iframe-based or fetch-based composition in the browser.

**Implementation**:
```
Hub Frame ──► Fetches ──► Individual Doc Sites
```

## Decision Outcome

**Chosen option**: Option 1 — Build-Time Federation

Build-time federation provides the best balance of search quality, SEO, and simplicity for our constraints (GitHub Pages hosting, no server).

### Positive Consequences

- **Unified Search**: Single Lunr/MiniSearch index across all content
- **SEO Optimal**: All content in static HTML, discoverable by search engines
- **No Runtime Dependencies**: Works offline, no CORS complexity
- **Consistent UX**: Single VitePress theme across all content
- **Predictable URLs**: Clean, persistent URLs for all pages

### Negative Consequences

- **Source Dependency**: Build fails if source repos are unavailable
- **Update Latency**: Changes require hub rebuild (mitigated by automation)
- **Build Time**: Increases with number of source repos
- **Repository Access**: Requires checkout access to private repos

## Pros and Cons of the Options

### Option 1: Build-Time Federation

**Pros**:
- Best SEO (all content pre-rendered)
- Unified search index
- No runtime complexity
- Works offline
- Single consistent theme

**Cons**:
- Requires source availability at build time
- Longer build times
- More complex CI/CD

### Option 2: Runtime Federation

**Pros**:
- Independent deployments
- Faster hub builds
- Source availability not required at build

**Cons**:
- Search fragmentation (requires federated search solution)
- SEO challenges (dynamic content less discoverable)
- Complex runtime orchestration
- CORS and authentication complexity
- Inconsistent UX across modules

**Verdict**: Rejected due to SEO and search fragmentation concerns.

### Option 3: Client-Side Proxy

**Pros**:
- Simplest implementation
- Source sites remain independent

**Cons**:
- Poor SEO (iframes/fetched content not indexed)
- No unified search
- jarring UX (iframes)
- CORS limitations
- Broken navigation patterns

**Verdict**: Rejected due to SEO and UX concerns.

## Implementation Details

### HubGenerator Architecture

```typescript
// packages/docs/src/utils/hub-generator.ts
interface HubGeneratorConfig {
  hubDir: string;           // Target directory
  projects: ProjectMap;     // Source repository mapping
  layers: LayerConfig[];    // Content layer configuration
}

interface ProjectMap {
  [projectId: string]: string;  // projectId -> source path
}

generate(): void {
  // 1. Clean target directories
  // 2. Copy content from each project
  // 3. Transform frontmatter (add project attribution)
  // 4. Generate index files
  // 5. Update VitePress config
}
```

### Frontmatter Transformation

Source frontmatter is enriched with federation metadata:

```yaml
# Source (in project repo)
---
title: API Reference
---

# Transformed (in hub)
---
title: API Reference
project: pheno-sdk
source_repo: github.com/phenotype/pheno-sdk
source_path: docs/reference/api.md
federated: true
---
```

### CI Integration

```yaml
# .github/workflows/federate.yml
on:
  schedule:
    - cron: '0 */4 * * *'  # Every 4 hours
  workflow_dispatch:

jobs:
  federate:
    steps:
      - name: Fetch Sources
        run: |
          docs hub --hub-dir .
      - name: Build
        run: bun run build
      - name: Deploy
        run: bun run deploy
```

## Related Decisions

- ADR-002: HubGenerator CLI Tool
- ADR-006: Layered Content Architecture

## References

- [Module Federation](https://module-federation.io/): Runtime federation pattern
- [Docusaurus Multi-instance](https://docusaurus.io/docs/docs-multi-instance): Build-time federation in Docusaurus
- [Vercel Turborepo Remote Caching](https://turbo.build/repo/docs/core-concepts/remote-caching): Related build optimization

---

# ADR-002: HubGenerator CLI Tool Architecture

## Status

- **Status**: Accepted
- **Date**: 2026-04-04
- **Deciders**: PhenoDocs Core Team

## Context and Problem Statement

Following the decision to use build-time federation (ADR-001), we need a robust mechanism to:

1. Aggregate content from multiple source repositories
2. Maintain directory structure and metadata
3. Generate navigation indices
4. Integrate with CI/CD pipelines

The question: Should we implement this as a standalone CLI tool, a library, or a collection of scripts?

## Decision Drivers

- Must integrate with Python-based docs_engine ecosystem
- Must support both CLI and programmatic usage
- Must handle 10+ repositories efficiently
- Must provide clear error messages and logging
- Must support incremental updates

## Considered Options

### Option 1: Python CLI Tool with TypeScript Bindings (Selected)

Primary implementation in Python (matching docs_engine), with TypeScript types for VitePress integration.

### Option 2: Pure TypeScript Tool

Implement entirely in TypeScript as part of @phenotype/docs package.

### Option 3: Hybrid Scripts (Shell + Python + Node)

Collection of scripts in different languages coordinated via shell.

## Decision Outcome

**Chosen option**: Option 1 — Python CLI Tool with TypeScript Bindings

Primary Python implementation maintains ecosystem consistency while TypeScript types enable type-safe VitePress integration.

### Positive Consequences

- **Ecosystem Alignment**: Consistent with docs_engine (Python)
- **MCP Integration**: Can expose as MCP tool for agent usage
- **Type Safety**: TypeScript types for config validation
- **Performance**: Python's file operations are fast enough for this use case
- **Testability**: Python's testing ecosystem well-understood

### Negative Consequences

- **Two Languages**: Requires maintenance of Python core + TypeScript types
- **Dependency Surface**: Both Python and Node environments required

## Pros and Cons of the Options

### Option 1: Python CLI with TypeScript Bindings

**Pros**:
- Ecosystem consistency with docs_engine
- Can expose as MCP tool
- Fast development velocity
- Good testing support

**Cons**:
- Multi-language maintenance
- Two runtime dependencies

### Option 2: Pure TypeScript

**Pros**:
- Single language/stack
- Direct VitePress integration
- Can use Bun for performance

**Cons**:
- Divergence from docs_engine ecosystem
- Harder to share logic with Python-based tooling
- Less suitable for MCP tool exposure

**Verdict**: Rejected to maintain ecosystem consistency.

### Option 3: Hybrid Scripts

**Pros**:
- Use best tool for each subtask

**Cons**:
- High complexity
- Hard to test
- Hard to debug
- Inconsistent interfaces

**Verdict**: Rejected due to complexity and maintenance burden.

## Implementation Details

### Command Structure

```bash
docs hub [OPTIONS]

Options:
  --hub-dir PATH       Target directory for hub (default: .)
  --config PATH        Path to hub configuration file
  --projects JSON      JSON map of projects
  --dry-run            Show what would be done without doing it
  --verbose            Enable detailed logging
  --incremental        Only update changed files
```

### Configuration Schema

```python
# Python (runtime)
@dataclass
class HubConfig:
    hub_dir: Path
    projects: dict[str, Path]
    layers: list[LayerConfig]
    transforms: list[TransformConfig]
```

```typescript
// TypeScript (type definitions)
interface HubConfig {
  hubDir: string;
  projects: Record<string, string>;
  layers: LayerConfig[];
  transforms: TransformConfig[];
}
```

### Algorithm

```python
def generate_hub(config: HubConfig) -> None:
    # Phase 1: Discovery
    sources = discover_sources(config.projects)
    
    # Phase 2: Validation
    validate_sources(sources)
    
    # Phase 3: Transformation
    for source in sources:
        transform = apply_transforms(source, config.transforms)
        enriched = enrich_frontmatter(transform, source.project)
        write_to_hub(enriched, config.hub_dir)
    
    # Phase 4: Index Generation
    generate_indices(config.hub_dir)
    
    # Phase 5: VitePress Config Update
    update_vitepress_config(config)
```

### Error Handling

```python
class HubError(Exception):
    """Base exception for hub generation errors."""
    pass

class SourceNotFoundError(HubError):
    """Raised when a source repository is not found."""
    pass

class TransformError(HubError):
    """Raised when a content transformation fails."""
    pass
```

## Related Decisions

- ADR-001: Build-Time Federation
- ADR-003: Layered Content Architecture

## References

- [docs_engine](https://github.com/phenotype/docs_engine): Related Python package
- [Pydantic](https://docs.pydantic.dev/): Configuration validation
- [Typer](https://typer.tiangolo.com/): CLI framework

---

# ADR-003: AI-Context Generation (.llms.txt)

## Status

- **Status**: Accepted
- **Date**: 2026-04-04
- **Deciders**: PhenoDocs Core Team

## Context and Problem Statement

Large Language Models (LLMs) increasingly assist developers. For LLMs to provide accurate, context-aware assistance, they need:

1. **Concise Context**: Relevant documentation without noise
2. **Priority Signaling**: Clear indication of what content is critical vs. optional
3. **Discoverability**: Standard location for LLM context

The `.llms.txt` convention (proposed by Anthropic, adopted by Vercel, Stripe) addresses this by providing a structured, token-efficient documentation extract at a well-known location.

The question: Should PhenoDocs implement `.llms.txt` generation, and if so, how should it be structured?

## Decision Drivers

- Must support AI-assisted development workflows
- Must minimize token usage (cost and context window constraints)
- Must be automatic (not manual maintenance burden)
- Must be accurate (reflect actual documentation content)
- Must be discoverable (standard location and format)

## Considered Options

### Option 1: Full .llms.txt Implementation (Selected)

Implement comprehensive `.llms.txt` generation with priority sections, summaries, and cross-references.

### Option 2: Minimal .llms.txt

Generate only a basic index with links, no summaries or prioritization.

### Option 3: No .llms.txt

Rely on LLMs to scrape the full documentation site.

## Decision Outcome

**Chosen option**: Option 1 — Full .llms.txt Implementation

Comprehensive implementation provides maximum value for AI-assisted workflows while maintaining automatic generation.

### Positive Consequences

- **Token Efficiency**: 90%+ reduction vs. full site scraping
- **Priority Awareness**: Critical content clearly marked
- **Accuracy**: Always in sync with actual documentation
- **Standard Compliant**: Works with Anthropic, Vercel, and other tools
- **Discoverability**: Well-known location (`/.llms.txt`)

### Negative Consequences

- **Generation Complexity**: Requires content analysis and summarization
- **Build Time**: Additional step in build pipeline
- **Validation Needed**: Must verify generated content is coherent

## Pros and Cons of the Options

### Option 1: Full Implementation

**Pros**:
- Maximum value for AI workflows
- Token-efficient
- Automatic generation
- Standard compliant

**Cons**:
- More complex to implement
- Additional build step

### Option 2: Minimal Implementation

**Pros**:
- Simple to implement
- Follows convention

**Cons**:
- Limited value (just a link list)
- No priority signaling
- May not fit in context window for large sites

**Verdict**: Rejected — insufficient value for the effort.

### Option 3: No Implementation

**Pros**:
- No implementation effort

**Cons**:
- LLMs scrape full site (high token cost, may exceed context window)
- No priority signaling
- Poor accuracy (LLM may miss critical content)

**Verdict**: Rejected — misses opportunity to optimize AI workflows.

## Implementation Details

### File Structure

```
.llms.txt              # Main entry point
.llms/                 # Extracts directory
  ├── getting-started.md
  ├── architecture.md
  ├── api-reference.md
  └── ...
```

### Generation Algorithm

```python
def generate_llms_txt(config: HubConfig) -> None:
    # Phase 1: Content Analysis
    pages = analyze_content(config.hub_dir)
    
    # Phase 2: Priority Classification
    critical = filter_by_priority(pages, 'critical')
    high = filter_by_priority(pages, 'high')
    medium = filter_by_priority(pages, 'medium')
    
    # Phase 3: Summarization
    for page in critical + high:
        page.summary = generate_summary(page.content)
    
    # Phase 4: Generate .llms.txt
    write_llms_txt(critical, high, medium)
    
    # Phase 5: Generate Extracts
    for page in critical + high:
        write_extract(page)
```

### Format

```markdown
# PhenoDocs

> Federated documentation hub for the Phenotype ecosystem

## Docs

Critical documentation for understanding and using PhenoDocs:

- [Getting Started](https://kooshapari.com/docs/getting-started): Installation, quick start, and basic concepts
- [Architecture](https://kooshapari.com/docs/architecture): System design, federation model, and content layers
- [Hub Generator](https://kooshapari.com/docs/hub-generator): CLI tool for documentation aggregation

## Optional

Additional reference material:

- [API Reference](https://kooshapari.com/reference/api): Complete API documentation
- [ADRs](https://kooshapari.com/planning/adrs): Architecture decision records
- [Changelog](https://kooshapari.com/audit/changelog): Version history and migration guides

## MCP Tools

Available Model Context Protocol tools:

- `phenodocs_search`: Search documentation across all projects
- `phenodocs_hub_generate`: Generate federated documentation hub
```

### Frontmatter Integration

```yaml
---
title: API Reference
llms_extract: true
llms_priority: high
llms_summary: |
  Complete API reference for the HubGenerator class,
  including all public methods, configuration options,
  and usage examples.
---
```

### Build Integration

```typescript
// .vitepress/config.ts
export default defineConfig({
  buildEnd: async (siteConfig) => {
    await generateLlmsTxt(siteConfig.outDir);
  }
});
```

## Related Decisions

- ADR-001: Build-Time Federation
- SOTA.md: AI-Augmented Documentation section

## References

- [Anthropic .llms.txt Proposal](https://www.anthropic.com/): Origin of the convention
- [Vercel .llms.txt](https://vercel.com/docs/llms.txt): Production implementation
- [Stripe .llms.txt](https://stripe.com/docs/llms.txt): Enterprise implementation
- [Model Context Protocol](https://modelcontextprotocol.io/): Tool exposure standard

---

# ADR Index

| ID | Title | Status | Date |
|----|-------|--------|------|
| 001 | Build-Time Federation | Accepted | 2026-04-04 |
| 002 | HubGenerator CLI Tool | Accepted | 2026-04-04 |
| 003 | AI-Context Generation | Accepted | 2026-04-04 |

---

**Directory Status**: Layer 2 (Docs) — Active  
**Review Cycle**: Monthly  
**Next Review**: 2026-05-04
