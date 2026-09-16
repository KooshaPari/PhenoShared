# Phenotype Glass Recipe

Per-OS glassmorphism specification for `@phenotype/design`.
This document feeds the platform-icon-materials work and any
agent that needs to apply glass to app surfaces.

---

## Palette baseline

All glass recipes sit on the Keycap palette:

| Token           | Dark          | Light         |
|-----------------|---------------|---------------|
| `--kc-bg`       | `#090a0c`     | `#f8f9fa`     |
| `--kc-accent`   | `#7ebab5`     | `#7ebab5`     |
| `--kc-divider`  | `#1f2329`     | `#d4d7dc`     |
| accent tint     | `rgba(126,186,181, 0.06)` | — |

---

## Recipe 1 — Android Neo-Glass

**Target:** Material You frosted panels, cards, bottom sheets.

### Layer stack (top → bottom)

1. **Content** — text / icons at full opacity
2. **Specular ring** — `box-shadow: inset 0 0 0 0.5px rgba(255,255,255,0.30)` light / `0.06` dark
3. **Border** — `1px solid rgba(255,255,255,0.45)` light / `0.08` dark
4. **Fill** — `background: rgba(248,249,250, 0.72)` light / `rgba(9,10,12, 0.72)` dark
5. **Blur** — `backdrop-filter: blur(16px) saturate(1.1)`
6. **Depth shadow** — `box-shadow: 0 2px 8px rgba(0,0,0,0.08)` light / `0 4px 16px rgba(0,0,0,0.40)` dark

### Parameters

| Property        | Value           |
|-----------------|-----------------|
| Blur radius     | **16 px**       |
| Saturation      | **1.1**         |
| Fill opacity    | **0.72** (both) |
| Border opacity  | 0.45 light / 0.08 dark |
| Specular inset  | 0.30 light / 0.06 dark |
| Border radius   | **16 px**       |

### CSS class

```css
.glass-neo { /* see glass.css */ }
```

---

## Recipe 2 — macOS Liquid Glass

**Target:** macOS nav bars, visionOS panels, floating popovers.

### Layer stack (top → bottom)

1. **Content**
2. **Top-edge specular gradient** — `linear-gradient(180deg, rgba(255,255,255,0.70) 0%, transparent 8%)` light / `rgba(255,255,255,0.12)` dark
3. **Inner top highlight** — `box-shadow: inset 0 1px 0 rgba(255,255,255,0.80)` light / `0.10` dark
4. **Inner bottom shadow** — `box-shadow: inset 0 -1px 0 rgba(0,0,0,0.05)` light / `0.30` dark
5. **Border** — `1px solid rgba(255,255,255,0.55)` top/sides; `rgba(255,255,255,0.25)` bottom light; `0.10`/`0.04` dark
6. **Fill** — `rgba(255,255,255, 0.60)` light / `rgba(20,23,27, 0.60)` dark + teal accent tint `rgba(126,186,181,0.06)` dark only
7. **Blur** — `backdrop-filter: blur(20px) saturate(1.4)`
8. **Depth shadow** — `0 8px 32px rgba(0,0,0,0.10)` light / `0.60` dark

### Parameters

| Property           | Value            |
|--------------------|------------------|
| Blur radius        | **20 px**        |
| Saturation         | **1.4**          |
| Fill opacity       | **0.60** (both)  |
| Top border opacity | 0.55 light / 0.10 dark |
| Bottom border opacity | 0.25 light / 0.04 dark |
| Inner highlight    | 0.80 light / 0.10 dark |
| Inner shadow       | 0.05 light / 0.30 dark |
| Specular gradient  | 0→8% of height    |
| Border radius      | **14 px**        |
| Tint               | accent 0.06 (dark only) |

### CSS class

```css
.glass-liquid { /* see glass.css */ }
```

---

## Recipe 3 — Windows Mica

**Target:** Windows 11 Mica/Acrylic — app sidebars, titlebar-adjacent
surfaces, settings pages.

> Note: True Mica requires the `DwmSetWindowAttribute` OS API.
> This CSS approximation uses heavy blur + high fill opacity to
> simulate the system-color tint effect.

### Layer stack (top → bottom)

1. **Content**
2. **Accent tint** — `rgba(126,186,181,0.06)` dark only (no tint light)
3. **Fill** — `rgba(248,249,250, 0.82)` light / `rgba(9,10,12, 0.85)` dark
4. **Blur** — `backdrop-filter: blur(40px) saturate(1.8)`
5. **Border** — `1px solid var(--kc-divider)` (system chrome divider, not white)
6. **Shadow** — `0 1px 3px rgba(0,0,0,0.06)` light / `0 2px 8px rgba(0,0,0,0.50)` dark

### Parameters

| Property        | Value          |
|-----------------|----------------|
| Blur radius     | **40 px**      |
| Saturation      | **1.8**        |
| Fill opacity    | 0.82 light / **0.85** dark |
| Border          | `--kc-divider` (not white specular) |
| Border radius   | **8 px** (flat Windows aesthetic) |
| Tint opacity    | 0.06 (dark only) |

### CSS class

```css
.glass-mica { /* see glass.css */ }
```

---

## Utility recipes

### Frosted nav bar

Used in the Phenotype design showcase's sticky topbar:

```css
backdrop-filter: blur(14px) saturate(1.2);
background: color-mix(in oklab, var(--kc-bg) 88%, transparent);
border-bottom: 1px solid var(--kc-divider);
```

Class: `.glass-nav`

### Swatch badge overlay

Small frosted label over colored swatches:

```css
backdrop-filter: blur(4px);
background: rgba(9,10,12, 0.50);  /* dark */
background: rgba(255,255,255, 0.70);  /* light */
```

Class: `.glass-badge`

---

## Quick comparison table

| Recipe    | Blur  | Saturate | Fill opacity | Specular   | Radius | Platform        |
|-----------|-------|----------|--------------|------------|--------|-----------------|
| neo-glass | 16 px | 1.1      | 72%          | inset ring | 16 px  | Android / cross |
| liquid    | 20 px | 1.4      | 60%          | top gradient | 14 px | macOS / visionOS |
| mica      | 40 px | 1.8      | 82–85%       | none (flat)  | 8 px  | Windows 11      |
| nav       | 14 px | 1.2      | 88%          | none         | —     | Any (nav bars)  |
| badge     |  4 px | —        | 50–70%       | none         | 4 px  | Any             |

---

## Icon agent usage

When generating platform-specific app icons apply the glass material
as the **background layer** of the icon's keycap shape:

- **Android adaptive icon** background layer: use neo-glass values (blur 16, opacity 0.72, border radius 16 px at the icon canvas scale).
- **macOS .icns**: use liquid glass values (blur 20, specular gradient, border radius 14 px scaled to icon canvas).
- **Windows .ico**: use mica values (blur 40, flat border, 8 px corner, high opacity).

All three use `--kc-accent` (`#7ebab5`) as the logo/mark color, `#090a0c` for letter/glyph on teal fill.
