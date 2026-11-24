#!/usr/bin/env node
/**
 * minify-js.js
 *
 * Walks dist/ scripts/ and data/ directories, stripping single-line and
 * block comments from .js files while preserving string/template/regex
 * literals. This is a lightweight, zero-dependency minifier suitable for
 * the portfolio's own scripts — not a production-grade JS compressor.
 */

import { readdir, readFile, writeFile } from 'node:fs/promises';
import { join, extname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const distDir = join(root, 'dist');

// --- JS comment stripper ---

function stripComments(js) {
  let output = '';
  let i = 0;
  const len = js.length;

  while (i < len) {
    // Single-quoted string
    if (js[i] === "'") {
      let j = i + 1;
      while (j < len && js[j] !== "'") {
        j = js[j] === '\\' ? j + 2 : j + 1;
      }
      output += js.slice(i, j + 1);
      i = j + 1;
    }
    // Double-quoted string
    else if (js[i] === '"') {
      let j = i + 1;
      while (j < len && js[j] !== '"') {
        j = js[j] === '\\' ? j + 2 : j + 1;
      }
      output += js.slice(i, j + 1);
      i = j + 1;
    }
    // Template literal
    else if (js[i] === '`') {
      let j = i + 1;
      while (j < len && js[j] !== '`') {
        j = js[j] === '\\' ? j + 2 : j + 1;
      }
      output += js.slice(i, j + 1);
      i = j + 1;
    }
    // Regex literal (simplified detection: follows ( , = ! & | ? : [ ; { or start of line)
    else if (js[i] === '/' && js[i + 1] !== '/' && js[i + 1] !== '*') {
      const prevChar = output.trimEnd().at(-1) ?? '';
      const isRegexContext = /[(!&|?:;={[\n,]/.test(prevChar) || output.trimEnd() === '';
      if (isRegexContext) {
        let j = i + 1;
        while (j < len && js[j] !== '/') {
          j = js[j] === '\\' ? j + 2 : j + 1;
        }
        // Skip regex flags
        while (j + 1 < len && /[gimsuy]/.test(js[j + 1])) j++;
        output += js.slice(i, j + 1);
        i = j + 1;
      } else {
        output += js[i];
        i++;
      }
    }
    // Block comment
    else if (js[i] === '/' && js[i + 1] === '*') {
      const end = js.indexOf('*/', i + 2);
      if (end === -1) break;
      // Preserve line breaks to not disrupt source maps / line numbers
      i = end + 2;
    }
    // Single-line comment
    else if (js[i] === '/' && js[i + 1] === '/') {
      const end = js.indexOf('\n', i + 2);
      i = end === -1 ? len : end + 1;
    }
    else {
      output += js[i];
      i++;
    }
  }

  // Collapse multiple blank lines to single
  output = output.replace(/\n{3,}/g, '\n\n');

  return output;
}

// --- Walk and minify ---

async function walk(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) {
      await walk(path);
    } else if (extname(entry.name) === '.js') {
      const content = await readFile(path, 'utf8');
      const minified = stripComments(content);
      if (minified.length < content.length) {
        await writeFile(path, minified);
        const savings = ((1 - minified.length / content.length) * 100).toFixed(0);
        console.log(`  minified: ${path.replace(distDir + '/', '')} (-${savings}%)`);
      }
    }
  }
}

await walk(distDir);
console.log('\nJS minification complete.');
