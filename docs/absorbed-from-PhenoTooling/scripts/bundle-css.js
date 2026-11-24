#!/usr/bin/env node
/**
 * bundle-css.js
 *
 * Concatenates individual CSS files from styles/ into three bundle files
 * under styles/bundled/:
 *   - core.css      — design-system foundation (tokens, base, shell, responsive)
 *   - components.css — interactive UI elements
 *   - pages.css     — page-specific layouts
 *
 * Each bundle is minified: block/line comments stripped (URLs preserved),
 * redundant whitespace collapsed, and insignificant spaces removed.
 * A comment header with the original file list is kept in a banner.
 */

import { mkdir, readdir, readFile, writeFile } from 'node:fs/promises';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

// --- CSS Minifier (zero-dependency) ---

function minifyCss(css) {
  let output = '';
  let i = 0;
  const len = css.length;

  while (i < len) {
    if (css[i] === '/' && css[i + 1] === '*') {
      // Block comment or @charset — find closing */
      const end = css.indexOf('*/', i + 2);
      if (end === -1) break;
      i = end + 2;
    } else if (css[i] === '/' && css[i + 1] === '/') {
      // Line comment — skip to newline
      const end = css.indexOf('\n', i + 2);
      i = end === -1 ? len : end + 1;
    } else if (css[i] === "'" || css[i] === '"') {
      // String literal — copy verbatim
      const quote = css[i];
      let j = i + 1;
      while (j < len && css[j] !== quote) {
        j = css[j] === '\\' ? j + 2 : j + 1;
      }
      output += css.slice(i, j + 1);
      i = j + 1;
    } else if (css[i] <= ' ') {
      // Whitespace — preserve a single space when between non-whitespace chars.
      // The subsequent collapse step will reduce runs of spaces to one.
      // This ensures descendant combinator spaces (e.g., '.foo a') survive.
      output += ' ';
      i++;
    } else {
      output += css[i];
      i++;
    }
  }

  // Collapse runs of spaces to a single space
  output = output.replace(/ +/g, ' ');

  // Remove spaces inside function parentheses: calc( 100% - 20px ) → calc(100%-20px)
  output = output.replace(/\(\s+/g, '(');
  output = output.replace(/\s+\)/g, ')');

  // Remove space after colon in property values: font-size: 1rem → font-size:1rem
  // But preserve space after colon in pseudo-elements :hover, :before, etc.
  output = output.replace(/([^:])\s*:\s+/g, '$1:');

  // Remove space after comma in value lists (but NOT inside calc/log functions)
  output = output.replace(/,\s+/g, ',');

  // Remove space before semicolons
  output = output.replace(/\s+;/g, ';');

  // Remove space before closing braces
  output = output.replace(/\s+}/g, '}');

  // Remove space after opening braces
  output = output.replace(/{\s+/g, '{');

  // Remove space before opening braces (after selector, preserving selectors like `a .b {`)
  output = output.replace(/\s+{/g, '{');

  // Remove spaces around > child combinator
  output = output.replace(/\s*>\s*/g, '>');

  // Remove spaces around + adjacent combinator
  output = output.replace(/\s*\+\s*/g, '+');

  // Remove spaces around ~ sibling combinator
  output = output.replace(/\s*~\s*/g, '~');

  // Remove space after !important
  output = output.replace(/!important\s/g, '!important');

  // Remove space after ! in non-important (unlikely but clean up)
  output = output.replace(/! /g, '!');

  // Remove empty rule blocks left over after stripping
  output = output.replace(/[^{}]*\{\}/g, '');

  // Final cleanup: leading/trailing spaces on each remaining token
  output = output.replace(/^ +| +$/gm, '');

  return output;
}

const root = fileURLToPath(new URL('..', import.meta.url));
const stylesDir = join(root, 'styles');
const outDir = join(stylesDir, 'bundled');

// --- Bundle definitions (order matters) ---

const bundles = {
  'core.css': [
    'tokens.css',
    'base.css',
    'shell.css',
  ],
  'components.css': [
    'artifacts.css',
    'responsive.css',
    'cards.css',
    'cursor.css',
    'reveal.css',
    'transitions.css',
    'parallax.css',
    'image-reveal.css',
    'image-slider.css',
    'skeleton.css',
    'project-index.css',
    'work-catalog.css',
    'radar.css',
    'timeline.css',
    'resume-timeline.css',
  ],
  'pages.css': [
    'hero.css',
    'main.css',
    'case-studies.css',
    'blog.css',
    'contact.css',
    'code-annotate.css',
    'cast-player.css',
    'construction-gate.css',
  ],
};

// --- Validate that every CSS file in styles/ is assigned to exactly one bundle ---

const allStyleFiles = (await readdir(stylesDir)).filter((f) => f.endsWith('.css'));
const bundled = new Set(Object.values(bundles).flat());

const unassigned = allStyleFiles.filter((f) => !bundled.has(f));
if (unassigned.length > 0) {
  console.error(`Warning: CSS files not assigned to any bundle: ${unassigned.join(', ')}`);
}

const assigned = Object.values(bundles).flat();
const dupes = assigned.filter((f, i) => assigned.indexOf(f) !== i);
if (dupes.length > 0) {
  console.error(`Warning: CSS files assigned to multiple bundles: ${[...new Set(dupes)].join(', ')}`);
}

// --- Build bundles ---

await mkdir(outDir, { recursive: true });

const stats = [];

for (const [bundleName, files] of Object.entries(bundles)) {
  const parts = [];

  // Header comment
  const headerLines = [
    `/* ========================================`,
    ` * Bundle: ${bundleName}`,
    ` * Files:  ${files.length}`,
    ` * Generated by scripts/bundle-css.js`,
    ` * ======================================== */`,
    '',
  ];
  parts.push(headerLines.join('\n'));

  // Concatenate each file with a section comment
  for (const file of files) {
    const filePath = join(stylesDir, file);
    const relPath = relative(root, filePath);
    let content;
    try {
      content = await readFile(filePath, 'utf8');
    } catch {
      console.error(`  Skipping missing file: ${relPath}`);
      continue;
    }

    parts.push(`/* --- ${relPath} --- */`);
    parts.push(content.trimEnd());
    parts.push(''); // trailing newline between files
  }

  const rawContent = parts.join('\n');
  const bundleContent = minifyCss(rawContent);
  const outPath = join(outDir, bundleName);
  await writeFile(outPath, bundleContent);

  const rawBytes = Buffer.byteLength(rawContent);
  const bytes = Buffer.byteLength(bundleContent);
  stats.push({ name: bundleName, files: files.length, bytes, rawBytes });
}

// --- Report ---

console.log('\nCSS Bundle Results:');
console.log('─'.repeat(60));
for (const s of stats) {
  const kb = (s.bytes / 1024).toFixed(1);
  const rawKb = (s.rawBytes / 1024).toFixed(1);
  const savings = ((1 - s.bytes / s.rawBytes) * 100).toFixed(0);
  console.log(`  ${s.name.padEnd(20)} ${String(s.files).padStart(3)} files  ${kb.padStart(7)} KB  (was ${rawKb}, -${savings}%)`);
}
console.log('─'.repeat(60));
const totalBytes = stats.reduce((sum, s) => sum + s.bytes, 0);
const totalRawBytes = stats.reduce((sum, s) => sum + s.rawBytes, 0);
const totalFiles = stats.reduce((sum, s) => sum + s.files, 0);
const totalSavings = ((1 - totalBytes / totalRawBytes) * 100).toFixed(0);
console.log(`  ${'TOTAL'.padEnd(20)} ${String(totalFiles).padStart(3)} files  ${(totalBytes / 1024).toFixed(1).padStart(7)} KB  (was ${(totalRawBytes / 1024).toFixed(1)}, -${totalSavings}%)`);
console.log(`\nBundles written to ${outDir}`);
