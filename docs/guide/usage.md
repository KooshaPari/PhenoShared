# Usage Patterns

## CSS Custom Properties

The palette exposes `--kc-*` tokens:

```css
.my-element {
  background: var(--kc-bg-soft);
  color: var(--kc-text-1);
  border: 1px solid var(--kc-divider);
}

.my-link {
  color: var(--kc-accent);
}

.my-link:hover {
  color: var(--kc-accent-hover);
}
```

These automatically switch between light and dark values based on the
`.dark` class or `prefers-color-scheme`.

## TypeScript Tokens

```typescript
import { keycap } from '@phenotype/design'

// Use in JS-driven styling (CSS-in-JS, inline styles, etc.)
const styles = {
  backgroundColor: keycap.dark.bg,
  color: keycap.dark.text1,
  borderColor: keycap.accent,
}
```

## VitePress Config Helper

```typescript
import { vitepressConfig } from '@phenotype/design/vitepress'

export default defineConfig({
  ...vitepressConfig, // appearance: 'dark', markdown theme
  title: 'My Project',
})
```

## Light vs Dark Accent

The accent teal `#7ebab5` works on dark backgrounds but lacks contrast
on light. Use the contrast variant:

| Context | Color | Token |
|---------|-------|-------|
| Dark background | `#7ebab5` | `--kc-accent` |
| Light background | `#4a9c97` | `--kc-accent-contrast` |
| Hover (dark) | `#95ccc8` | `--kc-accent-hover` |
| Button text on accent BG | `#090a0c` | `--kc-bg` (dark mode) |
| Button text on accent BG | `#ffffff` | white (light mode) |
