# TheGent Landing Site Library

Path utilities and site configuration for thegent-landing Astro project.

## Installation

This library is part of the `thegent-landing` package and requires no separate installation.

## Usage

```typescript
import { BASE_PATH, sitePath, getFullPath, createSitePath, SITE_CONFIG } from './lib';

// Get site configuration
console.log(SITE_CONFIG.name); // 'thegent'

// Build absolute paths
const docsPath = sitePath('/docs'); // '/thegent/docs'

// Create a reusable path builder
const getPath = createSitePath();
getPath('/about'); // '/thegent/about'

// Get full path for a route
const fullPath = getFullPath('/pricing'); // '/thegent/pricing'

// Base path constant
console.log(BASE_PATH); // '/thegent'
```

## API Reference

### Constants

#### `SITE_CONFIG`
Site configuration object with the following properties:
- `name`: Site identifier ('thegent')
- `displayName`: Human-readable name ('TheGent')
- `description`: Site description
- `primaryColor`: Primary brand color
- `accentColor`: Accent brand color
- `baseUrl`: Base URL path

#### `BASE_PATH`
Base path for all site routes, derived from `SITE_CONFIG.baseUrl`.

### Functions

#### `sitePath(path: string): string`
Constructs an absolute site path by prepending the base URL.

#### `createSitePath(): (path: string) => string`
Creates a reusable site path function configured with site-specific settings.

#### `getFullPath(route: string): string`
Returns the full absolute path for a given route.

### Types

- `SiteConfig`: Type for the SITE_CONFIG object
- `SitePathFunction`: Type for the sitePath function
