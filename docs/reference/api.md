# API Reference

 programmatic access to PhenoDocs functionality

## Python API

### HubGenerator

Main class for generating federation hubs.

```python
from docs_engine.hub.generator import HubGenerator
from pathlib import Path
```

#### Constructor

```python
HubGenerator(hub_dir: Path, projects: dict[str, str]) -> HubGenerator
```

**Parameters:**

- `hub_dir` — Output directory for the hub
- `projects` — Dict mapping project names to doc paths

**Example:**

```python
gen = HubGenerator(
    hub_dir=Path("./phenodocs"),
    projects={
        "thegent": "/workspace/thegent/docs",
        "pheno-sdk": "/workspace/pheno-sdk/docs"
    }
)
```

#### Methods

##### generate()

```python
def generate(self) -> None
```

Write hub files. Idempotent — safe to call multiple times.

**Creates:**

- `index.md` — Landing page
- `.vitepress/config.ts` — VitePress config
- `package.json` — Dependencies

**Example:**

```python
gen.generate()
print("Hub generated successfully!")
```

### CLI Commands

#### docs hub

```bash
docs hub [OPTIONS]
```

**Options:**

- `--hub-dir PATH` — Hub output directory (default: "../docs-hub")

**Example:**

```bash
docs hub --hub-dir ./phenodocs
```

## MCP Tools

### thegent_doc_hub_generate

Generate or regenerate the VitePress federation hub.

```json
{
  "name": "thegent_doc_hub_generate",
  "arguments": {
    "hub_dir": "../phenodocs"
  }
}
```

## Configuration Files

### package.json

```json
{
  "name": "phenodocs",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "vitepress dev",
    "build": "vitepress build",
    "preview": "vitepress preview"
  },
  "devDependencies": {
    "vitepress": "^1.0.0"
  }
}
```

### .vitepress/config.ts

```typescript
import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'PhenoDocs',
  description: 'Federation hub for all project documentation',
  themeConfig: {
    nav: [
      { text: 'Lab', link: '/lab/' },
      { text: 'Docs', link: '/docs/' },
      { text: 'Audit', link: '/audit/' },
      { text: 'KB', link: '/kb/' }
    ]
  }
})
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DOCS_HUB_DIR` | Output directory | `../docs-hub` |
| `VITEPRESS_PORT` | Dev server port | `5173` |
| `VITEPRESS_HOST` | Dev server host | `localhost` |

## Return Values

### generate() Return Value

Returns `None`. Files are written directly to `hub_dir`.

Check for success:

```python
import os

gen.generate()
index_path = hub_dir / "index.md"
if index_path.exists():
    print("Success!")
```

## Error Handling

```python
from docs_engine.hub.generator import HubGenerator
from pathlib import Path

try:
    gen = HubGenerator(
        hub_dir=Path("./phenodocs"),
        projects={"test": "/nonexistent/path"}
    )
    gen.generate()
except FileNotFoundError as e:
    print(f"Project path not found: {e}")
except PermissionError as e:
    print(f"Permission denied: {e}")
```

## TypeScript API

### generateHubConfig()

```typescript
import { defineConfig } from 'vitepress'

interface Project {
  name: string
  path: string
}

export function generateHubConfig(projects: Project[]) {
  return defineConfig({
    title: 'PhenoDocs',
    themeConfig: {
      nav: projects.map(p => ({
        text: p.name,
        link: `${p.path}/`
      }))
    }
  })
}
```

## Webhooks

### Hub Update Webhook

Trigger hub regeneration on doc changes:

```yaml
# .github/workflows/hub-update.yml
on:
  push:
    paths:
      - 'docs/**'
      - '!docs/**/*.md'  # exclude docs themselves
jobs:
  update-hub:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Generate Hub
        run: docs hub --hub-dir ./phenodocs
      - name: Commit changes
        run: |
          git config --local user.email "bot@phenodocs.io"
          git config --local user.name "PhenoDocs Bot"
          git add .
          git commit -m "Update hub" || exit 0
```

## Rate Limits

No rate limits for local generation. For CI/CD:

- Debounce: Wait 30s after last commit
- Cooldown: Max 1 generation per 5 minutes
