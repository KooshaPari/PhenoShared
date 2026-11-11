# Accessibility — sl-viewer WCAG AA Compliance

This document tracks `sl-viewer` (the desktop session viewer built with Dioxus) against the [WCAG 2.1 Level AA](https://www.w3.org/TR/WCAG21/) success criteria relevant to a native desktop application.

## Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Pass — implemented and verified |
| 🚧 | In progress / partial |
| ⬜ | Not yet addressed |
| N/A | Not applicable to this UI |

---

## 1 — Perceivable

### 1.1 Text Alternatives

| SC | Criterion | Status | Notes |
|----|-----------|--------|-------|
| 1.1.1 | Non-text Content | ✅ | All images and icons include `alt` text or `aria-label` attributes via the Dioxus accessibility tree. Decorative icons are marked with `aria-hidden="true"`. |

### 1.2 Time-based Media

| SC | Criterion | Status | Notes |
|----|-----------|--------|-------|
| 1.2.1 | Audio-only / Video-only | N/A | sl-viewer does not present audio or video content. |

### 1.3 Adaptable

| SC | Criterion | Status | Notes |
|----|-----------|--------|-------|
| 1.3.1 | Info and Relationships | ✅ | Semantic roles (`role="tablist"`, `role="tab"`, `role="tabpanel"`, `role="tree"`, `role="treeitem"`) are set on all structural elements. |
| 1.3.2 | Meaningful Sequence | ✅ | DOM order matches visual reading order; tab order follows logical flow. |
| 1.3.3 | Sensory Characteristics | ✅ | No instruction relies solely on color, shape, or location. Session status is communicated via text labels in addition to color. |
| 1.3.4 | Orientation | N/A | Desktop application; orientation lock not applicable. |
| 1.3.5 | Identify Input Purpose | ✅ | Search input uses `aria-label="Search sessions and bundles"`. Locale-aware placeholder text from i18n strings. |

### 1.4 Distinguishable

| SC | Criterion | Status | Notes |
|----|-----------|--------|-------|
| 1.4.1 | Use of Color | ✅ | Status indicators use icons + text, not color alone. Error states include ⚠ icon and text. |
| 1.4.2 | Audio Control | N/A | No audio playback. |
| 1.4.3 | Contrast (Minimum) | ✅ | All text passes 4.5:1 contrast (normal text) and 3:1 (large text) against backgrounds. Design tokens defined in `docs/a11y/design-tokens.md`. |
| 1.4.4 | Resize Text | ✅ | Viewer respects OS font-size preferences. Bundle list and session tree scale with system text size. |
| 1.4.5 | Images of Text | ✅ | No images of text are used. All text is rendered as live text. |
| 1.4.10 | Reflow | N/A | Desktop application; window resizes without horizontal scroll. |
| 1.4.11 | Non-text Contrast | ✅ | Interactive element borders and focus indicators meet 3:1 contrast ratio. |
| 1.4.12 | Text Spacing | ✅ | Layout tolerates increased line-height, letter-spacing, and paragraph spacing without loss of content. |
| 1.4.13 | Content on Hover or Focus | ✅ | Tooltips on session items can be dismissed (Esc) and are hover-persistent. |

---

## 2 — Operable

### 2.1 Keyboard Accessible

| SC | Criterion | Status | Notes |
|----|-----------|--------|-------|
| 2.1.1 | Keyboard | ✅ | All functionality accessible via keyboard. Shortcut reference at `docs/viewer-hotkeys.md`. |
| 2.1.2 | No Keyboard Trap | ✅ | Focus can be moved away from any component using standard Tab / Shift+Tab / Escape. Overlay dialogs trap focus intentionally and provide a close mechanism (see `docs/a11y/overlay-escape.md`). |
| 2.1.4 | Character Key Shortcuts | ✅ | All keyboard shortcuts use modifier keys (Ctrl/Cmd) or are remappable via the shortcuts palette. |

### 2.2 Enough Time

| SC | Criterion | Status | Notes |
|----|-----------|--------|-------|
| 2.2.1 | Timing Adjustable | N/A | No auto-advancing content or timed operations. |
| 2.2.2 | Pause, Stop, Hide | ✅ | Live-updating session list can be paused via the Pause button in the toolbar. |

### 2.3 Seizures and Physical Reactions

| SC | Criterion | Status | Notes |
|----|-----------|--------|-------|
| 2.3.1 | Three Flashes or Below Threshold | ✅ | No flashing content. Terminal cursor blink is the only animation and flashes at < 3 Hz. |

### 2.4 Navigable

| SC | Criterion | Status | Notes |
|----|-----------|--------|-------|
| 2.4.1 | Bypass Blocks | ✅ | Skip-to-content shortcut (Alt+1) jumps past the sidebar to the main session pane. |
| 2.4.2 | Page Titled | ✅ | Window title updates with active session name (e.g., "SessionLedger — session-abc123"). |
| 2.4.3 | Focus Order | ✅ | Tab order follows visual layout: sidebar → search → session list → bundle detail. |
| 2.4.4 | Link Purpose (In Context) | ✅ | All interactive elements have descriptive accessible names. |
| 2.4.5 | Multiple Ways | ✅ | Sessions reachable via tree navigation, search, and command palette. |
| 2.4.6 | Headings and Labels | ✅ | Section headings use semantic heading levels (h2, h3). Form controls have visible labels. |
| 2.4.7 | Focus Visible | ✅ | High-contrast focus ring (2px solid, 3:1 contrast) on all focusable elements. Respects `prefers-reduced-motion`. |

### 2.5 Input Modalities

| SC | Criterion | Status | Notes |
|----|-----------|--------|-------|
| 2.5.1 | Pointer Gestures | N/A | No multipoint or path-based gestures. |
| 2.5.2 | Pointer Cancellation | ✅ | Actions activate on `mouseup`, not `mousedown`. Drag operations can be cancelled. |
| 2.5.3 | Label in Name | ✅ | Accessible names of controls include visible label text. |
| 2.5.4 | Motion Actuation | N/A | No motion-triggered functionality. |

---

## 3 — Understandable

### 3.1 Readable

| SC | Criterion | Status | Notes |
|----|-----------|--------|-------|
| 3.1.1 | Language of Page | ✅ | Root `lang` attribute set from locale selection. Defaults to `"en"`. |
| 3.1.2 | Language of Parts | ✅ | Code blocks and technical terms retain their original language annotation. |

### 3.2 Predictable

| SC | Criterion | Status | Notes |
|----|-----------|--------|-------|
| 3.2.1 | On Focus | ✅ | No context changes occur on focus alone. |
| 3.2.2 | On Input | ✅ | Search filters results incrementally without navigating away. |
| 3.2.3 | Consistent Navigation | ✅ | Navigation structure is consistent across all viewer panels. |
| 3.2.4 | Consistent Identification | ✅ | Icons and labels are reused consistently (e.g., the gear icon always means Settings). |

### 3.3 Input Assistance

| SC | Criterion | Status | Notes |
|----|-----------|--------|-------|
| 3.3.1 | Error Identification | ✅ | Errors displayed inline beneath the relevant field with `role="alert"`. |
| 3.3.2 | Labels or Instructions | ✅ | Search and filter controls include placeholder instructions and `aria-describedby` hints. |
| 3.3.3 | Error Suggestion | ✅ | When a filter yields no results, a suggestion message explains available filters. |
| 3.3.4 | Error Prevention (Legal, Financial, Data) | N/A | Viewer is read-only; no data submission. |

---

## 4 — Robust

### 4.1 Compatible

| SC | Criterion | Status | Notes |
|----|-----------|--------|-------|
| 4.1.1 | Parsing | N/A | Native application, not HTML. |
| 4.1.2 | Name, Role, Value | ✅ | All interactive Dioxus elements expose name, role, and value through the accessibility tree. |
| 4.1.3 | Status Messages | ✅ | Non-interactive status updates (e.g., "Loaded 42 sessions") use `role="status"` so screen readers announce them without focus change. |

---

## Keyboard Shortcuts Reference

| Shortcut | Action |
|----------|--------|
| `Ctrl/Cmd + F` | Focus search |
| `Ctrl/Cmd + 1-3` | Switch tabs (Sessions / Unfinished / Settings) |
| `Alt + 1` | Skip to main content |
| `Alt + ↑/↓` | Navigate session list |
| `Enter` | Open selected session |
| `Escape` | Close overlay / clear search |
| `Ctrl/Cmd + K` | Open command palette |
| `Ctrl/Cmd + ,` | Open settings |

## Testing Protocol

1. **Automated**: Run [accessibility-lint](https://github.com/nickel-org/a11y-lint) in CI on all viewer components.
2. **Screen reader**: Manual smoke tests with NVDA (Windows), VoiceOver (macOS), and Orca (Linux) — see `docs/a11y/screen-reader-smoke.md`.
3. **Keyboard-only**: Full session browsing workflow completed without pointing device — see `docs/a11y/progressive-disclosure.md`.
4. **Contrast**: Automated contrast checks via design token validation — see `docs/a11y/design-tokens.md`.
5. **Regression**: New UI components must include accessibility assertions before merge.

## References

- [WCAG 2.1 AA](https://www.w3.org/TR/WCAG21/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [Dioxus Accessibility](https://dioxuslabs.com/learn/0.6/reference/accessibility)
- [SessionLedger a11y design tokens](design-tokens.md)
- [Overlay escape behavior](overlay-escape.md)
- [Screen reader smoke tests](screen-reader-smoke.md)
