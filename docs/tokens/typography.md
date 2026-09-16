# Typography

## Font Families

| Token | Value | Usage |
|-------|-------|-------|
| `--kc-font-base` | Inter, system stack | Body text, headings, UI |
| `--kc-font-mono` | JetBrains Mono | Code blocks, CLI output |

## Font Loading

The palette CSS imports fonts from Google Fonts:

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
```

For self-hosting, download the fonts and replace the `@import` with
local `@font-face` declarations.

## Heading Styles

| Level | Weight | Letter Spacing |
|-------|--------|---------------|
| h1 | 700 (bold) | -0.03em |
| h2 | 600 (semibold) | -0.02em |
| h3 | 600 (semibold) | -0.01em |
| Body | 400 (regular) | normal |

## Line Height

Body text uses `1.75` line height for readability in documentation contexts.

## Code

Code blocks use `13px` font size with the mono stack. Inline code
uses the `--kc-code-bg` background.
